# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression checks for the renderer's V2 two-pass latent upscale path."""

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
    MiniMaxH3EasyRenderAdvanced,
    MiniMaxH3EasyRenderPass2,
    MiniMaxH3EasyRenderPass1,
    MiniMaxH3EasyRenderAdvancedWithModel,
    _apply_secondary_refiner_lora,
    _resolve_h3_secondary_upscaler,
    _segment_av_streams,
    _segment_latent_streams,
    _segment_pack_latent,
)


def main() -> None:
    required = MiniMaxH3EasyRenderAdvancedWithModel.INPUT_TYPES()["required"]
    scale_spec = required["digital_human_upscale_scale"]
    widget_order = list(required)
    assert widget_order.index("digital_human_upscale_scale") == (
        widget_order.index("digital_human_selflift") + 1
    )
    assert scale_spec[0] == "FLOAT"
    assert scale_spec[1]["default"] == 1.5
    assert scale_spec[1]["min"] == 1.0
    assert scale_spec[1]["max"] == 4.0
    refiner_spec = required["digital_human_refiner_lora"]
    assert refiner_spec[1]["default"] == "none"
    refiner_name = "minimax\\minimax_h3_open_regenerate_2k_refiner_rank_384_bf16.safetensors"
    assert refiner_name in refiner_spec[0]
    source_model = object()
    patched_model = object()
    with patch("aicg3d_h3easy.nodes.nodes.LoraLoaderModelOnly") as loader_cls:
        loader_cls.return_value.load_lora_model_only.return_value = (patched_model,)
        assert _apply_secondary_refiner_lora(source_model, refiner_name) is patched_model
        loader_cls.return_value.load_lora_model_only.assert_called_once_with(
            source_model, refiner_name, 1.0
        )
    assert _apply_secondary_refiner_lora(source_model, "none") is source_model
    assert MiniMaxH3EasyRenderPass2.RETURN_TYPES == ("AICG3D_H3_PASS1", "VIDEO", "VIDEO")
    assert "run_nonce" in MiniMaxH3EasyRenderPass1.INPUT_TYPES()["required"]
    assert MiniMaxH3EasyRenderPass1.RETURN_NAMES == ("pass1", "video")
    assert MiniMaxH3EasyRenderPass2.RETURN_NAMES == ("pass_data", "first_pass_video", "video")

    v1 = "minimax_h3_latent_upscaler_3d_fp16.safetensors"
    v2 = "minimax_h3_latent_upscaler_3d_fp16_V2.safetensors"
    if v2 in scale_spec[0]:
        assert scale_spec[1]["default"] == v2
        assert _resolve_h3_secondary_upscaler(v1) == v2

    first_video = torch.zeros((1, 24, 2, 4, 8), dtype=torch.float32)
    first_audio = torch.zeros((1, 32, 2, 1), dtype=torch.float32)
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
    )
    second_pass = {}

    def fake_secondary_sample(
        second_model,
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
            "steps": steps,
            "denoise": denoise,
            "seed": seed,
            "conditioning": second_conditioning,
            "latent": second_latent,
        })
        video, audio = _segment_latent_streams(second_latent)
        corrupted_audio = torch.ones_like(audio)
        return (_segment_pack_latent(video, corrupted_audio),)

    with (
        patch(
            "aicg3d_h3easy.nodes.MiniMaxH3EasyRenderPass2._upscale_video_latent",
            return_value=(upscaled_video, first_audio),
        ),
        patch(
            "aicg3d_h3easy.nodes.MiniMaxH3EasySecondPassConditioning.rebuild_from_conditioning",
            return_value=(positive,),
        ),
        patch(
            "aicg3d_h3easy.aicg3d_sampler.AICG3DSamplerAdvanced.sample",
            side_effect=fake_secondary_sample,
        ),
    ):
        refined = MiniMaxH3EasyRenderAdvanced._run_secondary_sample(
            first_latent=first_latent,
            first_conditioning=positive,
            h3_context=context,
            highres_model=SimpleNamespace(load_device=torch.device("cpu")),
            seed=456,
            sampler_name="euler",
            scheduler="beta",
            second_steps=8,
            second_denoise=0.8,
            upscaler_model=v2,
            output_scale=1.5,
        )

    refined_video, refined_audio = _segment_latent_streams(refined)
    assert tuple(refined_video.shape) == tuple(upscaled_video.shape)
    assert torch.equal(refined_audio, first_audio)
    mask_video, mask_audio = _segment_av_streams(
        second_pass["latent"].get("noise_mask"),
        "Second-pass AV mask is missing",
    )
    assert torch.all(mask_video > 0)
    assert torch.count_nonzero(mask_audio) == 0
    assert second_pass["steps"] == 6
    assert abs(second_pass["denoise"] - 0.35) < 1e-6
    assert second_pass["seed"] == 456
    print("V2 two-pass latent upscale: ok")


if __name__ == "__main__":
    main()
