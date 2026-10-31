# Copyright (c) 2025 SparkAudio and Xinsheng Wang
# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""Bundled, dependency-isolated Spark-TTS nodes for AICG3D."""
from __future__ import annotations

import gc
import os
import platform
import re
import tempfile
import threading
from pathlib import Path

import numpy as np

from aicg3d_sparktts.model_status import (
    MODEL_DOWNLOAD_URL,
    find_speaker_dir,
    load_speaker_catalog,
    resolve_speaker_audio,
    spark_model_status,
)
from aicg3d_sparktts.utils.token_parser import (
    AGE_MAP,
    GENDER_MAP,
    LEVELS_MAP,
    TASK_TOKEN_MAP,
)

MODEL_CACHE = TOKENIZER = AUDIO_TOKENIZER = None
_LOCK = threading.RLock()
_MODEL_HINT = (
    "首次运行前，请把完整 Spark-TTS-0.5B 模型放到 "
    f"ComfyUI/models/tts/Spark-TTS-0.5B。下载地址：{MODEL_DOWNLOAD_URL}"
)


def _device():
    import torch

    if platform.system() == "Darwin" and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _ready_model() -> Path:
    status = spark_model_status()
    if not status["installed"]:
        raise RuntimeError(status["message"])
    return Path(status["model_dir"])


def _require_dependencies() -> None:
    import importlib.util

    modules = ("omegaconf", "soundfile", "soxr", "einx", "transformers")
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError(
            "Spark-TTS 缺少运行依赖："
            + "、".join(missing)
            + "。请重启 ComfyUI 自动安装，或执行 python -m pip install "
            + " ".join(missing)
        )


def _load_models(device):
    _require_dependencies()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from aicg3d_sparktts.models.audio_tokenizer import BiCodecTokenizer

    model_dir = _ready_model()
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir / "LLM"))
    model = AutoModelForCausalLM.from_pretrained(str(model_dir / "LLM"))
    model.to(device).eval()
    audio_tokenizer = BiCodecTokenizer(model_dir, device=device)
    return tokenizer, model, audio_tokenizer


class SparkTTS:
    """Inference wrapper with controllable and cloned voices."""

    _aicg3d_supports_age = True

    def __init__(self, tokenizer, model, audio_tokenizer, device, model_dir: Path):
        from aicg3d_sparktts.utils.file import load_config

        self.tokenizer = tokenizer
        self.model = model
        self.audio_tokenizer = audio_tokenizer
        self.device = device
        self.sample_rate = int(load_config(str(model_dir / "config.yaml"))["sample_rate"])

    def cleanup(self) -> None:
        import torch

        self.tokenizer = self.model = self.audio_tokenizer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def process_prompt_control(self, gender, age, pitch, speed, text) -> str:
        if (
            gender not in GENDER_MAP
            or age not in AGE_MAP
            or pitch not in LEVELS_MAP
            or speed not in LEVELS_MAP
        ):
            raise ValueError("Spark-TTS 声线参数无效")
        style = (
            f"<|gender_{GENDER_MAP[gender]}|>"
            f"<|pitch_label_{LEVELS_MAP[pitch]}|>"
            f"<|speed_label_{LEVELS_MAP[speed]}|>"
            f"<|age_{AGE_MAP[age]}|>"
        )
        return (
            f"{TASK_TOKEN_MAP['controllable_tts']}<|start_content|>{text}"
            f"<|end_content|><|start_style_label|>{style}<|end_style_label|>"
        )

    def process_prompt(self, text, audio_path, prompt_text):
        global_ids, semantic_ids = self.audio_tokenizer.tokenize(str(audio_path))
        global_tokens = "".join(
            f"<|bicodec_global_{i}|>" for i in global_ids.squeeze()
        )
        head = f"{TASK_TOKEN_MAP['tts']}<|start_content|>"
        tail = (
            f"<|end_content|><|start_global_token|>{global_tokens}"
            "<|end_global_token|>"
        )
        if prompt_text is not None:
            semantic_tokens = "".join(
                f"<|bicodec_semantic_{i}|>" for i in semantic_ids.squeeze()
            )
            return (
                f"{head}{prompt_text}{text}{tail}"
                f"<|start_semantic_token|>{semantic_tokens}",
                global_ids,
            )
        return f"{head}{text}{tail}", global_ids

    def inference(
        self,
        text: str,
        prompt_speech_path=None,
        prompt_text=None,
        gender=None,
        age="Youth-Adult",
        pitch="moderate",
        speed="moderate",
        temperature=0.8,
        top_k=50,
        top_p=0.95,
        max_new_tokens=3000,
        do_sample=True,
    ):
        import torch

        with torch.inference_mode():
            if gender is not None:
                prompt = self.process_prompt_control(gender, age, pitch, speed, text)
            elif prompt_speech_path is not None:
                prompt, global_ids = self.process_prompt(
                    text, prompt_speech_path, prompt_text
                )
            else:
                raise ValueError("Spark-TTS 缺少参考音频或声线控制参数")
            inputs = self.tokenizer([prompt], return_tensors="pt").to(self.device)
            output = self.model.generate(
                **inputs,
                max_new_tokens=int(max_new_tokens),
                do_sample=bool(do_sample),
                top_k=int(top_k),
                top_p=float(top_p),
                temperature=float(temperature),
            )
            generated = [row[len(src):] for src, row in zip(inputs.input_ids, output)]
            decoded = self.tokenizer.batch_decode(
                generated, skip_special_tokens=True
            )[0]
            semantic = [
                int(token)
                for token in re.findall(r"bicodec_semantic_(\d+)", decoded)
            ]
            if not semantic:
                raise RuntimeError(
                    "Spark-TTS 没有生成有效语音 token，请检查模型是否完整。"
                )
            semantic_ids = torch.tensor(
                [semantic], dtype=torch.long, device=self.device
            )
            if gender is not None:
                values = [
                    int(token)
                    for token in re.findall(r"bicodec_global_(\d+)", decoded)
                ]
                if not values:
                    raise RuntimeError(
                        "Spark-TTS 没有生成有效音色 token，请检查模型是否完整。"
                    )
                global_ids = torch.tensor(
                    [values], dtype=torch.long, device=self.device
                ).unsqueeze(0)
            return self.audio_tokenizer.detokenize(
                global_ids.to(self.device).squeeze(0), semantic_ids
            )


def _audio_result(wav, sample_rate):
    import torch

    values = np.asarray(wav, dtype=np.float32).squeeze()
    if not values.size or not np.isfinite(values).all():
        raise RuntimeError("Spark-TTS 返回空音频或无效音频")
    waveform = torch.from_numpy(np.ascontiguousarray(values)).reshape(1, 1, -1)
    return ({"waveform": waveform, "sample_rate": int(sample_rate)},)


def _run_spark(text, unload_model, seed, infer):
    global MODEL_CACHE, TOKENIZER, AUDIO_TOKENIZER

    if not str(text or "").strip():
        raise ValueError("Spark-TTS 输入文本不能为空")
    model_dir = _ready_model()
    if seed:
        import torch

        torch.manual_seed(int(seed))
        np.random.seed(int(seed) & 0xFFFFFFFF)
    with _LOCK:
        device = _device()
        if MODEL_CACHE is None:
            TOKENIZER, MODEL_CACHE, AUDIO_TOKENIZER = _load_models(device)
        tts = SparkTTS(TOKENIZER, MODEL_CACHE, AUDIO_TOKENIZER, device, model_dir)
        try:
            return _audio_result(infer(tts), tts.sample_rate)
        finally:
            if unload_model:
                tts.cleanup()
                MODEL_CACHE = TOKENIZER = AUDIO_TOKENIZER = None
                gc.collect()


class SparkTTSRun:
    CATEGORY = "AICG3D/H3 语音"
    FUNCTION = "speak"
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    DESCRIPTION = _MODEL_HINT

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": _MODEL_HINT},
                ),
                "gender": (["female", "male"], {"default": "female"}),
                "age": (list(AGE_MAP), {"default": "Youth-Adult"}),
                "pitch": (list(LEVELS_MAP), {"default": "moderate"}),
                "speed": (list(LEVELS_MAP), {"default": "moderate"}),
                "temperature": (
                    "FLOAT",
                    {"default": 0.8, "min": 0, "max": 1.5, "step": 0.05},
                ),
                "top_k": ("INT", {"default": 50, "min": 0}),
                "top_p": (
                    "FLOAT",
                    {"default": 0.95, "min": 0, "max": 1, "step": 0.01},
                ),
                "max_new_tokens": ("INT", {"default": 3000, "min": 128}),
                "do_sample": ("BOOLEAN", {"default": True}),
                "unload_model": ("BOOLEAN", {"default": True}),
                "seed": (
                    "INT",
                    {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
            }
        }

    def speak(
        self,
        text,
        gender,
        pitch,
        speed,
        temperature,
        top_k,
        top_p,
        max_new_tokens,
        do_sample,
        unload_model,
        seed,
        age=None,
    ):
        age = age or globals().get("_AICG3D_ACTIVE_AGE") or "Youth-Adult"
        return _run_spark(
            text,
            unload_model,
            seed,
            lambda tts: tts.inference(
                text,
                gender=gender,
                age=age,
                pitch=pitch,
                speed=speed,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
            ),
        )


def _speaker_choices():
    return list(load_speaker_catalog()) or ["婷婷"]


def _write_temp_audio(audio, directory):
    import soundfile as sf

    waveform = audio["waveform"].detach().cpu().float().squeeze(0)
    values = waveform.transpose(0, 1).numpy()
    path = os.path.join(directory, "reference.wav")
    sf.write(
        path,
        np.ascontiguousarray(values),
        int(audio["sample_rate"]),
        subtype="PCM_16",
    )
    return path


class SparkTTSClone:
    CATEGORY = "AICG3D/H3 语音"
    FUNCTION = "clone"
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    DESCRIPTION = _MODEL_HINT

    @classmethod
    def INPUT_TYPES(cls):
        speakers = _speaker_choices()
        return {
            "required": {
                "text": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": _MODEL_HINT},
                ),
                "cloned_speaker": (speakers, {"default": speakers[0]}),
                "temperature": (
                    "FLOAT",
                    {"default": 0.8, "min": 0, "max": 1.5, "step": 0.05},
                ),
                "top_k": ("INT", {"default": 50, "min": 0}),
                "top_p": (
                    "FLOAT",
                    {"default": 0.95, "min": 0, "max": 1, "step": 0.01},
                ),
                "max_new_tokens": ("INT", {"default": 3000, "min": 128}),
                "do_sample": ("BOOLEAN", {"default": True}),
                "unload_model": ("BOOLEAN", {"default": True}),
                "seed": (
                    "INT",
                    {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
            },
            "optional": {
                "custom_clone_text": ("STRING", {"default": "", "multiline": True}),
                "custom_clone_audio": ("AUDIO",),
            },
        }

    def clone(
        self,
        text,
        cloned_speaker,
        temperature,
        top_k,
        top_p,
        max_new_tokens,
        do_sample,
        unload_model,
        seed,
        custom_clone_text=None,
        custom_clone_audio=None,
    ):
        if custom_clone_audio is None:
            audio_path = resolve_speaker_audio(cloned_speaker)
            if audio_path is None:
                raise RuntimeError(
                    f"内置说话人 {cloned_speaker} 的参考音频缺失，"
                    f"请重新安装插件或放到 {find_speaker_dir()}"
                )
            clone_text = load_speaker_catalog().get(cloned_speaker)

            def infer(tts):
                return tts.inference(
                    text,
                    prompt_speech_path=audio_path,
                    prompt_text=clone_text,
                    gender=None,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    max_new_tokens=max_new_tokens,
                    do_sample=do_sample,
                )

        else:
            clone_text = str(custom_clone_text or "").strip() or None

            def infer(tts):
                with tempfile.TemporaryDirectory(
                    prefix="aicg3d_sparktts_"
                ) as temp_dir:
                    return tts.inference(
                        text,
                        prompt_speech_path=Path(
                            _write_temp_audio(custom_clone_audio, temp_dir)
                        ),
                        prompt_text=clone_text,
                        gender=None,
                        temperature=temperature,
                        top_k=top_k,
                        top_p=top_p,
                        max_new_tokens=max_new_tokens,
                        do_sample=do_sample,
                    )

        return _run_spark(text, unload_model, seed, infer)


NODE_CLASS_MAPPINGS = {
    "AICG3D_SparkTTSRun": SparkTTSRun,
    "AICG3D_SparkTTSClone": SparkTTSClone,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AICG3D_SparkTTSRun": "AICG3D Spark-TTS 固定声线生成",
    "AICG3D_SparkTTSClone": "AICG3D Spark-TTS 音色克隆",
}
LEGACY_NODE_CLASS_MAPPINGS = {
    "SparkTTSRun": SparkTTSRun,
    "SparkTTSClone": SparkTTSClone,
}
LEGACY_NODE_DISPLAY_NAME_MAPPINGS = {
    "SparkTTSRun": "Spark-TTS 固定声线生成（AICG3D 内置兼容）",
    "SparkTTSClone": "Spark-TTS 音色克隆（AICG3D 内置兼容）",
}

__all__ = [
    "MODEL_CACHE",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "SparkTTS",
    "SparkTTSClone",
    "SparkTTSRun",
]
