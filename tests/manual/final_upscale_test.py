# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = ROOT.parents[1]
for path in (str(COMFY_ROOT), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.final_upscale import MiniMaxH3EasyFinalHighResUpscale as Node


def test_window_plan_covers_every_frame_once() -> None:
    for total_frames in (1, 38, 39, 300, 362, 363, 700, 1000, 2500):
        for max_frames in (39, 90, 362, 900):
            for overlap in (0, 4, 24, 120):
                plans = Node._window_plan(total_frames, max_frames, overlap)
                kept = [(start, end) for _decode_start, _decode_end, start, end in plans]
                assert kept[0][0] == 0
                assert kept[-1][1] == total_frames
                assert all(start < end for start, end in kept)
                assert all(left[1] == right[0] for left, right in zip(kept, kept[1:]))


def test_window_plan_reuses_context_without_mixing_output() -> None:
    plans = Node._window_plan(1000, 362, 24)
    assert len(plans) == 3
    first_decode_start, first_decode_end, first_keep_start, first_keep_end = plans[0]
    second_decode_start, _second_decode_end, second_keep_start, _second_keep_end = plans[1]
    assert first_decode_start == first_keep_start == 0
    assert first_keep_end == second_keep_start
    assert second_decode_start < first_decode_end
    assert first_keep_end <= first_decode_end


def test_exposure_lock_matches_source_luminance() -> None:
    reference = torch.full((2, 16, 16, 3), 0.25, dtype=torch.float32)
    processed = torch.full((2, 16, 16, 3), 0.28, dtype=torch.float32)
    corrected = Node._lock_exposure(processed, reference)
    luminance = (corrected[..., :3] * torch.tensor([0.2126, 0.7152, 0.0722])).sum(-1).mean()
    expected = 0.25
    assert abs(float(luminance) - expected) < 1e-3


def test_exposure_lock_preserves_frame_count() -> None:
    reference = torch.rand((7, 12, 10, 3), dtype=torch.float32)
    processed = torch.rand((7, 24, 20, 3), dtype=torch.float32)
    corrected = Node._lock_exposure(processed, reference)
    assert corrected.shape == processed.shape


if __name__ == "__main__":
    test_window_plan_covers_every_frame_once()
    test_window_plan_reuses_context_without_mixing_output()
    test_exposure_lock_matches_source_luminance()
    test_exposure_lock_preserves_frame_count()
    print("final_upscale_test: ok")
