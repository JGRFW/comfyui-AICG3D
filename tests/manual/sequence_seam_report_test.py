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
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.nodes import (  # noqa: E402
    _SEQUENCE_LIVE_CACHE,
    _SEQUENCE_LIVE_CACHE_LOCK,
    _SequenceSeamMatcher,
    MiniMaxH3SequenceSegment,
    _sequence_cache_read_chain,
    _sequence_collect_chain,
    _sequence_frame_luma,
    _sequence_handoff_context_frames,
    _sequence_stabilize_tail_exposure,
)


def _frames(value: float, count: int = 14) -> torch.Tensor:
    return torch.full((count, 48, 64, 3), float(value), dtype=torch.float32)


def _segment(index: int, node_id: str, previous=None) -> MiniMaxH3SequenceSegment:
    segment = object.__new__(MiniMaxH3SequenceSegment)
    object.__setattr__(segment, "index", index)
    object.__setattr__(segment, "node_id", node_id)
    object.__setattr__(segment, "previous", previous)
    return segment


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


def test_second_pass_disables_bridge_but_keeps_exposure_lock() -> None:
    matcher = _SequenceSeamMatcher(enabled=True, allow_motion_bridge=False)
    before = _frames(0.36)
    after = _frames(0.52)
    matcher.apply(before.clone(), 1)
    output = matcher.apply(after.clone(), 2)
    record = matcher.records[-1]

    assert record["applied"], record
    assert record["bridge_weight"] == 0.0, record
    assert record["seam_gap_after"] < record["seam_gap_before"], record
    assert not torch.equal(output, after), "exposure correction must stay enabled for Pass 2"


def test_tail_exposure_pulse_is_removed_before_handoff() -> None:
    matcher = _SequenceSeamMatcher(enabled=True, allow_motion_bridge=False)
    segment = _frames(0.50, count=24)
    segment[-1].fill_(0.46)
    repaired = matcher.apply(segment, 1)

    assert abs(_sequence_frame_luma(repaired[-1]) - 0.50) < 0.003
    assert abs(_sequence_frame_luma(matcher.previous_tail[-1]) - 0.50) < 0.003


def test_tail_exposure_high_pulse_is_removed_before_handoff() -> None:
    matcher = _SequenceSeamMatcher(enabled=True, allow_motion_bridge=False)
    segment = _frames(0.50, count=24)
    segment[-1].fill_(0.56)
    repaired = matcher.apply(segment, 1)

    assert abs(_sequence_frame_luma(repaired[-1]) - 0.50) < 0.003
    assert abs(_sequence_frame_luma(matcher.previous_tail[-1]) - 0.50) < 0.003


def test_tail_helper_leaves_real_fade_alone() -> None:
    segment = _frames(0.50, count=24)
    for index in range(8):
        segment[-(index + 1)].fill_(0.50 - index * 0.015)
    original = segment.clone()
    repaired, correction = _sequence_stabilize_tail_exposure(segment)

    assert correction == 0.0
    assert torch.equal(repaired, original)

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


def test_cache_chain_ignores_disconnected_stale_tail() -> None:
    from types import SimpleNamespace

    scope = "test:stale-tail"
    chain_key = "root:1"
    with _SEQUENCE_LIVE_CACHE_LOCK:
        for index in range(1, 5):
            _SEQUENCE_LIVE_CACHE[(scope, chain_key, index)] = SimpleNamespace(index=index)
    try:
        chain = _sequence_cache_read_chain(scope, chain_key, 3)
        assert [item.index for item in chain] == [1, 2, 3]
    finally:
        with _SEQUENCE_LIVE_CACHE_LOCK:
            for index in range(1, 5):
                _SEQUENCE_LIVE_CACHE.pop((scope, chain_key, index), None)


def test_non_contiguous_chain_accepts_skipped_middle_segments() -> None:
    first = _segment(1, "node-1")
    second = _segment(2, "node-2", first)
    tail = _segment(6, "node-6", second)
    chain = _sequence_collect_chain(tail)
    assert [item.index for item in chain] == [1, 2, 6]


def test_non_contiguous_chain_accepts_skipped_first_last_and_single_segment() -> None:
    second = _segment(2, "node-2")
    sixth = _segment(6, "node-6", second)
    assert [item.index for item in _sequence_collect_chain(sixth)] == [2, 6]
    assert [item.index for item in _sequence_collect_chain(second)] == [2]


def test_non_contiguous_chain_rejects_duplicate_or_descending_slots() -> None:
    first = _segment(1, "node-1")
    duplicate = _segment(1, "node-1b", first)
    descending = _segment(2, "node-2")
    earlier = _segment(1, "node-1c", descending)
    for tail in (duplicate, earlier):
        try:
            _sequence_collect_chain(tail)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid sequence slot order was accepted")


def test_cache_chain_reads_exact_effective_nodes_after_bypass() -> None:
    from types import SimpleNamespace

    scope = "test:bypass-chain"
    chain_key = "root:1"
    values = {
        1: SimpleNamespace(index=1, node_id="node-1"),
        2: SimpleNamespace(index=2, node_id="node-2"),
        6: SimpleNamespace(index=6, node_id="node-6"),
    }
    with _SEQUENCE_LIVE_CACHE_LOCK:
        for index, value in values.items():
            _SEQUENCE_LIVE_CACHE[(scope, chain_key, index)] = value
    try:
        chain = _sequence_cache_read_chain(
            scope,
            chain_key,
            len(values),
            [1, 2, 6],
            ["node-1", "node-2", "node-6"],
        )
        assert [item.index for item in chain] == [1, 2, 6]
    finally:
        with _SEQUENCE_LIVE_CACHE_LOCK:
            for index in values:
                _SEQUENCE_LIVE_CACHE.pop((scope, chain_key, index), None)


def test_cache_chain_uses_node_ids_when_runtime_slots_are_renumbered() -> None:
    from types import SimpleNamespace

    scope = "test:bypass-first-runtime-slots"
    chain_key = "node-2"
    values = {
        1: SimpleNamespace(index=1, node_id="node-2"),
        2: SimpleNamespace(index=2, node_id="node-3"),
        3: SimpleNamespace(index=3, node_id="node-4"),
    }
    with _SEQUENCE_LIVE_CACHE_LOCK:
        for index, value in values.items():
            _SEQUENCE_LIVE_CACHE[(scope, chain_key, index)] = value
    try:
        chain = _sequence_cache_read_chain(
            scope,
            chain_key,
            len(values),
            [2, 3, 4],
            ["node-2", "node-3", "node-4"],
        )
        assert [item.index for item in chain] == [1, 2, 3]
        assert [item.node_id for item in chain] == ["node-2", "node-3", "node-4"]
    finally:
        with _SEQUENCE_LIVE_CACHE_LOCK:
            for index in values:
                _SEQUENCE_LIVE_CACHE.pop((scope, chain_key, index), None)


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
        test_second_pass_disables_bridge_but_keeps_exposure_lock,
        test_tail_exposure_pulse_is_removed_before_handoff,
        test_tail_exposure_high_pulse_is_removed_before_handoff,
        test_tail_helper_leaves_real_fade_alone,
        test_real_scene_change_skips_spatial_blend,
        test_cache_chain_ignores_disconnected_stale_tail,
        test_non_contiguous_chain_accepts_skipped_middle_segments,
        test_non_contiguous_chain_accepts_skipped_first_last_and_single_segment,
        test_non_contiguous_chain_rejects_duplicate_or_descending_slots,
        test_cache_chain_reads_exact_effective_nodes_after_bypass,
        test_cache_chain_uses_node_ids_when_runtime_slots_are_renumbered,
        test_disabled_mode_only_reports,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} sequence seam checks")


if __name__ == "__main__":
    main()
