# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Voice cast contracts for the infinite sequence workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
if str(COMFY_ROOT) not in sys.path:
    sys.path.insert(0, str(COMFY_ROOT))

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3CharacterVoiceCast,
    MiniMaxH3CharacterVoiceRole,
    MiniMaxH3EasyCharacterVoiceLibrary,
    _MediaInput,
    _apply_character_voice_cast,
    _resolve_sequence_voice_cast,
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


def test_disabled_library_skips_validation_and_returns_no_roles() -> None:
    library = MiniMaxH3EasyCharacterVoiceLibrary()
    invalid_state = {
        "version": 1,
        "roles": [{
            "id": "girl",
            "mode": "reference",
            "reference": "",
            "rights_confirmed": False,
        }],
    }
    invalid_json = json.dumps(invalid_state, ensure_ascii=False)
    assert "没有参考音频" in library.VALIDATE_INPUTS(voice_state=invalid_json, enabled=True)
    assert library.VALIDATE_INPUTS(voice_state=invalid_json, enabled=False) is True
    cast, report = library.load(voice_state=invalid_json, enabled=False)
    assert isinstance(cast, MiniMaxH3CharacterVoiceCast)
    assert cast.roles == ()
    assert json.loads(report)["enabled"] is False

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


def test_sequence_inherits_same_cloned_voice_without_repeating_at_role() -> None:
    girl = MiniMaxH3CharacterVoiceRole(
        role_id="girl",
        name="女孩",
        mode="reference",
        description="Q版小女孩，儿童声线",
        language="Chinese",
        age="child",
        gender="female",
        pitch="high",
        pace="natural",
        reference_filename="voice/girl.wav",
        reference_item=_MediaInput(1, "audio", {}),
        rights_confirmed=True,
    )
    cast = MiniMaxH3CharacterVoiceCast((girl,))
    previous = SimpleNamespace(
        voice_cast=cast,
        sample=SimpleNamespace(active_voice_ids=("girl",)),
    )
    active_cast, active_ids = _resolve_sequence_voice_cast(
        "她继续小声说：<d>[Chinese] 别怕。</d>",
        None,
        previous,
    )
    assert active_cast is cast
    assert active_ids == ("girl",)
    items, prompt = _apply_character_voice_cast(
        "她继续小声说：<d>[Chinese] 别怕。</d>",
        [_MediaInput(0, "image", object())],
        active_cast,
        forced_role_ids=active_ids,
    )
    assert len(items) == 2
    assert items[-1].media_type == "audio"
    assert "S1 = 女孩" in prompt
    assert "timbre reference <Audio 1>" in prompt


def test_sequence_inherits_described_child_voice_metadata() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    previous = SimpleNamespace(
        voice_cast=cast,
        sample=SimpleNamespace(active_voice_ids=("girl",)),
    )
    active_cast, active_ids = _resolve_sequence_voice_cast(
        "她继续说：<d>[Chinese] 别怕。</d>",
        cast,
        previous,
    )
    _items, prompt = _apply_character_voice_cast(
        "她继续说：<d>[Chinese] 别怕。</d>",
        [],
        active_cast,
        forced_role_ids=active_ids,
    )
    assert "S1 = 女孩" in prompt
    assert "儿童/女性" in prompt
    assert "pitch 很高" in prompt
    assert "fixed timbre:" in prompt


def test_explicit_new_role_overrides_inherited_voice() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    previous = SimpleNamespace(
        voice_cast=cast,
        sample=SimpleNamespace(active_voice_ids=("girl",)),
    )
    _active_cast, active_ids = _resolve_sequence_voice_cast(
        "@男孩 回答：<d>[Chinese] 我在这里。</d>",
        cast,
        previous,
    )
    assert active_ids == ("boy",)


def test_template_speaker_label_activates_and_switches_voice() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    _items, prompt = _apply_character_voice_cast(
        "(S1) says: <d>[Chinese] 别怕。</d>",
        [],
        cast,
    )
    assert "S1 = 女孩" in prompt
    assert "S2 = 男孩" not in prompt
    first_cast, first_ids = _resolve_sequence_voice_cast(
        "(S1) says: <d>[Chinese] 别怕。</d>",
        cast,
        None,
    )
    assert first_cast is cast
    assert first_ids == ("girl",)
    previous = SimpleNamespace(
        voice_cast=cast,
        sample=SimpleNamespace(active_voice_ids=("girl",)),
    )
    _active_cast, active_ids = _resolve_sequence_voice_cast(
        "(S2) says: <d>[Chinese] 我在这里。</d>",
        cast,
        previous,
    )
    assert active_ids == ("boy",)


def test_missing_inherited_role_fails_instead_of_falling_back_to_adult_voice() -> None:
    girl = MiniMaxH3CharacterVoiceRole(
        role_id="girl", name="女孩", mode="described", description="童声",
        language="Chinese", age="child", gender="female", pitch="high", pace="natural",
    )
    boy = MiniMaxH3CharacterVoiceRole(
        role_id="boy", name="男孩", mode="described", description="童声",
        language="Chinese", age="child", gender="male", pitch="high", pace="natural",
    )
    previous = SimpleNamespace(
        voice_cast=MiniMaxH3CharacterVoiceCast((girl,)),
        sample=SimpleNamespace(active_voice_ids=("girl",)),
    )
    try:
        _resolve_sequence_voice_cast(
            "她继续说话。",
            MiniMaxH3CharacterVoiceCast((boy,)),
            previous,
        )
    except ValueError as exc:
        assert "girl" in str(exc)
    else:
        raise AssertionError("An incompatible cast must not silently drop the locked voice")


def main() -> None:
    tests = (
        test_default_cast_has_six_fixed_speakers,
        test_only_mentioned_roles_are_injected,
        test_disabled_library_skips_validation_and_returns_no_roles,
        test_reference_state_keeps_trim_duration,
        test_h3_audio_reference_budget_is_enforced,
        test_sequence_inherits_same_cloned_voice_without_repeating_at_role,
        test_sequence_inherits_described_child_voice_metadata,
        test_explicit_new_role_overrides_inherited_voice,
        test_template_speaker_label_activates_and_switches_voice,
        test_missing_inherited_role_fails_instead_of_falling_back_to_adult_voice,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} voice cast checks")


if __name__ == "__main__":
    main()
