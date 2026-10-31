# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Release audit for the fixed character voice library integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def test_voice_library_backend_contract() -> None:
    from aicg3d_h3easy.nodes import (
        MiniMaxH3Easy,
        MiniMaxH3EasyCharacterVoiceLibrary,
        MiniMaxH3EasySequenceSegment,
    )

    assert "voice_state" in MiniMaxH3EasyCharacterVoiceLibrary.INPUT_TYPES()["required"]
    optional = MiniMaxH3EasySequenceSegment.INPUT_TYPES().get("optional", {})
    assert "voice_cast" in optional
    assert optional["voice_cast"][0] == "AICG3D_CHARACTER_VOICE_CAST"
    main_optional = MiniMaxH3Easy.INPUT_TYPES().get("optional", {})
    assert "voice_cast" in main_optional
    assert main_optional["voice_cast"][0] == "AICG3D_CHARACTER_VOICE_CAST"


def test_voice_submission_bridge_guards_cached_redraw() -> None:
    bridge = (PLUGIN_ROOT / "web" / "aicg3d_voice_bridge_v1.js").read_text(encoding="utf-8")
    assert '__AICG3D_VOICE_CAST_SUBMISSION_PATCHED' in bridge
    assert "promptNode.inputs.voice_cast = [String(source.id), 0]" in bridge
    assert "cached previous" in bridge
    assert "voiceLibraryForSegment" in bridge
    assert "input.link = null" in bridge
    assert "mode !== 2 && mode !== 4" in bridge
    assert "delete promptNode.inputs.voice_cast" in bridge


def test_voice_cast_node_is_strictly_optional() -> None:
    from aicg3d_h3easy.nodes import (
        MiniMaxH3Easy,
        MiniMaxH3EasySequenceSegment,
        _MediaInput,
        _apply_character_voice_cast,
    )

    required = MiniMaxH3EasySequenceSegment.INPUT_TYPES()["required"]
    optional = MiniMaxH3EasySequenceSegment.INPUT_TYPES()["optional"]
    assert "voice_cast" not in required
    assert "voice_cast" in optional
    assert "voice_cast" not in MiniMaxH3Easy.INPUT_TYPES()["required"]
    assert "voice_cast" in MiniMaxH3Easy.INPUT_TYPES()["optional"]
    items = [_MediaInput(1, "image", object())]
    result_items, result_prompt = _apply_character_voice_cast(
        "plain prompt", list(items), None
    )
    assert result_items == items
    assert result_prompt == "plain prompt"
    source = (PLUGIN_ROOT / "aicg3d_h3easy" / "nodes.py").read_text(encoding="utf-8")
    assert "inherited_cast = previous_segment.sample.voice_cast" not in source


def test_voice_library_ui_and_workflows_are_packaged() -> None:
    voice_ui = PLUGIN_ROOT / "web" / "aicg3d_voice_library.js"
    voice_bridge = PLUGIN_ROOT / "web" / "aicg3d_voice_bridge_v1.js"
    voice_preview = PLUGIN_ROOT / "web" / "aicg3d_voice_preview.js"
    assert voice_ui.is_file()
    assert voice_bridge.is_file()
    assert voice_preview.is_file()
    assert "@角色${role.seat}" in voice_ui.read_text(encoding="utf-8")
    voice_ui_source = voice_ui.read_text(encoding="utf-8")
    assert 'if (role.mode !== "reference") {' in voice_ui_source
    assert "panel.append(descriptionBox);" in voice_ui_source
    backend_source = (PLUGIN_ROOT / "aicg3d_h3easy" / "nodes.py").read_text(encoding="utf-8")
    assert "timbre is defined only by the attached " in backend_source
    preview_source = voice_preview.read_text(encoding="utf-8")
    assert "/aicg3d/api/voice-preview-spark" in preview_source
    assert "reference_source = payload.source" in preview_source
    assert "/aicg3d/api/voice-preview/delete" in preview_source
    assert "清除生成音色" in preview_source
    assert "应用到提示词" in preview_source
    assert "固定角色音色库" in voice_ui.read_text(encoding="utf-8")

    for workflow in (
        "11.AICG3D_多参考-首尾帧-数字人.json",
        "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json",
        "13.AICG3D_参考无限生成视频.json",
        "13.AICG3D_无限分段 生视频.json",
    ):
        data = json.loads((PLUGIN_ROOT / "workflows" / workflow).read_text(encoding="utf-8"))
        types = {node.get("type") for node in data.get("nodes", [])}
        assert "AICG3D_H3CharacterVoiceLibrary" in types, workflow


def main() -> None:
    tests = (
        test_voice_library_backend_contract,
        test_voice_submission_bridge_guards_cached_redraw,
        test_voice_cast_node_is_strictly_optional,
        test_voice_library_ui_and_workflows_are_packaged,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} voice release audit checks")


if __name__ == "__main__":
    main()
