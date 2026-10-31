# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Voice cast contracts for the infinite sequence workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3CharacterVoiceCast,
    MiniMaxH3CharacterVoiceRole,
    MiniMaxH3EasyCharacterVoiceLibrary,
    _MediaInput,
    _apply_character_voice_cast,
    _voice_cast_normalize_state,
)


def test_default_cast_has_six_fixed_speakers() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    assert isinstance(cast, MiniMaxH3CharacterVoiceCast)
    assert [role.role_id for role in cast.roles] == [
        "girl",
        "boy",
        "heroine",
        "hero",
        "old_woman",
        "old_man",
    ]


def test_only_mentioned_roles_are_injected() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    items, prompt = _apply_character_voice_cast(
        "@女孩 对 @女主角 说：<d>[Chinese] 你好。</d>",
        [],
        cast,
    )
    assert items == []
    assert "S1 = 女孩" in prompt
    assert "S3 = 女主角" in prompt
    assert "S2 = 男孩" not in prompt
    assert "@女孩" not in prompt
    assert "S1（女孩）" in prompt
    assert "S3（女主角）" in prompt


def test_reference_state_keeps_trim_duration() -> None:
    state = _voice_cast_normalize_state({
        "version": 1,
        "roles": [{
            "id": "girl",
            "mode": "reference",
            "reference": "voice/girl.wav",
            "reference_start": 2.5,
            "reference_duration": 7.0,
            "rights_confirmed": True,
            "picture_index": 2,
        }],
    })
    girl = state["roles"][0]
    assert girl["mode"] == "reference"
    assert girl["reference"] == "voice/girl.wav"
    assert girl["reference_start"] == 2.5
    assert girl["reference_duration"] == 7.0
    assert girl["rights_confirmed"] is True
    assert girl["picture_index"] == 2


def test_h3_audio_reference_budget_is_enforced() -> None:
    roles = tuple(
        MiniMaxH3CharacterVoiceRole(
            role_id=f"role-{index}",
            name=f"角色{index}",
            mode="reference",
            description="test",
            language="Chinese",
            age="adult",
            gender="neutral",
            pitch="medium",
            pace="natural",
            reference_filename=f"voice-{index}.wav",
            reference_item=_MediaInput(index, "audio", {}),
            rights_confirmed=True,
        )
        for index in range(1, 5)
    )
    cast = MiniMaxH3CharacterVoiceCast(roles)
    prompt = "、".join(f"@{role.name}" for role in roles)
    try:
        _apply_character_voice_cast(prompt, [_MediaInput(0, "image", object())], cast)
    except ValueError as exc:
        assert "最多接受 3 条音频" in str(exc)
    else:
        raise AssertionError("Four cloned voices should exceed the H3 audio reference budget")


def main() -> None:
    tests = (
        test_default_cast_has_six_fixed_speakers,
        test_only_mentioned_roles_are_injected,
        test_reference_state_keeps_trim_duration,
        test_h3_audio_reference_budget_is_enforced,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} voice cast checks")


if __name__ == "__main__":
    main()
