# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression checks for reference-conditioned Motion Context handoffs."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import torch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import nodes as h3_nodes  # noqa: E402


def main() -> None:
    image = SimpleNamespace(media_type="image")
    video = SimpleNamespace(media_type="video")
    audio = SimpleNamespace(media_type="audio")

    assert h3_nodes._segment_has_visual_reference([image])
    assert h3_nodes._segment_has_visual_reference((video,))
    assert not h3_nodes._segment_has_visual_reference([audio])
    assert not h3_nodes._segment_has_visual_reference(None)

    # 13 号工作流当前使用 39 帧 Motion Context。
    context_frames = 39
    context_tokens = int(h3_nodes.h3.temporal_shape(context_frames)[1])
    generator = torch.Generator().manual_seed(0)
    latent = torch.randn(1, 24, context_tokens, 16, 16, generator=generator)
    # 每个通道一个固定的平均色偏移：通道均值 = 该 token 的平均亮度 / 色偏。
    # H3 VAE 在 encode 时会减掉 latents_mean 再做缩放，所以这个偏移就是
    # 解码后画面相对“数据集平均画面”的亮度差。
    latent = latent + torch.arange(24).view(1, 24, 1, 1, 1) * 0.5

    text_only = h3_nodes._segment_prepare_motion_context_guide(
        latent, context_frames, 17, []
    )
    audio_only = h3_nodes._segment_prepare_motion_context_guide(
        latent, context_frames, 17, [audio]
    )
    assert text_only is latent
    assert audio_only is latent

    first = h3_nodes._segment_prepare_motion_context_guide(
        latent, context_frames, 17, [image]
    )
    repeated = h3_nodes._segment_prepare_motion_context_guide(
        latent, context_frames, 17, [image]
    )
    assert first is not latent
    assert first.shape == latent.shape
    assert torch.equal(first, repeated)
    # 默认 alpha = 0：这些 token 是干净条件帧，掺进去的噪声洗不掉，所以锚点
    # 必须原样返回。段与段之间的色差就是从这里回来的，改动时不要放宽这条。
    assert torch.equal(first, latent)

    tail_start = int(latent.shape[2]) - context_tokens
    if tail_start > 0:
        assert torch.equal(first[:, :, :tail_start], latent[:, :, :tail_start])

    # 显式开启 taper 时的契约：只动尾部 token、同 seed 确定性、并且每个 token
    # 的平均亮度/色偏不被拉向数据集均值（旧实现会乘 (1 - alpha)，必须更小）。
    saved_alpha = h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA
    saved_end = h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA_END
    saved_dc = h3_nodes.SEGMENT_CONTEXT_NOISE_PRESERVE_DC
    h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA = 0.45
    h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA_END = 0.10
    try:
        h3_nodes.SEGMENT_CONTEXT_NOISE_PRESERVE_DC = False
        legacy = h3_nodes._segment_prepare_motion_context_guide(
            latent, context_frames, 17, [image]
        )
        h3_nodes.SEGMENT_CONTEXT_NOISE_PRESERVE_DC = True
        noised = h3_nodes._segment_prepare_motion_context_guide(
            latent, context_frames, 17, [image]
        )
        again = h3_nodes._segment_prepare_motion_context_guide(
            latent, context_frames, 17, [image]
        )
        assert torch.equal(noised, again)
        assert torch.equal(noised[:, :, :tail_start], latent[:, :, :tail_start])
        assert not torch.equal(noised[:, :, tail_start:], latent[:, :, tail_start:])

        base_mean = latent[:, :, tail_start:].mean(dim=(-2, -1))
        kept_mean = noised[:, :, tail_start:].mean(dim=(-2, -1))
        legacy_mean = legacy[:, :, tail_start:].mean(dim=(-2, -1))
        assert (kept_mean - base_mean).abs().mean() < 0.15
        assert (legacy_mean - base_mean).abs().max() > 1.0
        assert (
            (kept_mean - base_mean).abs().max()
            < (legacy_mean - base_mean).abs().max() * 0.25
        )
    finally:
        h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA = saved_alpha
        h3_nodes.SEGMENT_CONTEXT_NOISE_ALPHA_END = saved_end
        h3_nodes.SEGMENT_CONTEXT_NOISE_PRESERVE_DC = saved_dc

    print("Reference-conditioned Motion Context noise: ok")


if __name__ == "__main__":
    main()
