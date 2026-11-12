# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import torch

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = ROOT.parents[1]
for path in (str(COMFY_ROOT), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import relay_vsr  # noqa: E402


MODEL_X2 = "RelayVSR\\relayvsr_x2_lightx2v_int8_convrot.safetensors"
MODEL_X4 = "RelayVSR\\relayvsr_x4_int8_convrot.safetensors"
VAE_X2 = "RelayVSR\\relayvsr_flash_vae_x2_fp32.safetensors"
VAE_X4 = "RelayVSR\\relayvsr_flash_vae_x4_fp32.safetensors"


class _FakeVideo:
    def __init__(self, frames: torch.Tensor, audio: object) -> None:
        self.frames = frames
        self.audio = audio

    def get_components(self):
        return SimpleNamespace(
            images=self.frames,
            audio=self.audio,
            frame_rate=24.0,
        )


def _fake_nodes(records: dict[str, object]):
    class FakeUNETLoader:
        def load_unet(self, name, weight_dtype):
            records["model"] = (name, weight_dtype)
            return ("loaded-model",)

    class FakeVAELoader:
        def load_vae(self, name):
            records["vae"] = name
            return ("loaded-vae",)

    class FakeKSampler:
        def sample(self, *args):
            records["ksampler"] = args
            return ({"samples": torch.zeros((1, 4, 2, 2, 2))},)

    return SimpleNamespace(
        UNETLoader=FakeUNETLoader,
        VAELoader=FakeVAELoader,
        KSampler=FakeKSampler,
    )


def test_relay_scale_detection() -> None:
    assert relay_vsr.relay_scale(MODEL_X2) == 2
    assert relay_vsr.relay_scale(MODEL_X4) == 4
    assert relay_vsr.relay_scale(VAE_X2) == 2
    assert relay_vsr.relay_scale(VAE_X4) == 4
    assert relay_vsr.relay_scale("plain-vae.safetensors") is None


def test_matching_x2_model_and_vae_use_reference_sampler() -> None:
    records: dict[str, object] = {}
    source = torch.full((5, 12, 10, 3), 0.2, dtype=torch.float32)
    decoded = torch.full((5, 24, 20, 3), 0.22, dtype=torch.float32)

    class FakeConditioning:
        @staticmethod
        def execute(model, images):
            records["conditioning"] = (model, images)
            return (["positive"], {"samples": torch.zeros((1, 4, 2, 2, 2))})

    class FakeDecode:
        @staticmethod
        def execute(vae, samples, images, detail=1.0):
            records["decode"] = (vae, samples, images, detail)
            return (decoded,)

    fake_nodes = _fake_nodes(records)
    core_classes = {
        "RelayVSRConditioning": FakeConditioning,
        "VSRDecode": FakeDecode,
    }
    with patch.object(relay_vsr, "relay_model_choices", return_value=[MODEL_X2]), patch.object(
        relay_vsr,
        "relay_vae_choices",
        return_value=[VAE_X2],
    ), patch.object(relay_vsr.importlib, "import_module", return_value=fake_nodes), patch.object(
        relay_vsr,
        "_core_node_class",
        side_effect=lambda name: core_classes[name],
    ):
        runner = relay_vsr.RelayVSRRunner(
            MODEL_X2,
            VAE_X2,
            detail=0.5,
            lock_source_exposure=True,
        )
        enhanced = runner.enhance(source)

    assert records["model"] == (MODEL_X2, "default")
    assert records["vae"] == VAE_X2
    conditioning_model, conditioning_frames = records["conditioning"]
    assert conditioning_model == "loaded-model"
    assert conditioning_frames.shape == source.shape
    _decode_vae, _samples, decode_frames, detail = records["decode"]
    assert decode_frames.shape == source.shape
    assert detail == 0.5

    sampler_args = records["ksampler"]
    assert sampler_args[1:7] == (0, 1, 1.0, "euler", "simple", ["positive"])
    assert sampler_args[7] == ["positive"]
    assert sampler_args[9] == 1.0
    assert enhanced.shape == decoded.shape
    assert enhanced.shape[0] == source.shape[0]
    assert torch.allclose(
        enhanced.mean(dim=(1, 2, 3)),
        source.mean(dim=(1, 2, 3)),
        atol=1e-4,
    )


def test_mismatched_model_and_vae_are_rejected() -> None:
    with patch.object(relay_vsr, "relay_model_choices", return_value=[MODEL_X2]), patch.object(
        relay_vsr,
        "relay_vae_choices",
        return_value=[VAE_X4],
    ):
        try:
            relay_vsr.RelayVSRRunner(MODEL_X2, VAE_X4)
        except ValueError as exc:
            assert "相同倍数" in str(exc)
        else:
            raise AssertionError("mismatched RelayVSR scales were accepted")


def test_relay_decode_runs_inside_inference_mode() -> None:
    records: dict[str, object] = {}
    source = torch.full((3, 8, 6, 3), 0.2, dtype=torch.float32)
    active = {"value": False}

    class RecordingInferenceMode:
        def __enter__(self):
            active["value"] = True
            records["entered"] = True
            return self

        def __exit__(self, exc_type, exc, traceback):
            active["value"] = False
            records["exited"] = True
            return False

    def assert_inference_mode(stage: str) -> None:
        if not active["value"]:
            raise AssertionError(f"{stage} ran outside torch.inference_mode")

    class FakeConditioning:
        @staticmethod
        def execute(model, images):
            assert_inference_mode("RelayVSRConditioning")
            return (["positive"], {"samples": torch.zeros((1, 4, 1, 2, 2))})

    class FakeDecode:
        @staticmethod
        def execute(vae, samples, images, detail=1.0):
            assert_inference_mode("VSRDecode")
            return (torch.full((3, 16, 12, 3), 0.2, dtype=torch.float32),)

    fake_nodes = _fake_nodes(records)
    original_sample = fake_nodes.KSampler.sample

    def recording_sample(*args):
        assert_inference_mode("KSampler")
        return original_sample(*args)

    fake_nodes.KSampler.sample = staticmethod(recording_sample)
    core_classes = {
        "RelayVSRConditioning": FakeConditioning,
        "VSRDecode": FakeDecode,
    }
    with patch.object(relay_vsr, "relay_model_choices", return_value=[MODEL_X2]), patch.object(
        relay_vsr,
        "relay_vae_choices",
        return_value=[VAE_X2],
    ), patch.object(relay_vsr.importlib, "import_module", return_value=fake_nodes), patch.object(
        relay_vsr,
        "_core_node_class",
        side_effect=lambda name: core_classes[name],
    ), patch.object(
        relay_vsr.torch,
        "inference_mode",
        side_effect=lambda: RecordingInferenceMode(),
    ):
        runner = relay_vsr.RelayVSRRunner(MODEL_X2, VAE_X2)
        result = runner.enhance(source)

    assert records.get("entered") is True
    assert records.get("exited") is True
    assert active["value"] is False
    assert result.shape == (3, 16, 12, 3)


def test_apply_to_video_preserves_original_audio() -> None:
    frames = torch.full((4, 8, 6, 3), 0.25, dtype=torch.float32)
    enhanced = torch.full((4, 8, 6, 3), 0.5, dtype=torch.float32)
    audio = object()
    runner = Mock()
    runner.enhance.return_value = enhanced
    captured: dict[str, object] = {}

    def make_components(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    with patch("comfy_api.latest.InputImpl.VideoFromComponents") as video_from, patch(
        "comfy_api.latest.Types.VideoComponents",
        side_effect=make_components,
    ):
        video_from.side_effect = lambda components: components
        result = relay_vsr.apply_to_video(_FakeVideo(frames, audio), runner)

    runner.enhance.assert_called_once()
    assert torch.equal(runner.enhance.call_args.args[0], frames)
    assert result.images is enhanced
    assert result.audio is audio
    assert captured["audio"] is audio
    assert float(result.frame_rate) == 24.0


def test_closed_renderer_keeps_non_relay_workflows_unchanged() -> None:
    from aicg3d_h3easy import nodes as base

    required = base.MiniMaxH3EasyRenderAdvancedWithModel.INPUT_TYPES()["required"]
    names = list(required)
    relay_names = [
        "relay_vsr_enabled",
        "relay_vsr_model",
        "relay_vsr_vae",
        "relay_vsr_detail",
        "relay_lock_source_exposure",
    ]
    assert names[-5:] == relay_names
    assert names[-6:-5] == ["sample_preview"]
    assert required["relay_vsr_enabled"][1]["default"] is False


def main() -> None:
    tests = (
        test_relay_scale_detection,
        test_matching_x2_model_and_vae_use_reference_sampler,
        test_mismatched_model_and_vae_are_rejected,
        test_relay_decode_runs_inside_inference_mode,
        test_apply_to_video_preserves_original_audio,
        test_closed_renderer_keeps_non_relay_workflows_unchanged,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} RelayVSR checks")


if __name__ == "__main__":
    main()
