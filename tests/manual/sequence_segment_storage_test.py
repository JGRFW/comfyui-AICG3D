# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import nodes as h3_nodes  # noqa: E402
from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3EasySequenceGlobal,
    MiniMaxH3EasySequenceSegment,
)


class FakeVideo:
    def get_dimensions(self):
        return 64, 36

    def save_to(self, target, **_kwargs):
        Path(target).write_bytes(b"fake-mp4")


def _clear_tracking(scope: str, chain_key: str) -> None:
    with h3_nodes._SEQUENCE_SEGMENT_FILES_LOCK:
        h3_nodes._SEQUENCE_SEGMENT_FILES.pop((scope, chain_key), None)


def test_global_node_appends_storage_controls() -> None:
    required = MiniMaxH3EasySequenceGlobal.INPUT_TYPES()["required"]
    names = list(required)
    assert names[-2:] == ["segment_output_directory", "segment_cleanup_policy"]
    assert required["segment_output_directory"][1]["default"] == ""
    assert required["segment_cleanup_policy"][1]["default"] == h3_nodes.SEQUENCE_SEGMENT_CLEANUP_PROMPT
    assert set(h3_nodes.SEQUENCE_SEGMENT_CLEANUP_CHOICES) == {
        "合成后提示删除",
        "合成后自动删除",
        "保留分段视频",
    }


def test_directory_resolution_accepts_default_relative_and_absolute() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "output"
        output.mkdir()
        with patch.object(h3_nodes.folder_paths, "get_output_directory", return_value=str(output)):
            default = Path(h3_nodes._sequence_segment_output_directory(""))
            relative = Path(h3_nodes._sequence_segment_output_directory("cache/segments"))
            absolute_target = Path(tmp) / "elsewhere" / "segments"
            absolute = Path(h3_nodes._sequence_segment_output_directory(str(absolute_target)))

        assert default == (output / "AICG3D_H3_segments").resolve()
        assert relative == (output / "cache" / "segments").resolve()
        assert absolute == absolute_target.resolve()


def test_saved_segment_uses_selected_directory_and_replaces_old_redraw() -> None:
    scope = "test:scope:save"
    chain = "test-chain-save"
    _clear_tracking(scope, chain)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            selected = Path(tmp) / "chosen"
            temp_preview = Path(tmp) / "temp"
            temp_preview.mkdir()
            config = SimpleNamespace(segment_output_directory=str(selected))
            with patch.object(
                h3_nodes.folder_paths,
                "get_temp_directory",
                return_value=str(temp_preview),
            ):
                first, first_path = MiniMaxH3EasySequenceSegment._save_segment_video(
                    FakeVideo(), config, 2, scope, chain,
                )
                second, second_path = MiniMaxH3EasySequenceSegment._save_segment_video(
                    FakeVideo(), config, 2, scope, chain,
                )

            assert Path(first_path).parent == selected.resolve()
            assert Path(second_path).parent == selected.resolve()
            assert first_path != second_path
            assert not Path(first_path).exists()
            assert Path(second_path).read_bytes() == b"fake-mp4"
            assert first["type"] == second["type"] == "temp"
            assert second["persistent_path"] == second_path
    finally:
        _clear_tracking(scope, chain)


def test_prompt_cleanup_token_deletes_only_recorded_files() -> None:
    scope = "test:scope:prompt"
    chain = "test-chain-prompt"
    _clear_tracking(scope, chain)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "AICG3D_segment_0001_test.mp4"
            second = Path(tmp) / "AICG3D_segment_0002_test.mp4"
            neighbor = Path(tmp) / "user-file.mp4"
            for path in (first, second, neighbor):
                path.write_bytes(b"video")
            h3_nodes._sequence_track_segment_file(scope, chain, 1, str(first))
            h3_nodes._sequence_track_segment_file(scope, chain, 2, str(second))

            cleanup = h3_nodes._sequence_finalize_segment_files(
                scope,
                chain,
                h3_nodes.SEQUENCE_SEGMENT_CLEANUP_PROMPT,
                2,
            )
            assert cleanup["count"] == 2
            assert cleanup["token"]
            assert first.exists() and second.exists() and neighbor.exists()

            paths = h3_nodes._sequence_take_cleanup_token(cleanup["token"])
            assert paths is not None
            deleted, failed = h3_nodes._sequence_delete_files(paths)
            assert (deleted, failed) == (2, 0)
            assert not first.exists() and not second.exists()
            assert neighbor.exists()
    finally:
        _clear_tracking(scope, chain)


def test_auto_cleanup_respects_segment_limit_and_keep_policy() -> None:
    scope = "test:scope:auto"
    chain = "test-chain-auto"
    _clear_tracking(scope, chain)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            files = [
                Path(tmp) / f"AICG3D_segment_{index:04d}_test.mp4"
                for index in (1, 2, 3)
            ]
            for index, path in enumerate(files, start=1):
                path.write_bytes(b"video")
                h3_nodes._sequence_track_segment_file(scope, chain, index, str(path))

            keep = h3_nodes._sequence_finalize_segment_files(
                scope,
                chain,
                h3_nodes.SEQUENCE_SEGMENT_CLEANUP_KEEP,
                2,
            )
            assert keep["count"] == 2
            assert all(path.exists() for path in files)

            auto = h3_nodes._sequence_finalize_segment_files(
                scope,
                chain,
                h3_nodes.SEQUENCE_SEGMENT_CLEANUP_AUTO,
                2,
            )
            assert auto["deleted"] == 2
            assert not files[0].exists() and not files[1].exists()
            assert files[2].exists()
    finally:
        _clear_tracking(scope, chain)


def test_cleanup_uses_runtime_indices_after_middle_bypass() -> None:
    scope = "test:scope:bypass"
    chain = "test-chain-bypass"
    _clear_tracking(scope, chain)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            files = {
                index: Path(tmp) / f"AICG3D_segment_{index:04d}_test.mp4"
                for index in range(1, 7)
            }
            for index, path in files.items():
                path.write_bytes(b"video")
                h3_nodes._sequence_track_segment_file(scope, chain, index, str(path))

            # UI keeps slots 1,2,6 while ComfyUI executes the surviving chain as
            # runtime slots 1,2,3. Node IDs restore the right cache objects, and
            # cleanup must follow those runtime slots instead of deleting slot 6.
            cleanup = h3_nodes._sequence_finalize_segment_files(
                scope,
                chain,
                h3_nodes.SEQUENCE_SEGMENT_CLEANUP_PROMPT,
                3,
                [1, 2, 3],
            )
            assert cleanup["count"] == 3
            paths = h3_nodes._sequence_take_cleanup_token(cleanup["token"])
            assert paths is not None
            deleted, failed = h3_nodes._sequence_delete_files(paths)
            assert (deleted, failed) == (3, 0)
            assert not files[1].exists()
            assert not files[2].exists()
            assert not files[3].exists()
            assert files[4].exists()
            assert files[5].exists()
            assert files[6].exists()
    finally:
        _clear_tracking(scope, chain)


def main() -> None:
    tests = (
        test_global_node_appends_storage_controls,
        test_directory_resolution_accepts_default_relative_and_absolute,
        test_saved_segment_uses_selected_directory_and_replaces_old_redraw,
        test_prompt_cleanup_token_deletes_only_recorded_files,
        test_auto_cleanup_respects_segment_limit_and_keep_policy,
        test_cleanup_uses_runtime_indices_after_middle_bypass,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} sequence segment storage checks")


if __name__ == "__main__":
    main()
