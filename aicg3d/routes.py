# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""AICG3D 前端接口。

只提供展示层需要的数据（技能目录、LoRA 元信息、素材库），模型加载与执行
仍然完全由 ComfyUI 自己负责。所有路由都挂在 ``/aicg3d/api`` 下。
"""
from __future__ import annotations

import json
import os
import struct
from typing import Any

import folder_paths
from aiohttp import web

import aicg3d.prompt_guides as guide_lib
import aicg3d.skills as skill_lib
from aicg3d_sparktts.model_status import spark_model_status

VERSION = "1.1.23"
PROJECT_NAME = "短剧工作台"
PROJECT_DESCRIPTION = "无限时长视频的 MiniMax H3 ComfyUI 工作流与插件"
REPOSITORY_URL = "https://github.com/JGRFW/comfyui-AICG3D"
SEARCH_ALIASES = [
    "短剧工作台",
    "无限时长视频的 MiniMax H3 工作流",
    "ComfyUI MiniMax H3 无限长视频",
    "MiniMax H3 本地短剧工作流",
    "MiniMax H3 无限分段生视频",
]
MEDIA_KINDS = {
    "image": (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"),
    "video": (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".mpg", ".mpeg", ".wmv", ".flv"),
    "audio": (".mp3", ".wav", ".flac", ".ogg", ".oga", ".m4a", ".aac", ".opus", ".wma"),
}
_PREVIEW_SUFFIXES = (".preview.png", ".preview.jpeg", ".preview.jpg", ".preview.webp", ".png", ".jpeg", ".jpg", ".webp")
_LORA_CACHE: dict[str, Any] = {}
_REGISTERED = False


def _lora_metadata(path: str) -> dict[str, Any]:
    """从 safetensors 头部读取 LoRA 的基础信息，结果按文件指纹缓存。"""
    try:
        stat = os.stat(path)
        key = f"{path}|{stat.st_mtime_ns}|{stat.st_size}"
    except OSError:
        return {}
    cached = _LORA_CACHE.get(path)
    if cached and cached.get("key") == key:
        return cached["value"]

    info: dict[str, Any] = {"size": stat.st_size}
    if path.lower().endswith(".safetensors"):
        try:
            with open(path, "rb") as handle:
                header_size = struct.unpack("<Q", handle.read(8))[0]
                if 0 < header_size < 64 * 1024 * 1024:
                    header = json.loads(handle.read(header_size).decode("utf-8"))
            meta = header.get("__metadata__") or {}
            mapping = {
                "ss_base_model_version": "base_model",
                "ss_sd_model_name": "source_model",
                "ss_network_module": "network",
                "ss_network_dim": "rank",
                "ss_network_alpha": "alpha",
                "ss_output_name": "title",
                "modelspec.title": "title",
                "modelspec.description": "description",
            }
            for source, target in mapping.items():
                value = meta.get(source)
                if value not in (None, "", "None") and target not in info:
                    info[target] = str(value)[:300]
            tensors = [name for name in header if name != "__metadata__"]
            info["tensor_count"] = len(tensors)
        except (OSError, ValueError, struct.error):
            pass

    for suffix in (".civitai.info", ".json"):
        sidecar = path[: -len(".safetensors")] + suffix if path.lower().endswith(".safetensors") else path + suffix
        if not os.path.isfile(sidecar):
            continue
        try:
            with open(sidecar, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            info.setdefault("title", str(payload.get("model", {}).get("name") or "")[:200])
            words = payload.get("trainedWords") or payload.get("trained_words")
            if isinstance(words, list) and words:
                info["trigger"] = ", ".join(str(word) for word in words[:8])[:300]
            info["base_model"] = info.get("base_model") or str(payload.get("baseModel") or "")
        except (OSError, ValueError):
            pass
        break

    _LORA_CACHE[path] = {"key": key, "value": info}
    return info


def _lora_preview(path: str) -> str:
    stem = os.path.splitext(path)[0]
    for candidate in (path + suffix for suffix in _PREVIEW_SUFFIXES[:4]):
        if os.path.isfile(candidate):
            return candidate
    for candidate in (stem + suffix for suffix in _PREVIEW_SUFFIXES[4:]):
        if os.path.isfile(candidate):
            return candidate
    return ""


def _entry_url(filename: str, storage: str = "input", subfolder: str = "") -> str:
    params = [f"filename={web_quote(filename)}", f"type={storage}"]
    if subfolder:
        params.append(f"subfolder={web_quote(subfolder)}")
    return "/view?" + "&".join(params)


def web_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(str(value), safe="")


def list_loras() -> list[dict[str, Any]]:
    entries = []
    for name in folder_paths.get_filename_list("loras"):
        try:
            path = folder_paths.get_full_path("loras", name)
        except Exception:
            path = None
        if not path or not os.path.isfile(path):
            continue
        info = _lora_metadata(path)
        entries.append({
            "name": name,
            "label": os.path.splitext(os.path.basename(name))[0],
            "group": os.path.dirname(name).replace("\\", "/"),
            "size": info.get("size", 0),
            "title": info.get("title", ""),
            "base_model": info.get("base_model", ""),
            "rank": info.get("rank", ""),
            "trigger": info.get("trigger", ""),
            "description": info.get("description", ""),
            "preview": f"/aicg3d/api/lora/preview?name={web_quote(name)}" if _lora_preview(path) else "",
        })
    entries.sort(key=lambda item: (item["group"], item["label"].lower()))
    return entries


def lora_preview_path(name: str) -> str:
    path = folder_paths.get_full_path("loras", name)
    if not path:
        return ""
    preview = _lora_preview(path)
    return preview if preview and os.path.isfile(preview) else ""


def list_media(kind: str = "", limit: int = 400) -> list[dict[str, Any]]:
    root = folder_paths.get_input_directory()
    wanted = MEDIA_KINDS.get(kind.lower())
    entries: list[dict[str, Any]] = []
    max_entries = max(1, min(4000, int(limit)))
    for current, _dirs, names in os.walk(root):
        if len(entries) >= max_entries:
            break
        for name in names:
            extension = os.path.splitext(name)[1].lower()
            if wanted:
                media_kind = kind.lower() if extension in wanted else ""
            else:
                media_kind = next(
                    (key for key, suffixes in MEDIA_KINDS.items() if extension in suffixes), ""
                )
            if not media_kind:
                continue
            absolute = os.path.join(current, name)
            subfolder = os.path.relpath(current, root).replace("\\", "/")
            subfolder = "" if subfolder == "." else subfolder
            try:
                stat = os.stat(absolute)
            except OSError:
                continue
            entries.append({
                "filename": name,
                "subfolder": subfolder,
                "kind": media_kind,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "path": f"{subfolder}/{name}" if subfolder else name,
                "url": _entry_url(name, "input", subfolder),
            })
            if len(entries) >= max_entries:
                break
    entries.sort(key=lambda item: item["mtime"], reverse=True)
    return entries


def _normalized_media_reference(value: Any) -> str:
    filename = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not filename or "\x00" in filename:
        return ""
    parts = [part for part in filename.split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def media_reference_exists(filename: str) -> bool:
    normalized = _normalized_media_reference(filename)
    if not normalized:
        return False
    try:
        input_root = os.path.realpath(folder_paths.get_input_directory())
        path = os.path.realpath(
            folder_paths.get_annotated_filepath(normalized, input_root)
        )
        if os.path.commonpath((input_root, path)) != input_root:
            return False
        return os.path.isfile(path)
    except (OSError, ValueError):
        return False

def _skill_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "name_en": item.get("name_en", ""),
        "summary": item.get("summary", ""),
        "tag": item.get("tag", ""),
        "kind": item.get("kind", "skill"),
        "skill_id": item.get("skill_id", ""),
        "guide_id": item.get("guide_id", ""),
        "references": item.get("references", []),
        "label": item.get("label", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "category_name": item.get("category_name", ""),
        "chars": item.get("chars", 0),
    }


VOICE_PREVIEW_SUBFOLDER = "aicg3d_voice_previews"
VOICE_PREVIEW_VOICES = {
    "Chinese": {
        "girl": "zh-CN-XiaoyiNeural",
        "boy": "zh-CN-YunxiaNeural",
        "heroine": "zh-CN-XiaoxiaoNeural",
        "hero": "zh-CN-YunxiNeural",
        "old_woman": "zh-CN-XiaobeiNeural",
        "old_man": "zh-CN-YunyangNeural",
    },
    "English": {
        "girl": "en-US-AnaNeural",
        "boy": "en-US-GuyNeural",
        "heroine": "en-US-JennyNeural",
        "hero": "en-US-ChristopherNeural",
        "old_woman": "en-US-AriaNeural",
        "old_man": "en-US-DavisNeural",
    },
    "Japanese": {
        "girl": "ja-JP-NanamiNeural",
        "boy": "ja-JP-KeitaNeural",
        "heroine": "ja-JP-NanamiNeural",
        "hero": "ja-JP-KeitaNeural",
        "old_woman": "ja-JP-NanamiNeural",
        "old_man": "ja-JP-KeitaNeural",
    },
    "Korean": {
        "girl": "ko-KR-SunHiNeural",
        "boy": "ko-KR-InJoonNeural",
        "heroine": "ko-KR-SunHiNeural",
        "hero": "ko-KR-InJoonNeural",
        "old_woman": "ko-KR-SunHiNeural",
        "old_man": "ko-KR-InJoonNeural",
    },
}


def _voice_preview_name(value: Any, fallback: str) -> str:
    import re

    name = re.sub(r"[\r\n\t<>]", " ", str(value or "")).strip()
    return name[:40] or fallback


def _voice_age_category(age: str, description: str = "") -> str:
    import re

    text = str(description or "")
    value = str(age or "auto").strip().lower()
    numeric = re.search(r"(?<!\d)(\d{1,3})\s*岁", text)
    if numeric:
        years = int(numeric.group(1))
        if years <= 12:
            return "child"
        if years <= 19:
            return "teenager"
        if years <= 35:
            return "young_adult"
        if years <= 59:
            return "middle_age"
        return "elder"
    chinese_years = {
        "三岁": 3, "四岁": 4, "五岁": 5, "六岁": 6, "七岁": 7, "八岁": 8,
        "九岁": 9, "十岁": 10, "十一岁": 11, "十二岁": 12, "十三岁": 13,
        "十五岁": 15, "十六岁": 16, "十八岁": 18, "二十岁": 20, "三十岁": 30,
        "四十岁": 40, "五十岁": 50, "六十岁": 60, "七十岁": 70, "八十岁": 80,
    }
    for token, years in chinese_years.items():
        if token in text:
            return _voice_age_category(str(years), f"{years}岁")
    keyword_groups = (
        ("child", ("幼童", "幼儿", "孩童", "小孩", "宝宝", "童声", "童音", "奶声", "奶音", "稚嫩")),
        ("teenager", ("青少年", "青春期", "少年", "少女", "十几岁", "中学生")),
        ("middle_age", ("中年", "四十多", "五十多", "40多", "50多", "成熟稳重", "沧桑")),
        ("elder", ("老年", "老人", "年长", "苍老", "花甲", "古稀", "老太太", "老爷子", "奶奶", "爷爷")),
        ("young_adult", ("青年", "年轻人", "大学", "二十多", "30岁", "三十多")),
    )
    for category, tokens in keyword_groups:
        if any(token in text for token in tokens):
            return category
    aliases = {
        "child": "child",
        "teenager": "teenager",
        "teen": "teenager",
        "young_adult": "young_adult",
        "youth": "young_adult",
        "adult": "adult",
        "middle_age": "middle_age",
        "middle-aged": "middle_age",
        "elder": "elder",
        "elderly": "elder",
    }
    return aliases.get(value, "adult")


def _voice_gender_category(role_id: str, gender: str, description: str = "") -> str:
    text = str(description or "")
    female_tokens = ("女性", "女孩", "女人", "女主", "妈妈", "母亲", "姐姐", "妹妹", "阿姨", "奶奶", "外婆", "少女", "女士")
    male_tokens = ("男性", "男孩", "男人", "男主", "爸爸", "父亲", "哥哥", "弟弟", "叔叔", "爷爷", "外公", "少年", "男士")
    if any(token in text for token in female_tokens):
        return "female"
    if any(token in text for token in male_tokens):
        return "male"
    value = str(gender or "neutral").strip().lower()
    if value in {"female", "male"}:
        return value
    return "female" if role_id in {"girl", "heroine", "old_woman"} else "male"

def _voice_preview_voice(
    language: str, role_id: str, gender: str, age: str, description: str = "",
) -> str:
    voices = VOICE_PREVIEW_VOICES[language]
    category = _voice_gender_category(role_id, gender, description)
    age_category = _voice_age_category(age, description)
    if language == "Chinese":
        if category == "female":
            return {
                "child": "zh-CN-XiaoyiNeural",
                "teenager": "zh-CN-XiaoyiNeural",
                "young_adult": "zh-CN-XiaoxiaoNeural",
                "adult": "zh-CN-XiaoxiaoNeural",
                "middle_age": "zh-CN-XiaoniNeural",
                "elder": "zh-CN-XiaobeiNeural",
            }.get(age_category, voices["heroine"])
        return {
            "child": "zh-CN-YunxiaNeural",
            "teenager": "zh-CN-YunxiNeural",
            "young_adult": "zh-CN-YunxiNeural",
            "adult": "zh-CN-YunxiNeural",
            "middle_age": "zh-CN-YunjianNeural",
            "elder": "zh-CN-YunyangNeural",
        }.get(age_category, voices["hero"])
    if language in {"Japanese", "Korean"}:
        return voices["heroine"] if category == "female" else voices["hero"]
    if category == "female":
        return voices["girl"] if age_category == "child" else voices["old_woman"] if age_category == "elder" else voices["heroine"]
    return voices["boy"] if age_category == "child" else voices["old_man"] if age_category == "elder" else voices["hero"]

def _voice_preview_prosody(pitch: str, pace: str, age: str, description: str = "") -> tuple[str, str]:
    pitch_hz = {
        "very_low": -24,
        "low": -16,
        "medium_low": -8,
        "medium": 0,
        "medium_high": 8,
        "high": 16,
        "very_high": 24,
    }.get(str(pitch or "medium"), 0)
    rate_percent = {
        "very_slow": -30,
        "slow": -18,
        "natural": 0,
        "fast": 15,
        "very_fast": 28,
    }.get(str(pace or "natural"), 0)
    age_category = _voice_age_category(age, description)
    if age_category == "child":
        pitch_hz = max(24, pitch_hz + 5)
        rate_percent += 3
    elif age_category == "teenager":
        pitch_hz = max(10, pitch_hz + 3)
        rate_percent += 2
    elif age_category == "middle_age":
        pitch_hz = min(-4, pitch_hz - 4)
        rate_percent -= 2
    elif age_category == "elder":
        pitch_hz = min(-16, pitch_hz - 6)
        rate_percent -= 8
    text = str(description or "").lower()
    if any(token in text for token in ("低沉", "宽厚", "沙哑", "浑厚", "very low")):
        pitch_hz -= 4
    if any(token in text for token in ("清亮", "明亮", "活泼", "有精神", "bright")):
        pitch_hz += 3
    if any(token in text for token in ("温柔", "柔和", "轻柔", "克制", "soft")):
        rate_percent -= 2
    pitch_hz = max(-35, min(35, pitch_hz))
    rate_percent = max(-45, min(45, rate_percent))
    return f"{rate_percent:+d}%", f"{pitch_hz:+d}Hz"

def _voice_preview_text(name: str, language: str, description: str = "") -> str:
    import re

    spoken = re.sub(r"\s+", " ", str(description or "")).strip()
    if spoken:
        return spoken[:500]
    if language == "English":
        return f"Hello, I am {name}. This is the fixed voice I will use in the scene."
    if language == "Japanese":
        return f"こんにちは、{name}です。これはシーンで使う固定の声です。"
    if language == "Korean":
        return f"안녕하세요, {name}입니다. 장면에서 사용할 고정 목소리입니다."
    return f"你好，我是{name}。这是我在短剧中使用的固定声音。"

def _spark_preview_pitch(value: str, age: str, description: str = "") -> str:
    levels = ["very_low", "low", "moderate", "high", "very_high"]
    normalized = {
        "very_low": 0,
        "low": 1,
        "medium_low": 1,
        "medium": 2,
        "medium_high": 3,
        "high": 3,
        "very_high": 4,
    }.get(str(value or "medium"), 2)
    age_category = _voice_age_category(age, description)
    if age_category == "child":
        return "very_high"
    if age_category == "teenager":
        return "high" if normalized < 3 else levels[normalized]
    if age_category == "middle_age":
        return "low" if normalized > 1 else levels[normalized]
    if age_category == "elder":
        return "very_low"
    text = str(description or "")
    if any(token in text for token in ("低沉", "宽厚", "沙哑", "浑厚")):
        normalized -= 1
    if any(token in text for token in ("清亮", "明亮", "活泼", "有精神")):
        normalized += 1
    return levels[max(0, min(4, normalized))]

def _spark_preview_speed(value: str, age: str, description: str = "") -> str:
    levels = ["very_low", "low", "moderate", "high", "very_high"]
    normalized = {
        "very_slow": 0,
        "slow": 1,
        "natural": 2,
        "fast": 3,
        "very_fast": 4,
    }.get(str(value or "natural"), 2)
    text = str(description or "")
    if age == "elder" or any(token in text for token in ("年长", "岁月", "苍老", "缓慢")):
        normalized -= 1
    if any(token in text for token in ("活泼", "有精神", "快速", "急促")):
        normalized += 1
    return levels[max(0, min(len(levels) - 1, normalized))]


def _spark_preview_gender(role_id: str, gender: str, description: str = "") -> str:
    return _voice_gender_category(role_id, gender, description)


def _spark_preview_age(age: str, description: str = "") -> str:
    category = _voice_age_category(age, description)
    return {
        "child": "Child",
        "teenager": "Teenager",
        "young_adult": "Youth-Adult",
        "adult": "Youth-Adult",
        "middle_age": "Middle-aged",
        "elder": "Elderly",
    }.get(category, "Youth-Adult")

def _ensure_spark_age_support(spark_class) -> Any:
    import sys
    import threading

    module = sys.modules.get(spark_class.__module__)
    tts_class = getattr(module, "SparkTTS", None)
    if not hasattr(module, "AGE_MAP") or tts_class is None:
        return module
    if getattr(tts_class, "_aicg3d_supports_age", False):
        if not hasattr(module, "_AICG3D_PREVIEW_LOCK"):
            module._AICG3D_PREVIEW_LOCK = threading.Lock()
        return module
    if not getattr(tts_class, "_aicg3d_age_patch", False):
        original = tts_class.process_prompt_control

        def process_prompt_control_with_age(self, gender, pitch, speed, text):
            active_age = getattr(module, "_AICG3D_ACTIVE_AGE", None)
            if active_age not in module.AGE_MAP:
                return original(self, gender, pitch, speed, text)
            gender_id = module.GENDER_MAP[gender]
            pitch_id = module.LEVELS_MAP[pitch]
            speed_id = module.LEVELS_MAP[speed]
            age_id = module.AGE_MAP[active_age]
            tokens = "".join((
                f"<|gender_{gender_id}|>",
                f"<|pitch_label_{pitch_id}|>",
                f"<|speed_label_{speed_id}|>",
                f"<|age_{age_id}|>",
            ))
            return "".join((
                module.TASK_TOKEN_MAP["controllable_tts"],
                "<|start_content|>", text, "<|end_content|>",
                "<|start_style_label|>", tokens, "<|end_style_label|>",
            ))

        tts_class.process_prompt_control = process_prompt_control_with_age
        tts_class._aicg3d_age_patch = True
    if not hasattr(module, "_AICG3D_PREVIEW_LOCK"):
        module._AICG3D_PREVIEW_LOCK = threading.Lock()
    return module

def _run_spark_voice_preview(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    import nodes as comfy_nodes

    status = spark_model_status()
    if not status["installed"]:
        raise LookupError(status["message"])
    mappings = getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {})
    spark_class = mappings.get("AICG3D_SparkTTSRun") or mappings.get("SparkTTSRun")
    if spark_class is None:
        raise LookupError("内置 Spark-TTS 节点未成功注册，请重启 ComfyUI 并检查启动日志。")
    spark_module = _ensure_spark_age_support(spark_class)

    role_id = str(payload.get("id") or "girl")
    language = str(payload.get("language") or "Chinese")
    if language != "Chinese":
        raise LookupError("Spark-TTS 试听当前使用中文固定声线")
    name = _voice_preview_name(payload.get("name"), role_id)
    description = str(payload.get("description") or "")[:500]
    age = str(payload.get("age") or "adult")
    gender = _spark_preview_gender(role_id, str(payload.get("gender") or "neutral"), description)
    pitch = _spark_preview_pitch(str(payload.get("pitch") or "medium"), age, description)
    speed = _spark_preview_speed(str(payload.get("pace") or "natural"), age, description)
    text = _voice_preview_text(name, "Chinese", description)
    seed_text = "|".join((role_id, name, gender, pitch, speed, description))
    import hashlib

    age_label = _spark_preview_age(age, description)
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:15], 16)
    lock = getattr(spark_module, "_AICG3D_PREVIEW_LOCK", None)
    if lock is None:
        import threading
        lock = threading.Lock()
        spark_module._AICG3D_PREVIEW_LOCK = lock
    with lock:
        spark_module._AICG3D_ACTIVE_AGE = age_label
        try:
            result = spark_class().speak(
                text=text,
                gender=gender,
                pitch=pitch,
                speed=speed,
                unload_model=True,
                temperature=0.8,
                top_k=50,
                top_p=0.95,
                max_new_tokens=1200,
                do_sample=True,
                seed=seed,
            )
        finally:
            spark_module._AICG3D_ACTIVE_AGE = None
    audio = result[0] if isinstance(result, tuple) and result else result
    if not isinstance(audio, dict) or "waveform" not in audio or "sample_rate" not in audio:
        raise RuntimeError("Spark-TTS 没有返回可用音频")
    settings = {
        "engine": "spark-tts",
        "voice": f"Spark-TTS {gender}/{age_label}/{pitch}/{speed}",
        "gender": gender,
        "age": age_label,
        "pitch": pitch,
        "speed": speed,
        "seed": seed,
        "text": text,
    }
    return audio, settings

def register_routes() -> bool:
    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        from server import PromptServer

        routes = PromptServer.instance.routes
    except Exception:
        return False

    @routes.get("/aicg3d/api/meta")
    async def aicg3d_meta(_request):
        return web.json_response({
            "name": PROJECT_NAME,
            "description": PROJECT_DESCRIPTION,
            "repository": REPOSITORY_URL,
            "search_aliases": SEARCH_ALIASES,
            "version": VERSION,
            "skills": len(skill_lib.discover()),
            "presets": len(skill_lib.discover_presets()),
            "prompt_guides": len(guide_lib.items()),
            "loras": len(folder_paths.get_filename_list("loras")),
            "sparktts": spark_model_status(),
        })

    @routes.get("/aicg3d/api/prompt-guides")
    async def aicg3d_prompt_guides(_request):
        """提示词方案列表：直接来自 prompt_guides/ 目录扫描，增删文件夹即时生效。"""
        return web.json_response({"guides": guide_lib.payload()})

    @routes.get("/aicg3d/api/skills")
    async def aicg3d_skills(_request):
        return web.json_response({"skills": [_skill_payload(item) for item in skill_lib.discover()]})

    @routes.get("/aicg3d/api/skills/{skill_id}")
    async def aicg3d_skill_detail(request):
        item = skill_lib.get(request.match_info.get("skill_id", ""))
        if item is None:
            return web.json_response({"error": "找不到该 Skill"}, status=404)
        payload = _skill_payload(item)
        payload["body"] = skill_lib.read_body(item)
        return web.json_response(payload)

    @routes.get("/aicg3d/api/presets")
    async def aicg3d_presets(_request):
        return web.json_response({
            "categories": skill_lib.preset_categories(),
            "presets": [_skill_payload(item) for item in skill_lib.discover_presets()],
        })

    @routes.get("/aicg3d/api/presets/{preset_id}")
    async def aicg3d_preset_detail(request):
        item = skill_lib.get(request.match_info.get("preset_id", ""))
        if item is None or item.get("kind") != "preset":
            return web.json_response({"error": "找不到该提示词模板"}, status=404)
        payload = _skill_payload(item)
        payload["body"] = skill_lib.read_body(item)
        return web.json_response(payload)

    @routes.get("/aicg3d/api/loras")
    async def aicg3d_loras(_request):
        return web.json_response({"loras": list_loras()})

    @routes.get("/aicg3d/api/lora/preview")
    async def aicg3d_lora_preview(request):
        path = lora_preview_path(request.query.get("name", ""))
        if not path:
            return web.Response(status=404)
        return web.FileResponse(path)

    @routes.get("/aicg3d/api/media")
    async def aicg3d_media(request):
        try:
            limit = int(request.query.get("limit", 400))
        except ValueError:
            limit = 400
        return web.json_response({
            "files": list_media(request.query.get("kind", ""), limit),
        })

    @routes.post("/aicg3d/api/media/validate")
    async def aicg3d_media_validate(request):
        try:
            payload = await request.json()
        except (TypeError, ValueError):
            return web.json_response({"error": "请求内容不是有效 JSON"}, status=400)
        raw_files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(raw_files, list):
            return web.json_response({"error": "files 必须是数组"}, status=400)

        checked = []
        missing = []
        seen = set()
        for item in raw_files[:1000]:
            if not isinstance(item, dict):
                continue
            filename = _normalized_media_reference(item.get("filename"))
            if not filename:
                continue
            owner_id = str(item.get("owner_id") or "")
            kind = str(item.get("kind") or "")
            key = (owner_id, kind, filename)
            if key in seen:
                continue
            seen.add(key)
            exists = media_reference_exists(filename)
            entry = {
                "owner_id": owner_id,
                "kind": kind,
                "filename": filename,
                "exists": exists,
            }
            checked.append(entry)
            if not exists:
                missing.append(entry)
        return web.json_response({
            "checked": len(checked),
            "missing": missing,
        })

    @routes.get("/aicg3d/api/sparktts/status")
    async def aicg3d_sparktts_status(_request):
        return web.json_response(spark_model_status())

    @routes.post("/aicg3d/api/voice-preview")
    async def aicg3d_voice_preview(request):
        try:
            payload = await request.json()
        except (TypeError, ValueError):
            return web.json_response({"error": "请求内容不是有效 JSON"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "音色参数必须是对象"}, status=400)

        role_id = str(payload.get("id") or "").strip().lower()
        if role_id not in {"girl", "boy", "heroine", "hero", "old_woman", "old_man"}:
            return web.json_response({"error": "未知角色座位"}, status=400)
        language = str(payload.get("language") or "Chinese").strip()
        if language not in VOICE_PREVIEW_VOICES:
            language = "Chinese"
        name = _voice_preview_name(payload.get("name"), role_id)
        age = str(payload.get("age") or "adult")
        gender = _voice_gender_category(role_id, str(payload.get("gender") or "neutral"), str(payload.get("description") or ""))
        pitch = str(payload.get("pitch") or "medium")
        pace = str(payload.get("pace") or "natural")
        description = str(payload.get("description") or "")[:500]
        voice = _voice_preview_voice(language, role_id, gender, age, description)
        rate, pitch_text = _voice_preview_prosody(pitch, pace, age, description)
        sample_text = _voice_preview_text(name, language, description)

        try:
            import hashlib
            import edge_tts
        except ImportError:
            return web.json_response(
                {"error": "缺少 edge-tts。请重启 ComfyUI 自动安装依赖，或执行：python -m pip install edge-tts"},
                status=503,
            )

        signature = "|".join((role_id, language, name, age, gender, pitch, pace, description, voice, rate, pitch_text))
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:20]
        filename = f"{role_id}-{digest}.mp3"
        input_root = os.path.realpath(folder_paths.get_input_directory())
        preview_dir = os.path.realpath(os.path.join(input_root, VOICE_PREVIEW_SUBFOLDER))
        if not preview_dir.startswith(input_root + os.sep):
            return web.json_response({"error": "试听目录不安全"}, status=500)
        os.makedirs(preview_dir, exist_ok=True)
        output_path = os.path.realpath(os.path.join(preview_dir, filename))
        if not output_path.startswith(preview_dir + os.sep):
            return web.json_response({"error": "试听文件路径不安全"}, status=500)

        if not os.path.isfile(output_path) or os.path.getsize(output_path) < 256:
            try:
                communicate = edge_tts.Communicate(
                    sample_text,
                    voice,
                    rate=rate,
                    pitch=pitch_text,
                    receive_timeout=20,
                )
                await communicate.save(output_path)
            except Exception as exc:
                try:
                    if os.path.isfile(output_path):
                        os.remove(output_path)
                except OSError:
                    pass
                return web.json_response({"error": f"试听音色生成失败：{exc}"}, status=502)

        reference = f"{VOICE_PREVIEW_SUBFOLDER}/{filename}"
        return web.json_response({
            "ok": True,
            "role_id": role_id,
            "voice": voice,
            "rate": rate,
            "pitch": pitch_text,
            "text": sample_text,
            "filename": filename,
            "subfolder": VOICE_PREVIEW_SUBFOLDER,
            "reference": reference,
            "url": _entry_url(filename, subfolder=VOICE_PREVIEW_SUBFOLDER),
            "source": "edge-tts",
        })
    @routes.post("/aicg3d/api/voice-preview-spark")
    async def aicg3d_voice_preview_spark(request):
        try:
            payload = await request.json()
        except (TypeError, ValueError):
            return web.json_response({"error": "请求内容不是有效 JSON"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "音色参数必须是对象"}, status=400)
        role_id = str(payload.get("id") or "").strip().lower()
        if role_id not in {"girl", "boy", "heroine", "hero", "old_woman", "old_man"}:
            return web.json_response({"error": "未知角色座位"}, status=400)

        import asyncio

        try:
            audio, settings = await asyncio.to_thread(_run_spark_voice_preview, payload)
        except LookupError as exc:
            return web.json_response({"error": str(exc)}, status=503)
        except Exception as exc:
            return web.json_response({"error": f"Spark-TTS 试听生成失败：{exc}"}, status=500)

        try:
            import hashlib
            import numpy as np
            import soundfile as sf
        except ImportError as exc:
            return web.json_response({"error": f"缺少试听音频保存依赖：{exc}"}, status=503)

        signature = "|".join(str(settings.get(key, "")) for key in ("voice", "seed", "text"))
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:20]
        filename = f"{role_id}-spark-{digest}.wav"
        input_root = os.path.realpath(folder_paths.get_input_directory())
        preview_dir = os.path.realpath(os.path.join(input_root, VOICE_PREVIEW_SUBFOLDER))
        if not preview_dir.startswith(input_root + os.sep):
            return web.json_response({"error": "试听目录不安全"}, status=500)
        os.makedirs(preview_dir, exist_ok=True)
        output_path = os.path.realpath(os.path.join(preview_dir, filename))
        if not output_path.startswith(preview_dir + os.sep):
            return web.json_response({"error": "试听文件路径不安全"}, status=500)

        try:
            waveform = audio["waveform"]
            if hasattr(waveform, "detach"):
                waveform = waveform.detach().cpu().float()
            values = waveform.numpy() if hasattr(waveform, "numpy") else np.asarray(waveform)
            values = np.squeeze(values)
            if values.ndim == 0:
                raise ValueError("empty waveform")
            if values.ndim == 1:
                values = values[:, None]
            elif values.ndim == 2 and values.shape[0] <= 8 and values.shape[1] > values.shape[0]:
                values = values.T
            sf.write(output_path, np.ascontiguousarray(values), int(audio["sample_rate"]), subtype="PCM_16")
        except Exception as exc:
            return web.json_response({"error": f"Spark-TTS 试听音频保存失败：{exc}"}, status=500)

        reference = f"{VOICE_PREVIEW_SUBFOLDER}/{filename}"
        return web.json_response({
            "ok": True,
            "role_id": role_id,
            "voice": settings["voice"],
            "rate": settings.get("speed", ""),
            "pitch": settings.get("pitch", ""),
            "text": settings["text"],
            "filename": filename,
            "subfolder": VOICE_PREVIEW_SUBFOLDER,
            "reference": reference,
            "url": _entry_url(filename, subfolder=VOICE_PREVIEW_SUBFOLDER),
            "source": "spark-tts",
        })
    @routes.post("/aicg3d/api/voice-preview/delete")
    async def aicg3d_voice_preview_delete(request):
        try:
            payload = await request.json()
        except (TypeError, ValueError):
            return web.json_response({"error": "请求内容不是有效 JSON"}, status=400)
        reference = _normalized_media_reference(payload.get("reference") if isinstance(payload, dict) else "")
        prefix = VOICE_PREVIEW_SUBFOLDER + "/"
        if not reference.startswith(prefix):
            return web.json_response({"error": "只能删除角色音色库生成的试听文件"}, status=400)
        input_root = os.path.realpath(folder_paths.get_input_directory())
        path = os.path.realpath(os.path.join(input_root, *reference.split("/")))
        preview_root = os.path.realpath(os.path.join(input_root, VOICE_PREVIEW_SUBFOLDER))
        if not path.startswith(preview_root + os.sep):
            return web.json_response({"error": "试听文件路径不安全"}, status=400)
        removed = False
        if os.path.isfile(path):
            os.remove(path)
            removed = True
        return web.json_response({"ok": True, "removed": removed, "reference": reference})
    _REGISTERED = True
    return True


