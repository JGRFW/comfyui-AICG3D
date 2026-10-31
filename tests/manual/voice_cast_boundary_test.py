# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression checks for voice mention boundaries and reference safety."""

from __future__ import annotations

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
    bind_reference_media,
)


def test_role_mentions_require_token_boundaries() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    _items, prompt = _apply_character_voice_cast(
        "@女孩子 出镜，@女孩2 不出镜，@girl-extra 也不出镜。",
        [],
        cast,
    )
    assert "S1 = 女孩" not in prompt
    assert "@女孩子" in prompt
    assert "@女孩2" in prompt
    assert "@girl-extra" in prompt


def test_reference_voice_requires_visual_reference() -> None:
    cast = MiniMaxH3CharacterVoiceCast((
        MiniMaxH3CharacterVoiceRole(
            role_id="girl",
            name="女孩",
            mode="reference",
            description="test",
            language="Chinese",
            age="child",
            gender="female",
            pitch="high",
            pace="natural",
            reference_filename="voice/girl.wav",
            reference_item=_MediaInput(0, "audio", {}),
            rights_confirmed=True,
        ),
    ))
    try:
        _apply_character_voice_cast("@女孩 开口说话", [], cast)
    except ValueError as exc:
        assert "至少需要 1 个画面参考" in str(exc)
    else:
        raise AssertionError("A cloned voice without a visual reference should fail clearly")


def test_fixed_seat_tokens_map_to_custom_names() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    _items, prompt = _apply_character_voice_cast("@角色1 对 @角色3 说话。", [], cast)
    assert "S1 = 女孩" in prompt
    assert "S3 = 女主角" in prompt
    assert "@角色1" not in prompt
    assert "S1（女孩）" in prompt
    assert "S3（女主角）" in prompt


def test_picture_binding_keeps_voice_with_the_right_visual_subject() -> None:
    cast, _report = MiniMaxH3EasyCharacterVoiceLibrary().load("")
    cast = MiniMaxH3CharacterVoiceCast(tuple(
        MiniMaxH3CharacterVoiceRole(
            role_id=role.role_id,
            name=role.name,
            mode=role.mode,
            description=role.description,
            language=role.language,
            age=role.age,
            gender=role.gender,
            pitch=role.pitch,
            pace=role.pace,
            picture_index=index,
        )
        for index, role in enumerate(cast.roles, start=1)
    ))
    items, prompt = _apply_character_voice_cast(
        "@角色1 在 <Picture 1> 说话，@角色2 在 <Picture 2> 回答。",
        [_MediaInput(0, "image", object()), _MediaInput(1, "image", object())],
        cast,
    )
    assert "visual binding: <Picture 1> is the visible character whose only voice is S1" in prompt
    assert "visual binding: <Picture 2> is the visible character whose only voice is S2" in prompt
    assert len(items) == 2


def test_picture_binding_stays_aligned_after_media_filtering() -> None:
    role = MiniMaxH3CharacterVoiceRole(
        role_id="boy", name="男孩", mode="described", description="test",
        language="Chinese", age="child", gender="male", pitch="high", pace="natural",
        picture_index=2,
    )
    cast = MiniMaxH3CharacterVoiceCast((role,))
    items, prompt = _apply_character_voice_cast(
        "@角色1 看向 <Picture 2>。",
        [_MediaInput(0, "image", object()), _MediaInput(1, "image", object()), _MediaInput(2, "image", object())],
        cast,
    )
    _items, prompt = bind_reference_media(prompt, items)
    assert "visual binding: <Picture 1> is the visible character whose only voice is S1" in prompt
    assert "<Picture 2>" not in prompt


def test_duplicate_picture_binding_is_rejected() -> None:
    cast = MiniMaxH3CharacterVoiceCast((
        MiniMaxH3CharacterVoiceRole("girl", "女孩", "described", "a", "Chinese", "child", "female", "high", "natural", 1),
        MiniMaxH3CharacterVoiceRole("boy", "男孩", "described", "b", "Chinese", "child", "male", "high", "natural", 1),
    ))
    try:
        _apply_character_voice_cast(
            "@角色1 和 @角色2",
            [_MediaInput(0, "image", object())],
            cast,
        )
    except ValueError as exc:
        assert "同一张人物参考图只能绑定一个角色声线" in str(exc)
    else:
        raise AssertionError("duplicate picture binding should fail")


def test_child_age_forces_childlike_pitch_in_h3_prompt() -> None:
    role = MiniMaxH3CharacterVoiceRole(
        role_id="heroine", name="女主角", mode="described", description="3岁小女孩声音",
        language="Chinese", age="child", gender="female", pitch="medium_low", pace="slow",
    )
    cast = MiniMaxH3CharacterVoiceCast((role,))
    _items, prompt = _apply_character_voice_cast("@角色1 开口说话", [], cast)
    assert "pitch 很高" in prompt
    assert "pitch 中低" not in prompt


def test_description_age_and_gender_override_conflicting_fields() -> None:
    role = MiniMaxH3CharacterVoiceRole(
        role_id="heroine", name="角色", mode="described", description="45岁中年男人，声音低沉稳重",
        language="Chinese", age="adult", gender="female", pitch="medium", pace="natural",
    )
    cast = MiniMaxH3CharacterVoiceCast((role,))
    _items, prompt = _apply_character_voice_cast("@角色1 开口说话", [], cast)
    assert "中年/男性" in prompt
    assert "pitch 偏低" in prompt


def test_reference_mode_hides_described_voice_metadata() -> None:
    image = _MediaInput(0, "image", object())
    reference = _MediaInput(1, "audio", {})
    role = MiniMaxH3CharacterVoiceRole(
        role_id="hero",
        name="男主角",
        mode="reference",
        description="这段描述只属于描述音色，不应进入克隆模式",
        language="Chinese",
        age="young_adult",
        gender="male",
        pitch="low",
        pace="natural",
        reference_filename="role.wav",
        reference_item=reference,
        rights_confirmed=True,
    )
    _items, prompt = _apply_character_voice_cast(
        "@角色1 开口说", [image], MiniMaxH3CharacterVoiceCast((role,))
    )
    assert "timbre is defined only by the attached reference audio" in prompt
    assert "这段描述只属于描述音色" not in prompt
    assert "fixed timbre:" not in prompt


def main() -> None:
    tests = (
        test_role_mentions_require_token_boundaries,
        test_fixed_seat_tokens_map_to_custom_names,
        test_picture_binding_keeps_voice_with_the_right_visual_subject,
        test_child_age_forces_childlike_pitch_in_h3_prompt,
        test_description_age_and_gender_override_conflicting_fields,
        test_picture_binding_stays_aligned_after_media_filtering,
        test_duplicate_picture_binding_is_rejected,
        test_reference_mode_hides_described_voice_metadata,
        test_reference_voice_requires_visual_reference,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} voice boundary checks")


if __name__ == "__main__":
    main()
