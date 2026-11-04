# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Checks for exact-target Pass2 upscaling and repair-only sampling."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import torch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3EasyRenderPass2,
    PASS2_UPSCALE_MODE_REPAIR,
    PASS2_UPSCALE_MODE_SCALE,
    PASS2_UPSCALE_MODE_TARGET,
    _segment_pack_latent,
)


def main() -> None:
    required = MiniMaxH3EasyRenderPass2.INPUT_TYPES()["required"]
    assert required["upscale_mode"][1]["default"] == PASS2_UPSCALE_MODE_SCALE
    assert required["target_width"][1]["default"] == 1920
    assert required["target_height"][1]["default"] == 1088

    video = torch.zeros((1, 24, 2, 45, 84), dtype=torch.float32)
    audio = torch.zeros((1, 32, 2, 1), dtype=torch.float32)
    packed = _segment_pack_latent(video, audio)
    upscaled = torch.zeros((1, 24, 2, 68, 120), dtype=torch.float32)
    captured = {}

    def fake_execute(latent, model_name, mode_config, align, chunking, device, precision):
        captured.update({
            "latent": latent,
            "model_name": model_name,
            "mode_config": mode_config,
            "align": align,
            "chunking": chunking,
            "device": device,
            "precision": precision,
        })
        return ({"samples": upscaled},)

    with patch(
        "aicg3d_h3easy.nodes.MiniMaxH3EasyLatentUpscaler3D.execute",
        side_effect=fake_execute,
    ):
        target_video, target_audio = MiniMaxH3EasyRenderPass2._upscale_video_latent(
            packed,
            "upscaler_v2.safetensors",
            1.5,
            "cuda",
            "fp16",
            True,
            None,
            upscale_mode=PASS2_UPSCALE_MODE_TARGET,
            target_width=1920,
            target_height=1088,
        )

    assert captured["mode_config"] == {
        "mode": "target dimensions",
        "width": 1920,
        "height": 1088,
    }
    assert torch.equal(target_video, upscaled)
    assert torch.equal(target_audio, audio)

    repaired_video, repaired_audio = MiniMaxH3EasyRenderPass2._upscale_video_latent(
        packed,
        None,
        1.5,
        "cuda",
        "fp16",
        True,
        None,
        upscale_mode=PASS2_UPSCALE_MODE_REPAIR,
        target_width=1920,
        target_height=1088,
    )
    assert torch.equal(repaired_video, video)
    assert torch.equal(repaired_audio, audio)
    print("Pass2 target resolution and repair-only modes: ok")


if __name__ == "__main__":
    main()
