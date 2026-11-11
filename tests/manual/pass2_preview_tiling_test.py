# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check Pass2 control order and the real tiled-sampling dispatch."""

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
    MiniMaxH3EasySegmentRefine,
)


def main() -> None:
    required = MiniMaxH3EasyRenderPass2.INPUT_TYPES()["required"]
    order = list(required)
    assert order.index("sample_preview") < order.index("preview_interval")
    assert order.index("preview_interval") < order.index("upscale_mode")
    assert order.index("upscale_mode") < order.index("target_width")
    assert order.index("target_width") < order.index("target_height")
    assert order.index("target_height") < order.index("repair_engine")
    assert order.index("tiled_sampling") < order.index("latent_upscale_model")

    sentinel = object()
    captured = {}

    def fake_tiled_sample(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel

    with (
        patch.object(MiniMaxH3EasySegmentRefine, "_tiled_pass_count", return_value=2),
        patch.object(MiniMaxH3EasySegmentRefine, "_tiled_sample", side_effect=fake_tiled_sample),
    ):
        result = MiniMaxH3EasyRenderPass2._tiled_second_pass(
            object(),
            [[torch.zeros((1, 8), dtype=torch.float32), {}]],
            "packed-av-latent",
            torch.zeros((1, 24, 2, 4, 8), dtype=torch.float32),
            "euler",
            "simple",
            4,
            0.35,
            123,
            512,
            512,
            128,
            32,
            object(),
            sampler=object(),
            sigmas=torch.tensor([1.0, 0.5, 0.2], dtype=torch.float32),
        )

    assert result is sentinel
    args = captured["args"]
    assert args[9:13] == (512, 512, 128, 32)
    print("Pass2 preview order and tiled sampling dispatch: ok")


if __name__ == "__main__":
    main()
