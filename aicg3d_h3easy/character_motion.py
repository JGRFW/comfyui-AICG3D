# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Character replacement and motion-rig nodes.

This module merges the newer workflow-facing nodes without replacing the
existing H3 node module.  Keeping the additions here preserves current
sampling, seam, exposure and preview improvements while making workflow 15
load with its expected node IDs and parameters.
"""

from __future__ import annotations

import importlib
import json
import math
import os
import sys
import types
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import psutil
import torch

import comfy.model_management
import comfy.samplers
import comfy.utils
import folder_paths
import nodes
from comfy_api.latest import InputImpl, Types
from comfy_extras import nodes_audio

import aicg3d_h3easy.nodes as h3


MEDIA_BUNDLE_TYPE = h3.MEDIA_BUNDLE_TYPE
SEGMENT_RESULT_TYPE = h3.SEGMENT_RESULT_TYPE
MEDIA_LOADER_GROUPS = h3.MEDIA_LOADER_GROUPS

MEDIA_LOADER_VIDEO_MIN_SIDE = 256
MEDIA_LOADER_VIDEO_MEMORY_FRACTION = 0.45
MEDIA_LOADER_VIDEO_MEMORY_RESERVE_BYTES = 1536 * 1024 ** 2


def _media_loader_entry_trim(raw: Mapping[str, Any]) -> dict[str, float]:
    trim: dict[str, float] = {}
    for key in ("start", "end", "duration"):
        try:
            number = float(raw.get(key))
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number >= 0:
            trim[key] = number
    if trim.get("end", 0.0) <= trim.get("start", 0.0):
        trim.pop("end", None)
    return trim


def _media_loader_normalize_state(value: Any) -> dict[str, list[dict[str, Any]]]:
    """Parse the canvas-managed media list while preserving trim metadata."""
    result = {kind: [] for kind, _maximum in MEDIA_LOADER_GROUPS}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = {}
    if not isinstance(value, Mapping):
        return result
    for kind, maximum in MEDIA_LOADER_GROUPS:
        entries = value.get(f"{kind}s")
        if not isinstance(entries, list):
            continue
        seen = set()
        for raw in entries:
            filename = str(raw.get("filename") if isinstance(raw, Mapping) else raw or "").strip()
            filename = filename.replace("\\", "/").lstrip("/")
            if not filename or "\x00" in filename or os.path.isabs(filename):
                continue
            parts = [part for part in filename.split("/") if part and part != "."]
            if not parts or any(part == ".." for part in parts):
                continue
            normalized = "/".join(parts)
            if normalized in seen:
                continue
            seen.add(normalized)
            entry = {"filename": normalized}
            if isinstance(raw, Mapping):
                entry.update(_media_loader_entry_trim(raw))
            result[kind].append(entry)
            if maximum is not None and len(result[kind]) >= maximum:
                break
    return result


def _media_loader_input_path(filename: str) -> str:
    path = folder_paths.get_annotated_filepath(filename, folder_paths.get_input_directory())
    if not os.path.isfile(path):
        raise ValueError(f"Media Loader cannot find input file: {filename}")
    return path


def _media_loader_trim_bounds(
    entry: Mapping[str, Any] | None,
    duration: float | None = None,
) -> tuple[float, float | None]:
    data = entry if isinstance(entry, Mapping) else {}
    start = max(0.0, float(data.get("start") or 0.0))
    try:
        end = float(data.get("end")) if data.get("end") is not None else None
    except (TypeError, ValueError):
        end = None
    if end is not None and math.isfinite(end) and end > start:
        return start, min(end, duration) if duration is not None else end
    return start, duration


def _media_loader_load_audio(
    path: str,
    entry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        waveform, sample_rate = nodes_audio.load(path)
    except Exception as exc:
        raise ValueError(
            f"Media Loader could not read audio file {os.path.basename(path)!r}: {exc}"
        ) from exc
    if not isinstance(waveform, torch.Tensor) or waveform.ndim != 2 or waveform.shape[-1] < 1:
        raise ValueError(
            f"Media Loader found no usable audio samples in {os.path.basename(path)!r}"
        )
    duration = waveform.shape[-1] / max(1, int(sample_rate))
    start, end = _media_loader_trim_bounds(entry, duration)
    if start > 0 or end is not None:
        start_sample = min(waveform.shape[-1], int(round(start * sample_rate)))
        end_sample = waveform.shape[-1] if end is None else min(
            waveform.shape[-1], int(round(end * sample_rate))
        )
        if end_sample <= start_sample:
            raise ValueError(f"Media Loader audio trim is empty in {os.path.basename(path)!r}")
        waveform = waveform[..., start_sample:end_sample]
    return {
        "waveform": waveform.unsqueeze(0).to(device="cpu", dtype=torch.float32).contiguous(),
        "sample_rate": int(sample_rate),
    }


def _media_loader_auto_video_side(
    width: int,
    height: int,
    frame_count: int,
    requested_long_side: int = 0,
) -> int:
    """Choose a safe decode long side while preserving the full duration."""
    requested = max(0, int(requested_long_side or 0))
    if requested:
        return max(16, requested)
    longest = max(1, int(width), int(height))
    frame_count = max(1, int(frame_count or 1))
    source_bytes = max(1, int(width) * int(height) * 3 * 4 * frame_count)
    try:
        available = int(psutil.virtual_memory().available)
    except Exception:
        available = 8 * 1024 ** 3
    usable = max(
        256 * 1024 ** 2,
        int((available - MEDIA_LOADER_VIDEO_MEMORY_RESERVE_BYTES) * MEDIA_LOADER_VIDEO_MEMORY_FRACTION),
    )
    target_bytes = max(256 * 1024 ** 2, usable // 2)
    if source_bytes <= target_bytes:
        return longest
    scale = math.sqrt(target_bytes / float(source_bytes))
    side = int(math.floor(longest * scale / 16.0) * 16)
    return max(MEDIA_LOADER_VIDEO_MIN_SIDE, min(longest, side))


def _media_loader_decode_video_limited(
    path: str,
    start: float,
    end: float | None,
    requested_long_side: int = 0,
) -> tuple[torch.Tensor, float, dict[str, Any] | None]:
    """Decode video frames one at a time and resize before retaining them."""
    try:
        import av
    except Exception as exc:
        raise ValueError("Media Loader 需要 PyAV 才能读取视频") from exc

    frames: list[torch.Tensor] = []
    with av.open(path, mode="r") as container:
        stream = next((candidate for candidate in container.streams if candidate.type == "video"), None)
        if stream is None:
            raise ValueError("视频中没有可用的视频流")
        try:
            stream.thread_type = "AUTO"
        except Exception:
            pass

        rate = stream.average_rate or stream.base_rate or 24
        fps = max(1.0, float(rate))
        source_duration = None
        if stream.duration is not None and stream.time_base is not None:
            source_duration = float(stream.duration * stream.time_base)
        elif container.duration is not None:
            source_duration = float(container.duration / av.time_base)
        start = max(0.0, float(start or 0.0))
        if end is not None and source_duration is not None:
            end = min(float(end), source_duration)

        source_width = int(
            getattr(stream, "width", 0) or getattr(stream.codec_context, "width", 0) or 1
        )
        source_height = int(
            getattr(stream, "height", 0) or getattr(stream.codec_context, "height", 0) or 1
        )
        estimated_frames = int(getattr(stream, "frames", 0) or 0)
        if estimated_frames <= 0 and source_duration is not None:
            estimated_frames = max(1, int(math.ceil(source_duration * fps)))
        target_long_side = _media_loader_auto_video_side(
            source_width,
            source_height,
            estimated_frames,
            requested_long_side,
        )

        for decode_index, frame in enumerate(container.decode(stream)):
            frame_time = getattr(frame, "time", None)
            if frame_time is None:
                frame_time = decode_index / fps
            frame_time = float(frame_time)
            if frame_time < start:
                continue
            if end is not None and frame_time > end:
                break
            width, height = int(frame.width), int(frame.height)
            longest = max(width, height)
            if longest > target_long_side:
                scale = target_long_side / float(longest)
                target_w = max(16, int(round(width * scale / 16.0)) * 16)
                target_h = max(16, int(round(height * scale / 16.0)) * 16)
                frame = frame.reformat(width=target_w, height=target_h, format="rgb24")
            elif frame.format.name != "rgb24":
                frame = frame.reformat(format="rgb24")
            image = frame.to_ndarray(format="rgb24")
            frames.append(torch.from_numpy(image).to(dtype=torch.float32).div_(255.0))

    if not frames:
        raise ValueError("视频在指定时间范围内没有可读取的帧")
    images = torch.stack(frames, dim=0).contiguous()

    cached_audio = None
    try:
        waveform, sample_rate = nodes_audio.load(path)
        if isinstance(waveform, torch.Tensor) and waveform.ndim == 2 and waveform.shape[-1] > 0:
            audio_duration = waveform.shape[-1] / max(1, int(sample_rate))
            audio_start, audio_end = _media_loader_trim_bounds(
                {"start": start, "end": end},
                audio_duration,
            )
            start_sample = min(waveform.shape[-1], int(round(audio_start * sample_rate)))
            end_sample = waveform.shape[-1] if audio_end is None else min(
                waveform.shape[-1], int(round(audio_end * sample_rate))
            )
            waveform = waveform[..., start_sample:end_sample]
            if waveform.shape[-1] > 0:
                cached_audio = {
                    "waveform": waveform.unsqueeze(0).to(
                        device="cpu", dtype=torch.float32
                    ).contiguous(),
                    "sample_rate": int(sample_rate),
                }
    except Exception:
        cached_audio = None
    return images, fps, cached_audio


def _media_loader_load_video(
    path: str,
    entry: Mapping[str, Any] | None = None,
    requested_long_side: int = 0,
) -> dict[str, Any]:
    start, end = _media_loader_trim_bounds(entry)
    frames, fps, audio = _media_loader_decode_video_limited(
        path,
        start,
        end,
        requested_long_side,
    )
    return {
        "images": frames,
        "audio": audio,
        "fps": float(fps),
    }


class MiniMaxH3EasyMediaLoaderVideoAware(h3.MiniMaxH3EasyMediaLoader):
    """Existing resource library with video trim and memory-safe decode controls."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "media_state": ("STRING", {"default": "", "multiline": False}),
                "视频解码长边": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 8192,
                        "step": 16,
                        "tooltip": (
                            "0=自动按系统可用内存选择安全解码尺寸；完整时长和音频始终保留。"
                            "也可手动指定长边，例如 1024、1920 或 0。"
                        ),
                    },
                ),
            },
        }

    @classmethod
    def IS_CHANGED(cls, media_state="", 视频解码长边=0, **_kwargs):
        state = _media_loader_normalize_state(media_state)
        signature = []
        for kind, _maximum in MEDIA_LOADER_GROUPS:
            for entry in state[kind]:
                filename = entry["filename"]
                trim = tuple(
                    sorted(
                        (key, entry.get(key))
                        for key in ("start", "end", "duration")
                        if key in entry
                    )
                )
                try:
                    stat = os.stat(_media_loader_input_path(filename))
                    signature.append((kind, filename, stat.st_mtime_ns, stat.st_size, trim))
                except (OSError, ValueError):
                    signature.append((kind, filename, None, None, trim))
        return repr((signature, int(视频解码长边 or 0)))

    @classmethod
    def VALIDATE_INPUTS(cls, media_state="", **_kwargs):
        state = _media_loader_normalize_state(media_state)
        for kind, _maximum in MEDIA_LOADER_GROUPS:
            for entry in state[kind]:
                try:
                    _media_loader_input_path(entry["filename"])
                except ValueError as exc:
                    return str(exc)
        return True

    def load(self, media_state="", 视频解码长边=0):
        state = _media_loader_normalize_state(media_state)
        items: list[Any] = []
        input_index = 0
        for media_type, _maximum in MEDIA_LOADER_GROUPS:
            for entry in state[media_type]:
                filename = entry["filename"]
                path = _media_loader_input_path(filename)
                if media_type == "image":
                    value = nodes.LoadImage().load_image(filename)[0]
                elif media_type == "audio":
                    value = _media_loader_load_audio(path, entry)
                else:
                    value = _media_loader_load_video(path, entry, 视频解码长边)
                input_index += 1
                items.append(h3._MediaInput(input_index, media_type, value))
        return (h3.MiniMaxH3MediaBundle(tuple(items)),)


def _node_output_value(output: Any, index: int = 0) -> Any:
    value = getattr(output, "result", output)
    if isinstance(value, (tuple, list)):
        if index >= len(value):
            raise ValueError(f"Node output has no item {index}")
        return value[index]
    return value


def _white_model_release_models() -> None:
    try:
        comfy.model_management.unload_all_models()
    except Exception:
        pass
    try:
        comfy.model_management.soft_empty_cache(force=True)
    except Exception:
        pass


def _white_model_video_payload(
    bundle: Any,
    direct_video: Any = None,
) -> tuple[torch.Tensor, float, Mapping[str, Any] | None]:
    value = direct_video
    if value is None:
        for item in getattr(bundle, "items", ()):
            if str(getattr(item, "media_type", "")) == "video":
                value = getattr(item, "value", None)
                break
    if value is None:
        raise ValueError("3D 白模节点需要接入 AICG3D 资源库，或直接接入 VIDEO")
    if isinstance(value, Mapping):
        frames = value.get("images")
        fps = float(value.get("fps") or value.get("frame_rate") or 24.0)
        audio = value.get("audio") if isinstance(value.get("audio"), Mapping) else None
        if isinstance(frames, torch.Tensor) and frames.ndim == 4 and frames.shape[0] > 0:
            return (
                frames[..., :3].detach().to(device="cpu", dtype=torch.float32).contiguous(),
                fps,
                audio,
            )
    if hasattr(value, "get_components"):
        components = value.get_components()
        frames = components.images
        if not isinstance(frames, torch.Tensor) or frames.ndim != 4 or frames.shape[0] < 1:
            raise ValueError("接入的视频没有可用的 IMAGE 帧")
        audio = components.audio if isinstance(components.audio, Mapping) else None
        return (
            frames[..., :3].detach().to(device="cpu", dtype=torch.float32).contiguous(),
            float(components.frame_rate or 24.0),
            audio,
        )
    raise ValueError("不支持这种视频数据格式")


class MiniMaxH3EasyWhiteModelRig:
    """Video -> SAM3/MoGe/SAM3DBody -> white 3D body model video."""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "render"
    RETURN_TYPES = ("VIDEO", "IMAGE", "AUDIO", "FLOAT", "STRING")
    RETURN_NAMES = ("white_video", "white_frames", "audio", "fps", "status")
    DESCRIPTION = (
        "把资源库视频转成 3D 白模动作视频，并保留原始音频，"
        "供人物动作和场景替换节点继续使用。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        checkpoints = folder_paths.get_filename_list("checkpoints")
        rtdetr = [
            name
            for name in folder_paths.get_filename_list("diffusion_models")
            if "rt_detr" in name.lower()
        ]
        body_models = [
            name
            for name in folder_paths.get_filename_list("detection")
            if "sam_3d_body" in name.lower()
        ]
        moge_models = [
            name
            for name in folder_paths.get_filename_list("geometry_estimation")
            if "moge" in name.lower()
        ]

        def preferred(values, contains, fallback):
            return next(
                (name for name in values if contains in name.lower()),
                values[0] if values else fallback,
            )

        return {
            "optional": {
                "media_bundle": (
                    MEDIA_BUNDLE_TYPE,
                    {"tooltip": "接现有 MiniMax H3 Aicg资源库；默认取其第一条视频。"},
                ),
                "video": ("VIDEO", {"tooltip": "也可以直接接 VIDEO；连接后优先于资源库。"}),
                "background": ("IMAGE", {"tooltip": "可选白模背景；不接则输出黑底白模。"}),
            },
            "required": {
                "目标提示词": (
                    "STRING",
                    {"default": "person", "tooltip": "SAM3 文字检测提示词；默认 person。"},
                ),
                "sam3_checkpoint": (
                    checkpoints or ["sam3.1_multiplex_fp16.safetensors"],
                    {
                        "default": preferred(
                            checkpoints,
                            "sam3.1_multiplex",
                            "sam3.1_multiplex_fp16.safetensors",
                        )
                    },
                ),
                "rtdetr_model": (
                    rtdetr or ["rt_detr_v4-x-hgnet_fp16.safetensors"],
                    {
                        "default": preferred(
                            rtdetr,
                            "rt_detr_v4-x-hgnet_fp16",
                            "rt_detr_v4-x-hgnet_fp16.safetensors",
                        )
                    },
                ),
                "body_model": (
                    body_models or ["sam_3d_body_dinov3_bf16.safetensors"],
                    {
                        "default": preferred(
                            body_models,
                            "sam_3d_body_dinov3_bf16",
                            "sam_3d_body_dinov3_bf16.safetensors",
                        )
                    },
                ),
                "moge_model": (
                    moge_models or ["geometry_estimation\\moge_3_vitg_fp16.safetensors"],
                    {
                        "default": preferred(
                            moge_models,
                            "moge_3_vitg_fp16",
                            "geometry_estimation\\moge_3_vitg_fp16.safetensors",
                        )
                    },
                ),
                "启用MoGe": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "开启后用 MoGe 估算 FOV/几何；16GB 显存建议先关闭，默认 53° 也能跑。",
                    },
                ),
                "MoGe分辨率等级": ("INT", {"default": 5, "min": 0, "max": 9, "step": 1}),
                "MoGe细化步数": ("INT", {"default": 0, "min": 0, "max": 8, "step": 1}),
                "最大人物数": ("INT", {"default": 16, "min": 1, "max": 64, "step": 1}),
                "检测阈值": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "检测间隔": ("INT", {"default": 1, "min": 1, "max": 16, "step": 1}),
                "长边像素": ("INT", {"default": 736, "min": 256, "max": 2048, "step": 16}),
                "推理批大小": ("INT", {"default": 64, "min": 1, "max": 512, "step": 1}),
                "渲染模式": (
                    ["mesh", "silhouette", "openpose_2d", "openpose_3d", "scail"],
                    {"default": "mesh"},
                ),
                "着色器": (
                    [
                        "default",
                        "normals",
                        "rainbow",
                        "rainbow_face_normal",
                        "rainbow_face_semantic",
                        "depth",
                    ],
                    {"default": "default"},
                ),
                "人物颜色衰减": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.1,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": "1.0 = 所有人物统一白模颜色。",
                    },
                ),
                "启用表情": ("BOOLEAN", {"default": True}),
                "启用平滑": ("BOOLEAN", {"default": True}),
                "保留原始音频": ("BOOLEAN", {"default": True}),
                "保留原视频场景": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "开启后，白模叠加在原视频画面上，保留原始背景；需要替换背景时请关闭。",
                    },
                ),
                "绿色背景": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "关闭“保留原视频场景”后生效；输出纯绿幕白模，便于后续背景替换。",
                    },
                ),
                "逐人锁定颜色": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "用 SAM3 跟踪 ID 给每个稳定人物分配固定颜色，便于区分替换1、替换2，"
                            "并在穿插走位时锁住身份。"
                        ),
                    },
                ),
                "人物颜色排序": (
                    ["左到右", "面积优先", "跟踪顺序"],
                    {
                        "default": "左到右",
                        "tooltip": (
                            "颜色按稳定人物首次出现后的顺序分配。左到右最符合常见替换编号；"
                            "固定调色板为蓝、红、绿、品红、青、黄循环。"
                        ),
                    },
                ),
                "人物颜色强度": (
                    "FLOAT",
                    {
                        "default": 0.75,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": (
                            "颜色叠加强度。0.75 既能明确区分人物，"
                            "又保留白模表面的动作和表情轮廓。"
                        ),
                    },
                ),
            },
        }

    @staticmethod
    def _colorize_tracked_people(
        white_frames: torch.Tensor,
        track_data: Any,
        sort_by: str,
        strength: float,
        background_kind: str = "black",
    ) -> tuple[torch.Tensor, int]:
        """Apply the core SCAIL colored-mask palette to each stable SAM3 track."""
        from comfy_extras.nodes_scail import SCAIL2ColoredMask

        packed = track_data.get("packed_masks") if isinstance(track_data, Mapping) else None
        if not isinstance(packed, torch.Tensor) or packed.ndim < 2 or int(packed.shape[1]) <= 0:
            return white_frames, 0

        sort_value = {
            "左到右": "left_to_right",
            "面积优先": "area",
            "跟踪顺序": "none",
        }.get(str(sort_by), "left_to_right")
        color_mask = _node_output_value(
            SCAIL2ColoredMask.execute(
                driving_track_data=track_data,
                ref_track_data=None,
                object_indices="",
                sort_by=sort_value,
                replacement_mode=False,
            )
        )
        if not isinstance(color_mask, torch.Tensor) or color_mask.ndim != 4:
            return white_frames, 0

        color_mask = color_mask.to(device=white_frames.device, dtype=white_frames.dtype)
        if tuple(color_mask.shape[1:3]) != tuple(white_frames.shape[1:3]):
            color_mask = comfy.utils.common_upscale(
                color_mask.movedim(-1, 1),
                int(white_frames.shape[2]),
                int(white_frames.shape[1]),
                "nearest-exact",
                "disabled",
            ).movedim(1, -1)
        if int(color_mask.shape[0]) != int(white_frames.shape[0]):
            if int(color_mask.shape[0]) < int(white_frames.shape[0]):
                pad = color_mask[-1:].repeat(
                    int(white_frames.shape[0]) - int(color_mask.shape[0]),
                    1,
                    1,
                    1,
                )
                color_mask = torch.cat((color_mask, pad), dim=0)
            else:
                color_mask = color_mask[: int(white_frames.shape[0])]

        palette = torch.tensor(
            [
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (1.0, 0.0, 1.0),
                (0.0, 1.0, 1.0),
                (1.0, 1.0, 0.0),
            ],
            device=color_mask.device,
            dtype=color_mask.dtype,
        )
        flat = color_mask.reshape(-1, 3)
        index = ((flat[:, None, :] - palette[None, 1:, :]) ** 2).sum(dim=-1).argmin(dim=1) + 1
        index = index.reshape(color_mask.shape[0], color_mask.shape[1], color_mask.shape[2])
        one_hot = torch.nn.functional.one_hot(index, num_classes=7).permute(0, 3, 1, 2).to(
            color_mask.dtype
        )
        kernel = 5 if str(background_kind) == "green" else 3
        dilated = torch.nn.functional.max_pool2d(
            one_hot,
            kernel_size=kernel,
            stride=1,
            padding=kernel // 2,
        )
        expanded_index = dilated.argmax(dim=1)
        color_source = palette[expanded_index]
        expanded_mask = expanded_index > 0

        if str(background_kind) == "green":
            green_dominant = (
                white_frames[..., 1]
                - torch.maximum(white_frames[..., 0], white_frames[..., 2])
            ).clamp(0.0, 1.0)
            person_alpha = (1.0 - green_dominant).clamp(0.0, 1.0)
        elif str(background_kind) == "black":
            person_alpha = white_frames.max(dim=-1).values
        else:
            person_alpha = expanded_mask.to(white_frames.dtype)

        amount = float(max(0.0, min(1.0, strength)))
        return white_frames.lerp(color_source, person_alpha.unsqueeze(-1) * amount), int(
            packed.shape[1]
        )

    def _render_impl(self, **kwargs):
        from comfy_extras.nodes_moge import LoadMoGeModel, MoGeGeometryToFOV, MoGeInference
        from comfy_extras.nodes_rtdetr import RTDETR_detect
        from comfy_extras.nodes_sam3 import SAM3_VideoTrack
        from comfy_extras.nodes_sam3d_body import (
            SAM3DBody_FaceExpression,
            SAM3DBody_Loader,
            SAM3DBody_Predict,
            SAM3DBody_Render,
            SAM3DBody_Smooth,
        )

        frames, fps, audio = _white_model_video_payload(
            kwargs.get("media_bundle"),
            kwargs.get("video"),
        )
        long_side = max(256, int(kwargs.get("长边像素") or 736))
        src_h, src_w = int(frames.shape[1]), int(frames.shape[2])
        scale = min(1.0, long_side / max(src_h, src_w))
        render_w = max(16, int(round(src_w * scale / 16) * 16))
        render_h = max(16, int(round(src_h * scale / 16) * 16))
        work_frames = comfy.utils.common_upscale(
            frames.movedim(-1, 1),
            render_w,
            render_h,
            "lanczos",
            crop="disabled",
        ).movedim(1, -1).contiguous()

        checkpoint_model, checkpoint_clip, _ = nodes.CheckpointLoaderSimple().load_checkpoint(
            str(kwargs.get("sam3_checkpoint"))
        )
        conditioning = nodes.CLIPTextEncode().encode(
            checkpoint_clip,
            str(kwargs.get("目标提示词") or "person"),
        )[0]

        max_objects = max(1, int(kwargs.get("最大人物数") or 16))
        threshold = float(kwargs.get("检测阈值") or 0.5)
        detect_interval = max(1, int(kwargs.get("检测间隔") or 1))
        track_data = _node_output_value(
            SAM3_VideoTrack.execute(
                images=work_frames,
                model=checkpoint_model,
                initial_mask=None,
                conditioning=conditioning,
                detection_threshold=threshold,
                max_objects=max_objects,
                detect_interval=detect_interval,
            )
        )
        del checkpoint_model, checkpoint_clip, conditioning
        _white_model_release_models()

        rtdetr_model = nodes.UNETLoader().load_unet(
            str(kwargs.get("rtdetr_model")),
            "default",
        )[0]
        bboxes = _node_output_value(
            RTDETR_detect.execute(
                model=rtdetr_model,
                image=work_frames,
                threshold=threshold,
                class_name="person",
                max_detections=max_objects,
            )
        )
        del rtdetr_model
        _white_model_release_models()

        if bool(kwargs.get("启用MoGe", False)):
            moge_model = _node_output_value(
                LoadMoGeModel.execute(str(kwargs.get("moge_model")))
            )
            moge_geometry = _node_output_value(
                MoGeInference.execute(
                    moge_model=moge_model,
                    image=work_frames,
                    resolution_level=int(kwargs.get("MoGe分辨率等级") or 5),
                    fov_x_degrees=0.0,
                    batch_size=4,
                    force_projection=True,
                    apply_mask=True,
                    refine_steps=int(kwargs.get("MoGe细化步数") or 0),
                )
            )
            fov = _node_output_value(
                MoGeGeometryToFOV.execute(moge_geometry, "vertical", "degrees"),
                0,
            )
            del moge_model, moge_geometry
        else:
            fov = 0.0
        _white_model_release_models()

        body_model = _node_output_value(
            SAM3DBody_Loader.execute(str(kwargs.get("body_model")))
        )

        pose_data = _node_output_value(
            SAM3DBody_Predict.execute(
                sam3d_body_model=body_model,
                image=work_frames,
                track_data=track_data,
                bboxes=bboxes,
                run_hand_refinement=True,
                fov=fov,
                batch_size=int(kwargs.get("推理批大小") or 64),
            )
        )
        if bool(kwargs.get("启用表情", True)):
            pose_data = _node_output_value(
                SAM3DBody_FaceExpression.execute(
                    sam3d_body_model=body_model,
                    mhr_pose_data=pose_data,
                    image=work_frames,
                    strength=1.0,
                    mouth_strength=1.0,
                    eye_strength=2.0,
                    brow_strength=2.0,
                    input_threshold=0.02,
                    blendshape_smooth_window=7,
                )
            )
        if bool(kwargs.get("启用平滑", True)):
            pose_data = _node_output_value(
                SAM3DBody_Smooth.execute(
                    mhr_pose_data=pose_data,
                    strength=1.0,
                    method="gaussian",
                    window=9,
                    rotation_threshold_degrees=30.0,
                )
            )

        render_mode = str(kwargs.get("渲染模式") or "mesh")
        explicit_background = kwargs.get("background")
        if explicit_background is not None:
            render_background = explicit_background
            background_kind = "external"
        elif bool(kwargs.get("保留原视频场景", False)):
            render_background = work_frames
            background_kind = "original"
        elif bool(kwargs.get("绿色背景", False)):
            render_background = torch.zeros_like(work_frames)
            render_background[..., 0] = 0.0
            render_background[..., 1] = 1.0
            render_background[..., 2] = 0.0
            background_kind = "green"
        else:
            render_background = None
            background_kind = "black"
        render_style = {
            "render_style": render_mode,
            "shader": {"shader": str(kwargs.get("着色器") or "default")},
            "opacity": 1.0,
            "person_palette_falloff": float(kwargs.get("人物颜色衰减") or 1.0),
            "region": "full_body",
        }
        white_frames = _node_output_value(
            SAM3DBody_Render.execute(
                pose_data=pose_data,
                background=render_background,
                width=render_w,
                height=render_h,
                render_style=render_style,
            )
        )
        colored_ids = 0
        if bool(kwargs.get("逐人锁定颜色", True)):
            white_frames, colored_ids = self._colorize_tracked_people(
                white_frames,
                track_data,
                str(kwargs.get("人物颜色排序") or "左到右"),
                float(kwargs.get("人物颜色强度") or 0.75),
                background_kind,
            )
        white_frames = white_frames.detach().to(
            device="cpu",
            dtype=torch.float32,
        ).contiguous()
        del body_model
        _white_model_release_models()

        audio_out = audio if bool(kwargs.get("保留原始音频", True)) else None
        components = Types.VideoComponents(
            images=white_frames,
            frame_rate=Fraction(str(float(fps))),
            audio=audio_out,
        )
        white_video = InputImpl.VideoFromComponents(components)
        color_status = f"，逐人颜色 ID={colored_ids}" if colored_ids else ""
        status = (
            f"3D 白模完成：{white_frames.shape[0]} 帧，"
            f"{render_w}x{render_h}，{fps:.4g} FPS{color_status}"
        )
        return white_video, white_frames, audio_out, float(fps), status

    def render(self, **kwargs):
        with torch.inference_mode():
            return self._render_impl(**kwargs)


_KJ_PREVIEW_NODE_CLASS = None
_KJ_PREVIEW_IMPORT_FAILED = False


def _load_kj_preview_override_class():
    """Load KJNodes' public ModelPreviewOverrideKJ class without copying it."""
    global _KJ_PREVIEW_NODE_CLASS, _KJ_PREVIEW_IMPORT_FAILED
    if _KJ_PREVIEW_NODE_CLASS is not None:
        return _KJ_PREVIEW_NODE_CLASS
    if _KJ_PREVIEW_IMPORT_FAILED:
        return None
    try:
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        custom_nodes_dir = os.path.dirname(plugin_dir)
        kj_nodes_dir = os.path.join(custom_nodes_dir, "comfyui-kjnodes", "nodes")
        if not os.path.isfile(os.path.join(kj_nodes_dir, "preview_override_node.py")):
            raise FileNotFoundError("comfyui-kjnodes/nodes/preview_override_node.py")
        package_name = "_aicg3d_kj_preview_runtime"
        if package_name not in sys.modules:
            package = types.ModuleType(package_name)
            package.__path__ = [kj_nodes_dir]
            sys.modules[package_name] = package
        module = importlib.import_module(f"{package_name}.preview_override_node")
        _KJ_PREVIEW_NODE_CLASS = getattr(module, "ModelPreviewOverrideKJ", None)
        if _KJ_PREVIEW_NODE_CLASS is None:
            raise RuntimeError("ModelPreviewOverrideKJ is not exported")
        return _KJ_PREVIEW_NODE_CLASS
    except Exception as error:
        _KJ_PREVIEW_IMPORT_FAILED = True
        print(f"[MiniMax H3 Aicg] 未能调用 KJNodes 模型预览：{error}")
        return None


def _apply_kj_preview_override(
    model,
    *,
    enabled,
    max_resolution,
    jpeg_quality,
    suppress_default_preview,
    preview_frames,
    preview_fps,
    vae,
    tiny_vae,
    audio_vae,
    unique_id,
):
    """Call KJNodes' public preview override node class without patching it."""
    if not enabled:
        return model
    preview_class = _load_kj_preview_override_class()
    if preview_class is None:
        return model

    original_hidden = getattr(preview_class, "hidden", None)
    try:
        preview_class.hidden = types.SimpleNamespace(unique_id=str(unique_id or "0"))
        output = preview_class.execute(
            model,
            int(max_resolution),
            int(jpeg_quality),
            bool(suppress_default_preview),
            int(preview_frames),
            int(preview_fps),
            vae,
            str(tiny_vae or "none"),
            audio_vae,
        )
    finally:
        preview_class.hidden = original_hidden
    result = getattr(output, "result", None)
    if not result:
        raise RuntimeError("KJNodes 模型预览没有返回 MODEL 输出")
    return result[0]


class MiniMaxH3EasySegmentSampler(h3.MiniMaxH3EasySegmentRender):
    """Segment sampler with built-in sampler/scheduler controls and overrides."""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "render_chain"
    RETURN_TYPES = (SEGMENT_RESULT_TYPE, "SAMPLER", "SIGMAS")
    RETURN_NAMES = ("segments", "sampler", "sigmas")
    DESCRIPTION = (
        "Combined segment sampler and scheduler. Built-in controls generate sampler/sigmas; "
        "optional sampler/sigmas inputs override them and the effective values are also exposed as outputs."
    )

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return repr(
            (
                kwargs.get("sampler_name"),
                kwargs.get("scheduler"),
                kwargs.get("steps"),
                kwargs.get("denoise"),
                kwargs.get("seed"),
                kwargs.get("segment_seeds"),
                kwargs.get("sampling_plan"),
                kwargs.get("preview_enabled"),
                kwargs.get("preview_max_resolution"),
                kwargs.get("preview_jpeg_quality"),
                kwargs.get("preview_suppress_default"),
                kwargs.get("preview_frames"),
                kwargs.get("preview_fps"),
                kwargs.get("tiny_vae"),
            )
        )

    @classmethod
    def INPUT_TYPES(cls):
        tiny_vae_models = folder_paths.get_filename_list("vae_approx")
        tiny_default = "taeh3.safetensors" if "taeh3.safetensors" in tiny_vae_models else "none"
        return {
            "required": {
                "model": ("MODEL",),
                "h3_context": ("MINIMAX_H3_CONTEXT",),
                "sampler_name": (comfy.samplers.SAMPLER_NAMES, {"default": "er_sde"}),
                "scheduler": (comfy.samplers.SCHEDULER_NAMES, {"default": "simple"}),
                "steps": ("INT", {"default": 25, "min": 1, "max": 10000}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 4294967295,
                        "control_after_generate": True,
                    },
                ),
                "segment_seeds": ("STRING", {"default": "default", "multiline": False}),
                "preview_enabled": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "直接在分段采样节点内调用 KJNodes 的模型预览，"
                            "不再额外接 Model Preview Override 节点。"
                        ),
                    },
                ),
                "preview_max_resolution": (
                    "INT",
                    {
                        "default": 360,
                        "min": 0,
                        "max": 8192,
                        "step": 8,
                        "tooltip": "预览图最长边；0 表示跟随采样分辨率。",
                    },
                ),
                "preview_jpeg_quality": (
                    "INT",
                    {
                        "default": 100,
                        "min": 30,
                        "max": 100,
                        "step": 1,
                        "tooltip": "预览图 JPEG 质量。",
                    },
                ),
                "preview_suppress_default": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "隐藏 ComfyUI 默认采样预览，只显示这个节点的预览面板。",
                    },
                ),
                "preview_frames": (
                    "INT",
                    {
                        "default": 277,
                        "min": 1,
                        "max": 1024,
                        "step": 1,
                        "tooltip": "每一步抽取的预览帧数；1 为单图，大于 1 为动态预览。",
                    },
                ),
                "preview_fps": (
                    "INT",
                    {"default": 12, "min": 1, "max": 60, "step": 1, "tooltip": "动态预览播放帧率。"},
                ),
                "tiny_vae": (
                    ["none", *tiny_vae_models],
                    {
                        "default": tiny_default,
                        "tooltip": "KJNodes 预览使用的 tiny VAE；选择 taeh3.safetensors 可显示真实 RGB 预览。",
                    },
                ),
            },
            "optional": {
                "sampler": ("SAMPLER",),
                "sigmas": ("SIGMAS",),
                "sampling_plan": (h3.SAMPLING_PLAN_TYPE,),
                "vae": ("VAE",),
                "audio_vae": ("VAE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @staticmethod
    def _build_sigmas(model, scheduler, steps, denoise):
        steps = max(1, int(steps))
        denoise = min(1.0, max(0.0, float(denoise)))
        model_sampling = model.get_model_object("model_sampling")
        if denoise >= 1.0:
            return comfy.samplers.calculate_sigmas(model_sampling, scheduler, steps)
        if denoise <= 0.0:
            return torch.FloatTensor([])
        total_steps = max(steps, int(steps / denoise))
        sigmas = comfy.samplers.calculate_sigmas(model_sampling, scheduler, total_steps)
        return sigmas[-(steps + 1):]

    @classmethod
    def render_chain(
        cls,
        model,
        h3_context,
        sampler_name,
        scheduler,
        steps,
        denoise,
        seed,
        segment_seeds,
        preview_enabled,
        preview_max_resolution,
        preview_jpeg_quality,
        preview_suppress_default,
        preview_frames,
        preview_fps,
        tiny_vae,
        sampler=None,
        sigmas=None,
        sampling_plan=None,
        vae=None,
        audio_vae=None,
        unique_id=None,
    ):
        model_obj = h3._resolve_h3_model(h3_context, model)
        model_obj = _apply_kj_preview_override(
            model_obj,
            enabled=bool(preview_enabled),
            max_resolution=preview_max_resolution,
            jpeg_quality=preview_jpeg_quality,
            suppress_default_preview=preview_suppress_default,
            preview_frames=preview_frames,
            preview_fps=preview_fps,
            vae=vae,
            tiny_vae=tiny_vae,
            audio_vae=audio_vae,
            unique_id=unique_id,
        )
        sampler_obj = sampler if sampler is not None else comfy.samplers.sampler_object(
            str(sampler_name)
        )
        sigmas_obj = sigmas if sigmas is not None else cls._build_sigmas(
            model_obj,
            scheduler,
            steps,
            denoise,
        )
        segments = super().render_chain(
            h3_context,
            model=model_obj,
            sampler=sampler_obj,
            sigmas=sigmas_obj,
            seed=seed,
            segment_seeds=segment_seeds,
            sampling_plan=sampling_plan,
        )[0]
        return segments, sampler_obj, sigmas_obj


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyMediaLoader": MiniMaxH3EasyMediaLoaderVideoAware,
    "MiniMaxH3EasyWhiteModelRig": MiniMaxH3EasyWhiteModelRig,
    "MiniMaxH3EasySegmentSampler": MiniMaxH3EasySegmentSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyMediaLoader": "MiniMax H3 Aicg资源库",
    "MiniMaxH3EasyWhiteModelRig": "MiniMax H3 Aicg 3D人物白模",
    "MiniMaxH3EasySegmentSampler": "MiniMax H3 Aicg 分段采样器",
}
