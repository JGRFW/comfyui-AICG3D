# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# -*- coding: utf-8 -*-
"""Spark-TTS model discovery and user-facing installation diagnostics."""
from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
from typing import Any

MODEL_FOLDER_NAME = "Spark-TTS-0.5B"
SPEAKER_FOLDER_NAME = "Step-Audio-speakers"
MODEL_DOWNLOAD_URL = "https://huggingface.co/SparkAudio/Spark-TTS-0.5B"
SPEAKER_DOWNLOAD_URL = "https://github.com/billwuhao/ComfyUI_SparkTTS"
PACKAGE_ROOT = Path(__file__).resolve().parent
BUNDLED_SPEAKER_DIR = PACKAGE_ROOT / "assets" / SPEAKER_FOLDER_NAME

_MODEL_FILE_GROUPS: tuple[tuple[str, ...], ...] = (
    ("config.yaml",),
    ("BiCodec/config.yaml",),
    ("BiCodec/model.safetensors",),
    ("LLM/config.json",),
    ("LLM/model.safetensors",),
    ("LLM/tokenizer.json", "LLM/tokenizer_config.json"),
    ("LLM/vocab.json", "LLM/merges.txt"),
    ("wav2vec2-large-xlsr-53/config.json",),
    ("wav2vec2-large-xlsr-53/preprocessor_config.json",),
    ("wav2vec2-large-xlsr-53/pytorch_model.bin", "wav2vec2-large-xlsr-53/model.safetensors"),
)


def _models_root() -> Path:
    try:
        import folder_paths

        root = getattr(folder_paths, "models_dir", "")
        if root:
            return Path(root)
    except Exception:
        pass
    configured = os.environ.get("COMFYUI_MODELS_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path.cwd() / "models"


def _model_candidates(root: Path | None = None) -> list[Path]:
    models_root = Path(root) if root is not None else _models_root()
    candidates: list[Path] = []
    override = os.environ.get("AICG3D_SPARK_TTS_MODEL", "").strip()
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend(
        (
            models_root / "tts" / MODEL_FOLDER_NAME,
            models_root / "TTS" / MODEL_FOLDER_NAME,
            models_root / MODEL_FOLDER_NAME,
        )
    )
    deduplicated: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(str(candidate)))
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(candidate)
    return deduplicated


def find_model_dir(models_root: Path | None = None) -> Path | None:
    fallback = None
    for candidate in _model_candidates(models_root):
        if not candidate.is_dir():
            continue
        if fallback is None:
            fallback = candidate
        if not missing_model_files(candidate):
            return candidate
    return fallback


def missing_model_files(model_dir: Path) -> list[str]:
    missing: list[str] = []
    for alternatives in _MODEL_FILE_GROUPS:
        if not any((model_dir / relative).is_file() for relative in alternatives):
            missing.append(" 或 ".join(alternatives))
    return missing


def _speaker_candidates(models_root: Path | None = None) -> list[Path]:
    models_base = Path(models_root) if models_root is not None else _models_root()
    candidates: list[Path] = []
    override = os.environ.get("AICG3D_SPARK_TTS_SPEAKERS", "").strip()
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend(
        (
            models_base / "tts" / SPEAKER_FOLDER_NAME,
            models_base / "TTS" / SPEAKER_FOLDER_NAME,
            BUNDLED_SPEAKER_DIR,
        )
    )
    deduplicated: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(str(candidate)))
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(candidate)
    return deduplicated


def find_speaker_dir(models_root: Path | None = None) -> Path:
    for candidate in _speaker_candidates(models_root):
        if (candidate / "speakers_info.json").is_file():
            return candidate
    return BUNDLED_SPEAKER_DIR


def load_speaker_catalog(models_root: Path | None = None) -> dict[str, str]:
    speaker_dir = find_speaker_dir(models_root)
    info_path = speaker_dir / "speakers_info.json"
    try:
        payload = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(name): str(text or "")
        for name, text in payload.items()
        if str(name).strip()
    }


def resolve_speaker_audio(
    speaker_name: str, models_root: Path | None = None
) -> Path | None:
    speaker_dir = find_speaker_dir(models_root)
    expected_stems = {
        f"{speaker_name}_prompt.wav".casefold(),
        f"{speaker_name}_prompt.WAV".casefold(),
    }
    try:
        for entry in speaker_dir.iterdir():
            if entry.is_file() and entry.name.casefold() in expected_stems:
                return entry
    except OSError:
        return None
    return None


def spark_model_status(models_root: Path | None = None) -> dict[str, Any]:
    models_base = Path(models_root) if models_root is not None else _models_root()
    runtime_missing = [
        name
        for name in ("omegaconf", "soundfile", "soxr", "einx", "transformers")
        if importlib.util.find_spec(name) is None
    ]
    expected_dir = models_base / "tts" / MODEL_FOLDER_NAME
    model_dir = find_model_dir(models_base)
    missing = missing_model_files(model_dir) if model_dir is not None else list(
        " 或 ".join(group) for group in _MODEL_FILE_GROUPS
    )
    speaker_dir = find_speaker_dir(models_base)
    speakers = load_speaker_catalog(models_base)
    speaker_audio_missing = [
        name for name in speakers if resolve_speaker_audio(name, models_base) is None
    ]
    model_ready = (
        model_dir is not None
        and not missing
        and bool(speakers)
        and not speaker_audio_missing
    )
    installed = model_ready and not runtime_missing
    if installed:
        message = (
            f"Spark-TTS 已就绪。模型：{model_dir}；说话人参考：{speaker_dir}。"
        )
    elif model_ready:
        message = (
            "Spark-TTS 模型已就绪，但缺少运行依赖："
            + "、".join(runtime_missing)
            + "。请重启 ComfyUI 自动安装，或执行 python -m pip install "
            + " ".join(runtime_missing)
        )
    else:
        missing_text = "、".join(missing[:5]) if missing else "speakers_info.json"
        if len(missing) > 5:
            missing_text += " 等"
        if speaker_audio_missing:
            missing_text += "；缺少说话人音频：" + "、".join(speaker_audio_missing)
        if runtime_missing:
            missing_text += "；运行依赖：" + "、".join(runtime_missing)
        message = (
            "缺少 Spark-TTS-0.5B 模型或不完整。"
            f"请把完整模型文件夹放到：{expected_dir}。"
            f"下载地址：{MODEL_DOWNLOAD_URL}。"
            f"当前缺少：{missing_text}。"
        )
    return {
        "installed": installed,
        "model_dir": str(model_dir) if model_dir is not None else "",
        "expected_dir": str(expected_dir),
        "missing_files": missing,
        "runtime_missing": runtime_missing,
        "download_url": MODEL_DOWNLOAD_URL,
        "speaker_dir": str(speaker_dir),
        "speaker_source": "external" if speaker_dir != BUNDLED_SPEAKER_DIR else "bundled",
        "speaker_count": len(speakers),
        "speaker_audio_missing": speaker_audio_missing,
        "speaker_download_url": SPEAKER_DOWNLOAD_URL,
        "message": message,
    }


__all__ = [
    "BUNDLED_SPEAKER_DIR",
    "MODEL_DOWNLOAD_URL",
    "MODEL_FOLDER_NAME",
    "SPEAKER_FOLDER_NAME",
    "find_model_dir",
    "find_speaker_dir",
    "load_speaker_catalog",
    "missing_model_files",
    "resolve_speaker_audio",
    "spark_model_status",
]
