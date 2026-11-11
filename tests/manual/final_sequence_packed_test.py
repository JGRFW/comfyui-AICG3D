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
    chain = [SimpleNamespace(config=config)]
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


def test_workflow_uses_one_final_sequence_wire() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    nodes = {int(node["id"]): node for node in workflow["nodes"]}
    combine = nodes[60]
    upscale = nodes[196]

    assert combine["type"] == "AICG3D_H3FinalSequenceCombine"
    assert combine["outputs"][3]["name"] == "final_sequence"
    assert combine["outputs"][3]["type"] == packed.FINAL_SEQUENCE_TYPE
    assert upscale["type"] == "AICG3D_H3FinalHighResUpscalePacked"
    assert [item["name"] for item in upscale["inputs"]] == ["final_sequence"]
    assert upscale["inputs"][0]["link"] == 361
    assert upscale["widgets_values"][:4] == [
        "video/MiniMax_H3_Final_HD",
        True,
        "none",
        False,
    ]

    links = {int(link[0]): link for link in workflow["links"]}
    assert 358 not in links
    assert 359 not in links
    assert 360 not in links
    assert links[361][1:5] == [60, 3, 196, 0]
    assert links[361][5] == packed.FINAL_SEQUENCE_TYPE


def main() -> None:
    tests = (
        test_legacy_final_upscale_stays_registered,
        test_packed_upscale_has_one_linked_input_and_compact_order,
        test_sequence_combine_appends_packet_after_legacy_outputs,
        test_refiner_is_only_applied_during_second_pass,
        test_workflow_uses_one_final_sequence_wire,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} packed final-sequence checks")


if __name__ == "__main__":
    main()
