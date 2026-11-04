# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify that AICG Render Pass 2 refines video while preserving source audio."""

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

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3Context,
    MiniMaxH3EasyRenderPass2,
    _lock_audio_latent,
    PASS2_TILED_OFF,
    _segment_av_streams,
    _segment_latent_streams,
    _segment_pack_latent,
)

from aicg3d_h3easy.aicg3d_sampler import AICG3DSamplerAdvanced  # noqa: E402


def test_sampler_forwards_audio_lock_mask() -> None:
    video = torch.zeros((1, 24, 1, 2, 2), dtype=torch.float32)
    audio = torch.zeros((1, 32, 1, 1), dtype=torch.float32)
    latent = _lock_audio_latent(_segment_pack_latent(video, audio), audio)
    captured = {}

    class FakeGuider:
        def __init__(self, model):
            self.model = model

        def set_conds(self, conditioning):
            self.conditioning = conditioning

        def sample(self, noise, samples, sampler, sigmas, **kwargs):
            captured["denoise_mask"] = kwargs.get("denoise_mask")
            return samples

    with (
        patch("aicg3d_h3easy.aicg3d_sampler.comfy.sample.prepare_noise", return_value=latent["samples"]),
        patch("aicg3d_h3easy.aicg3d_sampler.comfy.samplers.sampler_object", return_value=object()),
        patch("aicg3d_h3easy.aicg3d_sampler.nodes_custom_sampler.Guider_Basic", FakeGuider),
    ):
        AICG3DSamplerAdvanced().sample(
            object(),
            [[torch.zeros((1, 8)), {}]],
            latent,
            123,
            "euler",
            "beta",
            1,
            0.3,
            sigmas=torch.tensor([1.0, 0.0]),
        )

    mask_video, mask_audio = _segment_av_streams(
        captured.get("denoise_mask"),
        "Sampler discarded the packed AV denoise mask",
    )
    assert torch.all(mask_video > 0)
    assert torch.count_nonzero(mask_audio) == 0


def main() -> None:
    first_video = torch.zeros((1, 24, 2, 4, 8), dtype=torch.float32)
    first_audio = torch.arange(32, dtype=torch.float32).reshape(1, 32, 1, 1) / 32
    upscaled_video = torch.zeros((1, 24, 2, 6, 12), dtype=torch.float32)
    first_latent = _segment_pack_latent(first_video, first_audio)
    positive = [[torch.zeros((1, 8), dtype=torch.float32), {}]]
    context = MiniMaxH3Context(
        conditioning=positive,
        latent=first_latent,
        video_vae=None,
        audio_vae=None,
        fps=24,
        aspect_ratio="16:9",
        model=SimpleNamespace(load_device=torch.device("cpu")),
    )
    sampled_input = {}

    def fake_sample(
        model,
        conditioning,
        latent,
        seed,
        sampler_name,
        scheduler,
        steps,
        denoise,
        **kwargs,
    ):
        sampled_input.update(latent=latent, steps=steps, denoise=denoise)
        video, audio = _segment_latent_streams(latent)
        corrupted_audio = torch.ones_like(audio)
        return (_segment_pack_latent(video, corrupted_audio),)

    with (
        patch(
            "aicg3d_h3easy.nodes.MiniMaxH3EasyRenderPass2._upscale_video_latent",
            return_value=(upscaled_video, first_audio),
        ),
        patch(
            "aicg3d_h3easy.nodes.MiniMaxH3EasySecondPassConditioning.rebuild",
            return_value=(positive,),
        ),
        patch(
            "aicg3d_h3easy.aicg3d_sampler.AICG3DSamplerAdvanced.sample",
            side_effect=fake_sample,
        ),
        patch.object(
            MiniMaxH3EasyRenderPass2,
            "_decode_av",
            return_value=(torch.zeros((1, 2, 4, 4, 3)), {"waveform": torch.zeros(1, 1, 2), "sample_rate": 24000}),
        ),
        patch.object(MiniMaxH3EasyRenderPass2, "_compose_video", return_value="VIDEO"),
        patch("aicg3d_h3easy.nodes._release_render_resources"),
    ):
        result = MiniMaxH3EasyRenderPass2().render(
            {"latent": first_latent, "context": context},
            sampler_name="euler",
            scheduler="beta",
            steps=4,
            second_pass_seed=123,
            second_pass_denoise=0.3,
            latent_upscale_model="V2.safetensors",
            upscale_scale=1.5,
            tiled_sampling=PASS2_TILED_OFF,
            sample_preview="关",
            output_first_pass="关",
            cleanup_after_run="释放缓存",
        )

    refined_video, refined_audio = _segment_latent_streams(result[0]["latent"])
    assert tuple(refined_video.shape) == tuple(upscaled_video.shape)
    assert torch.equal(refined_audio, first_audio)

    mask_video, mask_audio = _segment_av_streams(
        sampled_input["latent"].get("noise_mask"),
        "Second-pass audio lock mask is missing",
    )
    assert torch.all(mask_video > 0)
    assert torch.count_nonzero(mask_audio) == 0
    print("Pass2 audio preservation and lock mask: ok")

    test_sampler_forwards_audio_lock_mask()
    print("Sampler audio lock mask forwarding: ok")


if __name__ == "__main__":
    main()
