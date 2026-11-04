# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise the optional SeedVR2, RTX VSR, and VOSR2 adapters with fake nodes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import nodes as h3_nodes  # noqa: E402
from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3Context,
    MiniMaxH3EasyRenderPass2,
    PASS2_REPAIR_RTX,
    PASS2_REPAIR_SEEDVR2,
    PASS2_REPAIR_VOSR2,
)


class FakeVideoVAE:
    def __init__(self):
        self.encoded_shape = None

    def encode(self, frames):
        self.encoded_shape = tuple(frames.shape)
        batch, _height, _width, _channels = frames.shape
        return torch.zeros((batch, 24, 2, 4, 8), dtype=torch.float32)


class FakeVAEDecode:
    def decode(self, _vae, _latent):
        return (torch.zeros((1, 8, 8, 3), dtype=torch.float32),)


class FakeSeedVR2:
    call = None

    @classmethod
    def execute(cls, **kwargs):
        cls.call = kwargs
        return SimpleNamespace(args=(kwargs["image"] + 0.1,))


class FakeRTX:
    call = None

    @classmethod
    def execute(cls, **kwargs):
        cls.call = kwargs
        return SimpleNamespace(args=(kwargs["images"] + 0.2,))


class FakeVOSRLoader:
    @classmethod
    def execute(cls, **kwargs):
        return SimpleNamespace(args=({"model": kwargs["model"]},))


class FakeVOSRUpscale:
    call = None

    @classmethod
    def execute(cls, **kwargs):
        cls.call = kwargs
        return SimpleNamespace(args=(kwargs["image"] + 0.3,))


def main() -> None:
    video = torch.zeros((1, 24, 2, 4, 8), dtype=torch.float32)
    fake_vae = FakeVideoVAE()
    context = MiniMaxH3Context(
        conditioning=[[torch.zeros((1, 8)), {}]],
        latent={"samples": video},
        video_vae=fake_vae,
        audio_vae=None,
        fps=24,
        aspect_ratio="16:9",
    )
    mappings = {
        "SeedVR2VideoUpscaler": FakeSeedVR2,
        "RTXVideoSuperResolution": FakeRTX,
        "VOSR2ModelLoader": FakeVOSRLoader,
        "VOSR2Upscale": FakeVOSRUpscale,
    }

    with (
        patch.object(h3_nodes.nodes, "VAEDecode", FakeVAEDecode),
        patch.object(h3_nodes.nodes, "NODE_CLASS_MAPPINGS", mappings),
        patch.object(
            MiniMaxH3EasyRenderPass2,
            "_resolve_repair_model",
            side_effect=lambda _engine, model: "VOSR2" if model.startswith("VOSR2") else "seedvr2_ema_3b_fp8_e4m3fn.safetensors",
        ),
    ):
        seed_output = MiniMaxH3EasyRenderPass2._repair_video_latent(
            context,
            video,
            engine=PASS2_REPAIR_SEEDVR2,
            model_name="auto",
            scale=1.0,
            seed=42,
            batch_size=5,
            temporal_overlap=2,
            color_correction="lab",
            quality="ULTRA",
            device="cuda",
            blocks_to_swap=0,
            offload_device="cpu",
            vae_tiling=True,
        )
        rtx_output = MiniMaxH3EasyRenderPass2._repair_video_latent(
            context,
            video,
            engine=PASS2_REPAIR_RTX,
            model_name="auto",
            scale=1.5,
            seed=42,
            batch_size=5,
            temporal_overlap=2,
            color_correction="lab",
            quality="HIGH",
            device="cuda",
            blocks_to_swap=0,
            offload_device="cpu",
            vae_tiling=True,
        )
        vosr_output = MiniMaxH3EasyRenderPass2._repair_video_latent(
            context,
            video,
            engine=PASS2_REPAIR_VOSR2,
            model_name="VOSR2 / VOSR2",
            scale=1.0,
            seed=42,
            batch_size=5,
            temporal_overlap=2,
            color_correction="wavelet",
            quality="ULTRA",
            device="cuda",
            blocks_to_swap=0,
            offload_device="cpu",
            vae_tiling=True,
        )

    assert all(tuple(value.shape) == (1, 24, 2, 4, 8) for value in (seed_output, rtx_output, vosr_output))
    assert FakeSeedVR2.call["resolution"] == 16
    assert FakeSeedVR2.call["batch_size"] == 5
    assert FakeSeedVR2.call["temporal_overlap"] == 2
    assert FakeSeedVR2.call["dit"]["model"] == "seedvr2_ema_3b_fp8_e4m3fn.safetensors"
    assert FakeRTX.call["resize_type"]["scale"] == 1.5
    assert FakeRTX.call["quality"] == "HIGH"
    assert FakeVOSRUpscale.call["upscale"] == 1
    assert FakeVOSRUpscale.call["tile_size"] == 512
    assert fake_vae.encoded_shape == (1, 8, 8, 3)
    print("Pass2 restoration engine adapters: ok")


if __name__ == "__main__":
    main()
