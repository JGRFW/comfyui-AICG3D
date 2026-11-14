# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = ROOT.parents[1]
for path in (str(COMFY_ROOT), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import final_sequence_packed as packed  # noqa: E402
from aicg3d_h3easy import final_upscale  # noqa: E402
from aicg3d_h3easy import nodes as base  # noqa: E402


WORKFLOW = ROOT / "workflows" / "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json"
SHORT_DRAMA_WORKFLOW = (
    COMFY_ROOT
    / "user"
    / "default"
    / "workflows"
    / "13.AICG3D_MiniMax H3 无限长视频短剧工作流.json"
)


class _FakeVideo:
    def get_components(self):
        return None


def _fake_bundle():
    return object.__new__(base.MiniMaxH3Bundle)


def test_legacy_final_upscale_stays_registered() -> None:
    mapping = final_upscale.NODE_CLASS_MAPPINGS
    assert "MiniMaxH3EasyFinalHighResUpscale" in mapping
    assert "MiniMaxH3EasyFinalHighResUpscalePacked" not in mapping


def test_packed_upscale_has_one_linked_input_and_compact_order() -> None:
    inputs = packed.MiniMaxH3EasyFinalHighResUpscalePacked.INPUT_TYPES()
    assert set(inputs) == {"required"}
    names = list(inputs["required"])
    assert names[:5] == [
        "final_sequence",
        "filename_prefix",
        "second_pass",
        "refiner_lora",
        "show_advanced_settings",
    ]
    assert "video" not in names
    assert "h3_bundle" not in names
    assert "model" not in names
    assert inputs["required"]["show_advanced_settings"][1]["default"] is False
    relay_names = [
        "relay_vsr_enabled",
        "relay_vsr_model",
        "relay_vsr_vae",
        "relay_vsr_detail",
        "relay_lock_source_exposure",
    ]
    assert names[-5:] == relay_names
    assert inputs["required"]["relay_vsr_enabled"][1]["default"] is False


def test_combined_final_node_has_one_segment_input_and_all_hd_controls() -> None:
    node = packed.MiniMaxH3EasyFinalSequenceUpscale
    inputs = node.INPUT_TYPES()
    names = list(inputs["required"])
    assert names[:5] == [
        "final_segment",
        "filename_prefix",
        "second_pass",
        "refiner_lora",
        "show_advanced_settings",
    ]
    assert "final_sequence" not in names
    assert "video" not in names
    assert "h3_bundle" not in names
    assert "model" not in names
    assert names[-5:] == [
        "relay_vsr_enabled",
        "relay_vsr_model",
        "relay_vsr_vae",
        "relay_vsr_detail",
        "relay_lock_source_exposure",
    ]
    assert set(inputs["optional"]) == {
        "cache_only",
        "cache_scope",
        "cache_segment_count",
        "cache_segment_indices",
        "cache_segment_nodes",
        "cache_chain_key",
    }
    assert node.RETURN_NAMES == (
        "video",
        "saved_file",
        "seam_report",
        "upscale_report",
    )


def test_sequence_combine_appends_packet_after_legacy_outputs() -> None:
    node = packed.MiniMaxH3EasyFinalSequenceCombine
    assert node.RETURN_TYPES[:3] == ("VIDEO", "STRING", "STRING")
    assert node.RETURN_TYPES[3] == packed.FINAL_SEQUENCE_TYPE
    assert node.RETURN_NAMES[:3] == ("video", "saved_file", "seam_report")
    assert node.RETURN_NAMES[3] == "final_sequence"

    bundle = _fake_bundle()
    config = SimpleNamespace(
        bundle=bundle,
        model="model-state",
        sampler="sampler-state",
        sigmas="sigmas-state",
    )
    chain = [SimpleNamespace(config=config, index=1)]
    base_result = {
        "ui": {"images": []},
        "result": ("video", "video/out.mp4", "seam report"),
    }
    with patch.object(node, "_resolve_chain_for_packet", return_value=chain), patch.object(
        base.MiniMaxH3EasySequenceCombine,
        "combine",
        return_value=dict(base_result),
    ):
        result = node.combine(final_segment=object())

    assert result["result"][:3] == base_result["result"]
    packet = result["result"][3]
    assert isinstance(packet, packed.MiniMaxH3FinalSequence)
    assert packet.h3_bundle is bundle
    assert packet.model == "model-state"
    assert packet.sampler == "sampler-state"
    assert packet.sigmas == "sigmas-state"


def test_refiner_is_only_applied_during_second_pass() -> None:
    node = packed.MiniMaxH3EasyFinalHighResUpscalePacked()
    sequence = packed.MiniMaxH3FinalSequence(
        video=_FakeVideo(),
        h3_bundle=_fake_bundle(),
        model="base-model",
        sampler="sampler",
        sigmas="sigmas",
    )
    calls: list[tuple[object, str]] = []

    def fake_apply(model, lora):
        calls.append((model, lora))
        return "refined-model"

    with patch.object(
        final_upscale.MiniMaxH3EasyFinalHighResUpscale,
        "upscale_final_video",
        return_value={"result": ("done",)},
    ) as parent, patch.object(base, "_apply_secondary_refiner_lora", side_effect=fake_apply):
        node.upscale_final_video(
            sequence,
            refiner_lora="refiner.safetensors",
            second_pass=False,
        )
        assert calls == []
        assert parent.call_args.kwargs["model"] == "base-model"

        node.upscale_final_video(
            sequence,
            refiner_lora="refiner.safetensors",
            second_pass=True,
        )
        assert calls == [("base-model", "refiner.safetensors")]
        assert parent.call_args.kwargs["model"] == "refined-model"


def test_combined_final_node_bypasses_hd_cleanly_when_all_stages_are_off() -> None:
    node = packed.MiniMaxH3EasyFinalSequenceUpscale()
    sequence = packed.MiniMaxH3FinalSequence(
        video=_FakeVideo(),
        h3_bundle=_fake_bundle(),
        saved_file="video/combined.mp4",
        seam_report="seam clean",
    )
    combined = {
        "ui": {"images": [{"filename": "combined.mp4"}]},
        "result": (sequence.video, sequence.saved_file, sequence.seam_report, sequence),
    }
    with patch.object(node, "combine", return_value=combined), patch.object(
        packed.MiniMaxH3EasyFinalHighResUpscalePacked,
        "upscale_final_video",
    ) as upscale:
        result = node.final_sequence_upscale(
            final_segment=object(),
            second_pass=False,
            repair_engine=base.PASS2_REPAIR_OFF,
            relay_vsr_enabled=False,
        )

    assert upscale.call_count == 0
    assert result["result"][:3] == (
        sequence.video,
        "video/combined.mp4",
        "seam clean",
    )
    assert "未重复采样" in result["result"][3]


def test_combined_final_node_keeps_post_hd_order() -> None:
    node = packed.MiniMaxH3EasyFinalSequenceUpscale()
    sequence = packed.MiniMaxH3FinalSequence(
        video=_FakeVideo(),
        h3_bundle=_fake_bundle(),
        saved_file="video/combined.mp4",
        seam_report="seam clean",
    )
    combined = {
        "ui": {},
        "result": (sequence.video, sequence.saved_file, sequence.seam_report, sequence),
    }
    highres = {
        "ui": {"images": [{"filename": "final.mp4"}]},
        "result": ("final-video", "video/final.mp4", "hd report"),
    }
    with patch.object(node, "combine", return_value=combined), patch.object(
        packed.MiniMaxH3EasyFinalHighResUpscalePacked,
        "upscale_final_video",
        return_value=highres,
    ) as upscale:
        result = node.final_sequence_upscale(
            final_segment=object(),
            filename_prefix="video/final",
            second_pass=True,
            refiner_lora="refiner.safetensors",
            latent_upscale_model="upscaler.safetensors",
        )

    assert upscale.call_count == 1
    assert upscale.call_args.args[0] is sequence
    assert upscale.call_args.kwargs["filename_prefix"] == "video/final"
    assert upscale.call_args.kwargs["second_pass"] is True
    assert result["result"] == (
        "final-video",
        "video/final.mp4",
        "seam clean",
        "hd report",
    )


def test_combined_final_node_defers_cleanup_until_final_output_success() -> None:
    node = packed.MiniMaxH3EasyFinalSequenceUpscale()
    sequence = packed.MiniMaxH3FinalSequence(
        video=_FakeVideo(),
        h3_bundle=_fake_bundle(),
        saved_file="video/combined.mp4",
        seam_report="seam clean",
    )
    combined = {
        "ui": {},
        "result": (sequence.video, sequence.saved_file, sequence.seam_report, sequence),
    }

    with patch.object(node, "combine", return_value=combined) as combine, patch.object(
        packed,
        "_finalize_sequence_segment_cleanup",
    ) as cleanup:
        node.final_sequence_upscale(
            final_segment=object(),
            second_pass=False,
            repair_engine=base.PASS2_REPAIR_OFF,
            relay_vsr_enabled=False,
        )
    assert combine.call_args.kwargs["_defer_segment_cleanup"] is True
    cleanup.assert_called_once_with(sequence)

    with patch.object(node, "combine", return_value=combined), patch.object(
        packed.MiniMaxH3EasyFinalHighResUpscalePacked,
        "upscale_final_video",
        side_effect=RuntimeError("post-HD failure"),
    ), patch.object(packed, "_finalize_sequence_segment_cleanup") as cleanup_after_failure:
        try:
            node.final_sequence_upscale(
                final_segment=object(),
                filename_prefix="video/final",
                second_pass=True,
            )
        except RuntimeError as exc:
            assert str(exc) == "post-HD failure"
        else:
            raise AssertionError("Expected the simulated post-HD failure")
    cleanup_after_failure.assert_not_called()


def test_workflow_uses_one_combined_final_node() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    nodes = {int(node["id"]): node for node in workflow["nodes"]}
    combined = nodes[60]

    assert 196 not in nodes
    assert combined["type"] == "AICG3D_H3FinalSequenceUpscale"
    assert combined["inputs"][0]["name"] == "final_segment"
    assert combined["inputs"][0]["link"] == 353
    assert [item["name"] for item in combined["outputs"]] == [
        "video",
        "saved_file",
        "seam_report",
        "upscale_report",
    ]
    assert combined["widgets_values"][:4] == [
        "video/MiniMax_H3_Final_HD",
        True,
        "none",
        False,
    ]
    assert combined["widgets_values"][-5:] == [
        False,
        "RelayVSR\\relayvsr_x2_lightx2v_int8_convrot.safetensors",
        "RelayVSR\\relayvsr_flash_vae_x2_fp32.safetensors",
        0.5,
        True,
    ]
    named = combined["widgets_values_named"]
    assert named["relay_vsr_enabled"] is False
    assert named["relay_vsr_model"].endswith("relayvsr_x2_lightx2v_int8_convrot.safetensors")
    assert named["relay_vsr_vae"].endswith("relayvsr_flash_vae_x2_fp32.safetensors")
    assert named["relay_vsr_detail"] == 0.5
    assert named["relay_lock_source_exposure"] is True

    links = {int(link[0]): link for link in workflow["links"]}
    assert 358 not in links
    assert 359 not in links
    assert 360 not in links
    assert 361 not in links
    assert links[353][1:5] == [193, 0, 60, 0]


def test_short_drama_workflow_uses_one_combined_final_node() -> None:
    if not SHORT_DRAMA_WORKFLOW.exists():
        print(f"SKIP missing local short-drama workflow: {SHORT_DRAMA_WORKFLOW}")
        return

    workflow = json.loads(SHORT_DRAMA_WORKFLOW.read_text(encoding="utf-8"))
    nodes = {int(node["id"]): node for node in workflow["nodes"]}
    links = {int(link[0]): link for link in workflow["links"]}

    assert 1159 not in nodes
    assert nodes[60]["type"] == "AICG3D_H3FinalSequenceUpscale"
    assert nodes[60]["inputs"][0]["name"] == "final_segment"
    assert nodes[60]["inputs"][0]["link"] == 745
    assert nodes[1160]["inputs"][0]["name"] == "video"
    assert nodes[1160]["inputs"][0]["link"] == 711

    assert 700 not in links
    assert links[745][1:5] == [1134, 0, 60, 0]
    assert links[711][1:5] == [60, 0, 1160, 0]

    global_node = nodes[212]
    input_names = [item["name"] for item in global_node["inputs"]]
    assert "second_pass_sampler_name" not in input_names
    assert input_names[-2:] == [
        "segment_output_directory",
        "segment_cleanup_policy",
    ]
    assert global_node["widgets_values"][-2:] == [
        "",
        "合成后提示删除",
    ]
    assert global_node["widgets_values_named"]["segment_output_directory"] == ""
    assert (
        global_node["widgets_values_named"]["segment_cleanup_policy"]
        == "合成后提示删除"
    )


def main() -> None:
    tests = (
        test_legacy_final_upscale_stays_registered,
        test_packed_upscale_has_one_linked_input_and_compact_order,
        test_combined_final_node_has_one_segment_input_and_all_hd_controls,
        test_sequence_combine_appends_packet_after_legacy_outputs,
        test_refiner_is_only_applied_during_second_pass,
        test_combined_final_node_bypasses_hd_cleanly_when_all_stages_are_off,
        test_combined_final_node_keeps_post_hd_order,
        test_combined_final_node_defers_cleanup_until_final_output_success,
        test_workflow_uses_one_combined_final_node,
        test_short_drama_workflow_uses_one_combined_final_node,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} packed final-sequence checks")


if __name__ == "__main__":
    main()
