# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify the segment-card preview picks a moving frame instead of latent t=0."""

from __future__ import annotations

import sys
from pathlib import Path

import torch
from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.render_progress import RenderPreviewEncoder  # noqa: E402


class RecordingPreviewer:
    """Stand-in for TAEHVPreviewerImpl: ComfyUI 的视频预览器只解第 0 个时刻。"""

    def __init__(self) -> None:
        self.calls = []

    def decode_latent_to_preview_image(self, preview_format, latent):
        assert preview_format == "JPEG"
        self.calls.append(latent)
        return ("JPEG", Image.new("RGB", (8, 8), (10, 20, 30)), 512)


def main() -> None:
    encoder = RenderPreviewEncoder.__new__(RenderPreviewEncoder)
    encoder.max_side = 512
    previewer = RecordingPreviewer()
    encoder._previewer = previewer

    tokens = 52
    # 每个 latent 时刻填自己序号，方便断言「到底解了第几个时刻」。
    latent = (
        torch.arange(tokens, dtype=torch.float32)
        .view(1, 1, tokens, 1, 1)
        .expand(1, 24, tokens, 54, 30)
        .contiguous()
    )

    def probe(position):
        previewer.calls.clear()
        image = encoder.decode(latent, position=position)
        assert image is not None
        assert len(previewer.calls) == 1
        picked = previewer.calls[0]
        return picked, float(picked[:, :, 0, 0, 0].flatten()[0])

    # 不给位置：沿用原生行为，整段 latent 交给预览器（它自己取第 0 个时刻）。
    picked, index = probe(None)
    assert picked.shape[2] == tokens, picked.shape
    assert index == 0.0

    # 给位置：只解一个时刻，并且随位置推进。
    for position, expected in (
        (0.0, 0.0),
        (0.125, 6.0),
        (0.25, 13.0),
        (0.5, 26.0),
        (0.75, 38.0),
        (1.0, 51.0),
    ):
        picked, index = probe(position)
        assert picked.shape[2] == 1, picked.shape
        assert index == expected, (position, index, expected)

    # 越界位置必须被夹住，不能抛异常。
    assert probe(-0.5)[1] == 0.0
    assert probe(2.0)[1] == 51.0

    # 只有单个时刻时不做切片（切了也是它自己）。
    short = latent[:, :, :1]
    previewer.calls.clear()
    assert encoder.decode(short, position=0.7) is not None
    assert previewer.calls[0].shape[2] == 1

    # 4D / None / 没有预览器时都要安全返回。
    assert encoder.decode(torch.zeros(1, 24, 8, 8), position=0.5) is not None
    assert encoder.decode(None) is None
    encoder._previewer = None
    assert encoder.decode(latent, position=0.5) is None

    print("Sequence preview frame sweep: ok")


if __name__ == "__main__":
    main()
