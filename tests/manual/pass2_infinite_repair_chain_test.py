# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify that 1.0x restoration nodes can be chained without H3 resampling."""

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
    PASS2_REPAIR_OFF,
    PASS2_REPAIR_SEEDVR2,
    _segment_latent_streams,
    _segment_pack_latent,
)


def main() -> None:
    required = MiniMaxH3EasyRenderPass2.INPUT_TYPES()["required"]
    assert required["repair_engine"][1]["default"] == PASS2_REPAIR_OFF
    assert PASS2_REPAIR_SEEDVR2 in required["repair_engine"][0]
    assert required["repair_scale"][1]["default"] == 1.0

    first_video = torch.zeros((1, 24, 2, 4, 8), dtype=torch.float32)
    first_audio = torch.arange(32, dtype=torch.float32).reshape(1, 32, 1, 1) / 32
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

    repaired_one = torch.full((1, 24, 2, 4, 8), 0.25, dtype=torch.float32)
    repaired_two = torch.full((1, 24, 2, 4, 8), 0.75, dtype=torch.float32)
    queued = [repaired_one, repaired_two]
    captured_inputs: list[torch.Tensor] = []
    engine_calls: list[dict] = []

    def fake_repair(_context, video_latent, **kwargs):
        captured_inputs.append(video_latent.clone())
        engine_calls.append(dict(kwargs))
        return queued.pop(0)

    def sampler_must_not_run(*_args, **_kwargs):
        raise AssertionError("独立修复引擎启用时不应再跑 H3 二采")

    with (
        patch.object(
            MiniMaxH3EasyRenderPass2,
            "_repair_video_latent",
            side_effect=fake_repair,
        ),
        patch(
            "aicg3d_h3easy.aicg3d_sampler.AICG3DSamplerAdvanced.sample",
            side_effect=sampler_must_not_run,
        ),
        patch.object(
            MiniMaxH3EasyRenderPass2,
            "_decode_av",
            return_value=(
                torch.zeros((1, 2, 4, 4, 3)),
                {"waveform": torch.zeros(1, 1, 2), "sample_rate": 24000},
            ),
        ),
        patch.object(MiniMaxH3EasyRenderPass2, "_compose_video", return_value="VIDEO"),
        patch("aicg3d_h3easy.nodes._release_render_resources"),
    ):
        first_result = MiniMaxH3EasyRenderPass2().render(
            {"latent": first_latent, "context": context},
            sampler_name="euler",
            scheduler="beta",
            steps=4,
            second_pass_seed=123,
            second_pass_denoise=0.3,
            latent_upscale_model="unused.safetensors",
            upscale_scale=1.0,
            repair_engine=PASS2_REPAIR_SEEDVR2,
            repair_model="auto",
            repair_scale=1.0,
            tiled_sampling="关",
            sample_preview="关",
            output_first_pass="关",
            cleanup_after_run="不处理",
        )
        second_result = MiniMaxH3EasyRenderPass2().render(
            first_result[0],
            sampler_name="euler",
            scheduler="beta",
            steps=4,
            second_pass_seed=124,
            second_pass_denoise=0.3,
            latent_upscale_model="unused.safetensors",
            upscale_scale=1.0,
            repair_engine=PASS2_REPAIR_SEEDVR2,
            repair_model="auto",
            repair_scale=1.0,
            tiled_sampling="关",
            sample_preview="关",
            output_first_pass="关",
            cleanup_after_run="不处理",
        )

    assert len(engine_calls) == 2
    assert all(call["scale"] == 1.0 for call in engine_calls)
    assert torch.equal(captured_inputs[0], first_video)
    assert torch.equal(captured_inputs[1], repaired_one)

    first_output_video, first_output_audio = _segment_latent_streams(first_result[0]["latent"])
    second_output_video, second_output_audio = _segment_latent_streams(second_result[0]["latent"])
    assert torch.equal(first_output_video, repaired_one)
    assert torch.equal(second_output_video, repaired_two)
    assert torch.equal(first_output_audio, first_audio)
    assert torch.equal(second_output_audio, first_audio)
    print("Pass2 infinite 1.0x restoration chain: ok")


if __name__ == "__main__":
    main()
