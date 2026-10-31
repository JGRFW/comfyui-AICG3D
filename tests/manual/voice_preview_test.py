# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Offline checks for multi-voice preview generation and route wiring."""

from __future__ import annotations

import sys
import types
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def test_six_seats_use_distinct_chinese_voices() -> None:
    from aicg3d import routes

    voices = routes.VOICE_PREVIEW_VOICES["Chinese"]
    assert len(set(voices.values())) == 6
    assert voices["girl"] != voices["boy"]
    assert voices["heroine"] != voices["hero"]
    assert voices["old_woman"] != voices["old_man"]


def test_voice_selection_follows_gender_and_age() -> None:
    from aicg3d import routes

    assert routes._voice_preview_voice("Chinese", "girl", "male", "child") == "zh-CN-YunxiaNeural"
    assert routes._voice_preview_voice("Chinese", "boy", "female", "elder") == "zh-CN-XiaobeiNeural"
    assert routes._voice_preview_voice("Chinese", "hero", "male", "adult") == "zh-CN-YunxiNeural"


def test_spark_preview_settings_follow_voice_fields() -> None:
    from aicg3d import routes

    assert routes._spark_preview_gender("girl", "male") == "male"
    assert routes._spark_preview_gender("hero", "neutral") == "male"
    assert routes._spark_preview_pitch("high", "child", "稚嫩") == "very_high"
    assert routes._spark_preview_pitch("medium_low", "child", "3岁小女孩") == "very_high"
    assert routes._spark_preview_pitch("low", "elder", "低沉 沙哑") == "very_low"
    assert routes._spark_preview_speed("natural", "elder", "年长") == "low"
    assert routes._spark_preview_age("child", "3岁小女孩") == "Child"
    assert routes._spark_preview_age("adult", "三岁幼儿奶声") == "Child"
    assert routes._spark_preview_age("elder", "老年") == "Elderly"


def test_age_and_gender_keywords_cover_all_stages() -> None:
    from aicg3d import routes

    samples = {
        "5岁小女孩": "Child",
        "15岁少年": "Teenager",
        "25岁青年女性": "Youth-Adult",
        "45岁中年男人": "Middle-aged",
        "70岁老年女性": "Elderly",
    }
    for text, expected in samples.items():
        assert routes._spark_preview_age("auto", text) == expected, text
    assert routes._voice_gender_category("hero", "neutral", "四十岁妈妈") == "female"
    assert routes._voice_gender_category("heroine", "neutral", "七十岁爷爷") == "male"
    assert routes._voice_preview_voice("Chinese", "heroine", "female", "middle_age", "中年女性") == "zh-CN-XiaoniNeural"
    assert routes._voice_preview_voice("Chinese", "hero", "male", "elder", "老年男性") == "zh-CN-YunyangNeural"


def test_spark_age_token_is_injected_without_changing_default_behavior() -> None:
    import sys
    import types
    from aicg3d import routes

    module = types.ModuleType("fake_spark_tts_module")
    module.AGE_MAP = {"Child": 0, "Elderly": 4}
    module.GENDER_MAP = {"female": 0, "male": 1}
    module.LEVELS_MAP = {"very_low": 0, "low": 1, "moderate": 2, "high": 3, "very_high": 4}
    module.TASK_TOKEN_MAP = {"controllable_tts": "<tts>"}

    class FakeSparkTTS:
        def process_prompt_control(self, gender, pitch, speed, text):
            return "original"

    class FakeSparkRun:
        pass

    FakeSparkTTS.__module__ = module.__name__
    FakeSparkRun.__module__ = module.__name__
    module.SparkTTS = FakeSparkTTS
    sys.modules[module.__name__] = module
    try:
        routes._ensure_spark_age_support(FakeSparkRun)
        model = FakeSparkTTS()
        module._AICG3D_ACTIVE_AGE = "Child"
        prompt = model.process_prompt_control("female", "very_high", "low", "你好")
        assert "<|age_0|>" in prompt
        module._AICG3D_ACTIVE_AGE = None
        assert model.process_prompt_control("female", "high", "moderate", "你好") == "original"
    finally:
        sys.modules.pop(module.__name__, None)


def test_preview_reads_the_fixed_voice_description_verbatim() -> None:
    from aicg3d import routes

    description = "3岁女童初变声前童声，清脆柔和，保留孩童灵气。"
    assert routes._voice_preview_text("女孩", "Chinese", description) == description
    assert routes._voice_preview_text("女孩", "Chinese", "  第一行  第二行  ") == "第一行 第二行"
    assert "固定声音" in routes._voice_preview_text("女孩", "Chinese", "")


def test_description_keywords_change_prosody() -> None:
    from aicg3d import routes

    bright = routes._voice_preview_prosody("medium", "natural", "adult", "清亮 活泼 有精神")
    low = routes._voice_preview_prosody("medium", "natural", "adult", "低沉 沙哑 宽厚")
    assert bright != low


def test_voice_preview_route_is_registered() -> None:
    from aicg3d import routes

    paths: set[str] = set()

    class FakeRoutes:
        def get(self, path):
            def decorate(handler):
                paths.add(path)
                return handler
            return decorate

        def post(self, path):
            def decorate(handler):
                paths.add(path)
                return handler
            return decorate

    class FakePromptServer:
        instance = types.SimpleNamespace(routes=FakeRoutes())

    original_server = sys.modules.get("server")
    original_registered = routes._REGISTERED
    try:
        sys.modules["server"] = types.SimpleNamespace(PromptServer=FakePromptServer)
        routes._REGISTERED = False
        assert routes.register_routes() is True
        assert "/aicg3d/api/voice-preview" in paths
        assert "/aicg3d/api/voice-preview-spark" in paths
        assert "/aicg3d/api/voice-preview/delete" in paths
        assert "/aicg3d/api/sparktts/status" in paths
    finally:
        routes._REGISTERED = original_registered
        if original_server is None:
            sys.modules.pop("server", None)
        else:
            sys.modules["server"] = original_server


def test_frontend_uses_generated_reference_audio() -> None:
    preview = (PLUGIN_ROOT / "web" / "aicg3d_voice_preview.js").read_text(encoding="utf-8")
    voice_ui = (PLUGIN_ROOT / "web" / "aicg3d_voice_library.js").read_text(encoding="utf-8")
    assert "绑定画面参考" in voice_ui
    assert "@角色${role.seat} <Picture ${role.picture_index}>" in voice_ui
    assert "儿童女声（3～8岁）" in voice_ui
    assert "老年男声（60岁以上）" in voice_ui
    assert "h3-voice-keyword-tag" in voice_ui
    assert 'api.fetchApi("/aicg3d/api/voice-preview-spark"' in preview
    assert 'api.fetchApi("/aicg3d/api/sparktts/status")' in preview
    assert "h3-voice-spark-status" in preview
    assert 'role.reference_source = payload.source' in preview
    assert "function applyRoleToPrompt(" in preview
    assert "function clearGeneratedVoice(" in preview
    assert "清除生成音色" in preview
    assert "应用到提示词" in preview
    assert "function currentRoleState(" in preview
    assert "停止试听" in preview
    assert "activeStopTimer" in preview
    assert "role.mode = \"reference\"" in preview
    assert "试听文件就是 H3 参考" in preview
    assert "SpeechSynthesisUtterance" not in preview


def test_edge_tts_dependency_is_declared() -> None:
    requirements = (PLUGIN_ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (PLUGIN_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "edge-tts" in requirements
    assert "edge-tts" in pyproject
    for dependency in ("omegaconf", "soundfile", "soxr", "einx", "transformers"):
        assert dependency in requirements
        assert dependency in pyproject


def main() -> None:
    tests = (
        test_six_seats_use_distinct_chinese_voices,
        test_voice_selection_follows_gender_and_age,
        test_spark_preview_settings_follow_voice_fields,
        test_age_and_gender_keywords_cover_all_stages,
        test_spark_age_token_is_injected_without_changing_default_behavior,
        test_description_keywords_change_prosody,
        test_preview_reads_the_fixed_voice_description_verbatim,
        test_voice_preview_route_is_registered,
        test_frontend_uses_generated_reference_audio,
        test_edge_tts_dependency_is_declared,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} voice preview checks")


if __name__ == "__main__":
    main()
