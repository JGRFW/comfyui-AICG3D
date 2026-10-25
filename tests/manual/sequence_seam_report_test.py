# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pure seam-repair checks for the 13 sequence workflow.

Run from the ComfyUI root with its bundled virtual environment:
    .venv\\Scripts\\python.exe custom_nodes\\comfyui-AICG3D\\tests\\manual\\sequence_seam_report_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from aicg3d_h3easy.nodes import (  # noqa: E402
    _SequenceSeamMatcher,
    _sequence_handoff_context_frames,
)


def _frames(value: float, count: int = 14) -> torch.Tensor:
    return torch.full((count, 48, 64, 3), float(value), dtype=torch.float32)


def test_handoff_grid() -> None:
    cases = {
        1: 5,
        5: 5,
        6: 22,
        22: 22,
        23: 39,
        39: 39,
        40: 56,
        56: 56,
    }
    actual = {value: _sequence_handoff_context_frames(value) for value in cases}
    assert actual == cases, actual


def test_same_shot_exposure_is_repaired() -> None:
    matcher = _SequenceSeamMatcher(enabled=True)
    before = _frames(0.36)
    after = _frames(0.52)
    matcher.apply(before.clone(), 1)
    output = matcher.apply(after.clone(), 2)
    record = matcher.records[-1]

    assert not record["hard_cut"], record
    assert record["applied"], record
    assert record["seam_gap_after"] < record["seam_gap_before"], record
    assert not torch.equal(output, after), "same-shot exposure should be corrected"


def test_real_scene_change_skips_spatial_blend() -> None:
    generator = torch.Generator().manual_seed(20261025)
    previous = torch.rand((14, 64, 64, 3), generator=generator)
    current = torch.rand((14, 64, 64, 3), generator=generator)


    matcher = _SequenceSeamMatcher(enabled=True)
    matcher.apply(previous, 1)
    output = matcher.apply(current, 2)
    record = matcher.records[-1]

    assert record["hard_cut"], record
    assert record["bridge_weight"] == 0.0, record
    assert record["status"] == "硬切保护", record
    assert output.shape == current.shape


def test_disabled_mode_only_reports() -> None:
    matcher = _SequenceSeamMatcher(enabled=False)
    matcher.apply(_frames(0.30), 1)
    current = _frames(0.55)
    original = current.clone()
    output = matcher.apply(current, 2)

    assert torch.equal(output, original), "disabled exposure lock must not alter frames"
    assert matcher.records[-1]["status"] == "仅检测"
    report = matcher.format_report(2, 28, 24.0, 39, "尾帧续写（latent）")
    assert "跨段曝光锁定关闭" in report
    assert "2→2" not in report
    assert "1→2" in report


def main() -> None:
    tests = (
        test_handoff_grid,
        test_same_shot_exposure_is_repaired,
        test_real_scene_change_skips_spatial_blend,
        test_disabled_mode_only_reports,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} sequence seam checks")


if __name__ == "__main__":
    main()
