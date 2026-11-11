# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression checks for the Smart Drama global second-pass switch."""

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
    MiniMaxH3EasySequenceGlobal,
    MiniMaxH3EasySequenceSegment,
    _segment_av_streams,
    _segment_latent_streams,
    _segment_pack_latent,
)


def main() -> None:
    required = MiniMaxH3EasySequenceGlobal.INPUT_TYPES()["required"]
    assert "second_pass" in required
    assert required["second_pass"][0] == "BOOLEAN"
    assert required["second_pass"][1]["default"] is False
    for name in (
        "second_pass_model",
        "second_pass_scale",
        "second_pass_sampler_name",
        "second_pass_scheduler",
        "second_pass_steps",
        "second_pass_denoise",
    ):
        assert name in required

    first_video = torch.zeros((1, 24, 14, 4, 8), dtype=torch.float32)
    first_audio = torch.zeros((1, 32, 2, 1), dtype=torch.float32)
    upscaled_video = torch.zeros((1, 24, 14, 6, 12), dtype=torch.float32)
    first_latent = _segment_pack_latent(first_video, first_audio)
    conditioning = [[torch.zeros((1, 8), dtype=torch.float32), {}]]
    config = SimpleNamespace(
        second_pass=True,
        second_pass_model="V2.safetensors",
        second_pass_scale=1.5,
        second_pass_sampler_name="er_sde",
        second_pass_scheduler="beta",
        second_pass_steps=4,
        second_pass_denoise=0.35,
        sampler_name="euler",
        scheduler="beta",
        sampler=None,
    )
    second_pass = {}
    upscale_calls = []
    previous_tail = torch.full((1, 24, 12, 6, 12), 0.25, dtype=torch.float32)

    def fake_upscale(first_latent, *_args, **_kwargs):
        video, audio = _segment_latent_streams(first_latent)
        upscale_calls.append(int(video.shape[2]))
        return torch.zeros((1, 24, video.shape[2], 6, 12), dtype=torch.float32), audio
    def fake_sample(
        model,
        second_conditioning,
        second_latent,
        seed,
        sampler_name,
        scheduler,
        steps,
        denoise,
        **kwargs,
    ):
        second_pass.update({
            "conditioning": second_conditioning,
            "latent": second_latent,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "steps": steps,
            "denoise": denoise,
        })
        video, audio = _segment_latent_streams(second_latent)
        refined_video = torch.full_like(video, 0.75)
        return (_segment_pack_latent(refined_video, torch.ones_like(audio)),)

    with (
        patch(
            "aicg3d_h3easy.nodes.MiniMaxH3EasyRenderPass2._upscale_video_latent",
            side_effect=fake_upscale,
        ),
        patch(
            "aicg3d_h3easy.nodes._resize_keyframe_conditioning",
            return_value=conditioning,
        ),
        patch(
            "aicg3d_h3easy.aicg3d_sampler.AICG3DSamplerAdvanced.sample",
            side_effect=fake_sample,
        ),
    ):
        refined, continuity_video = MiniMaxH3EasySequenceSegment._apply_sequence_second_pass(
            first_latent,
            conditioning,
            config,
            SimpleNamespace(load_device=torch.device("cpu")),
            123,
            boundary_frames=39,
            previous_second_pass_tail=previous_tail,
        )

    refined_video, refined_audio = _segment_latent_streams(refined)
    assert tuple(refined_video.shape) == tuple(upscaled_video.shape)
    assert upscale_calls == [14], (
        "Pass 2 must upscale the complete temporal sequence so the learned "
        "5-token temporal convolutions never see a synthetic cut at the join"
    )
    assert tuple(continuity_video.shape) == tuple(first_video.shape)
    assert torch.count_nonzero(continuity_video) == 0, (
        "continuity must stay on the native Pass 1 grid instead of inheriting "
        "a downscaled Pass 2 tail, which softens the next segment"
    )
    assert torch.equal(refined_audio, first_audio)
    mask_video, mask_audio = _segment_av_streams(
        second_pass["latent"].get("noise_mask"),
        "Smart Drama second-pass AV mask is missing",
    )
    assert torch.all(mask_video[:, :, :12] == 0.0), (
        "the hidden handoff must stay bit-identical to the previous Pass 2 tail"
    )
    assert torch.all(mask_video[:, :, 12:] == 1.0)
    pass2_input_video, _pass2_input_audio = _segment_latent_streams(second_pass["latent"])
    assert torch.equal(pass2_input_video[:, :, :12], previous_tail), (
        "Pass 2 must start from the exact high-resolution tail of the previous segment"
    )
    assert torch.count_nonzero(mask_audio) == 0
    assert second_pass["sampler_name"] == "er_sde"
    assert second_pass["scheduler"] == "beta"
    assert second_pass["steps"] == 4
    assert abs(second_pass["denoise"] - 0.35) < 1e-6
    print("Smart Drama second pass: ok")


if __name__ == "__main__":
    main()
