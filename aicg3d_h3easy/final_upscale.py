# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Final-sequence-only H3 upscale and restoration node.

Keeping this node separate from the story-segment renderer is intentional. The
record is already assembled when this node runs, so it cannot introduce a
second-pass exposure step at each story-segment boundary.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import torch

import comfy.samplers
import folder_paths
from comfy_api.latest import InputImpl, Types
from comfy_extras import nodes_minimax_h3 as h3

from aicg3d_h3easy import nodes as base


class MiniMaxH3EasyFinalHighResUpscale:
    """H3 latent upscale + second pass + optional video restoration for one final film."""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "upscale_final_video"
    OUTPUT_NODE = True
    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "saved_file", "upscale_report")
    DESCRIPTION = (
        "接在最终合成视频之后。先对整条成片做 H3 Latent 3D 放大与低降噪二采，"
        "再可选叠加 SeedVR2 / RTX VSR / VOSR2 画质修复或视频超分。"
        "长片自动按带重叠的时间窗口处理，只取各窗口中段，不在分段接缝处做混合；"
        "最终曝光对齐未处理成片，音频原轨直接封装，不经过二采或超分。"
    )

    @staticmethod
    def _upscale_model_choices() -> list[str]:
        return base.MiniMaxH3EasyRenderPass2._upscale_model_choices()

    @staticmethod
    def _repair_model_choices() -> list[str]:
        return base.MiniMaxH3EasyRenderPass2._repair_model_choices()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": (
                    "VIDEO",
                    {"tooltip": "接「最终合成视频」的 video 输出；必须是全部段落已经拼好的整片。"},
                ),
                "h3_bundle": (
                    "MINIMAX_H3_BUNDLE",
                    {"tooltip": "接 MiniMax H3 Aicg 加载器的 h3_bundle，用于 H3 Latent 二采。"},
                ),
                "filename_prefix": (
                    "STRING",
                    {"default": "video/MiniMax_H3_Final_HD"},
                ),
                "second_pass": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "开：H3 Latent 3D 放大后，再做低降噪 H3 二次采样。关：只运行下方超分/修复引擎。",
                    },
                ),
                "latent_upscale_model": (cls._upscale_model_choices(),),
                "upscale_mode": (
                    list(base.PASS2_UPSCALE_MODE_CHOICES),
                    {
                        "default": base.PASS2_UPSCALE_MODE_SCALE,
                        "tooltip": "按倍数：720P 可乘 1.5；目标分辨率：直接指定 1920×1088；仅采样修复：不改尺寸，只继续低降噪二采。",
                    },
                ),
                "upscale_scale": (
                    "FLOAT",
                    {"default": 1.5, "min": 1.0, "max": 4.0, "step": 0.05},
                ),
                "target_width": (
                    "INT",
                    {
                        "default": base.PASS2_TARGET_WIDTH,
                        "min": 64,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 8,
                    },
                ),
                "target_height": (
                    "INT",
                    {
                        "default": base.PASS2_TARGET_HEIGHT,
                        "min": 64,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 8,
                    },
                ),
                "upscale_device": (["cuda", "cpu"], {"default": "cuda"}),
                "upscale_precision": (["fp16", "fp32", "bf16"], {"default": "fp16"}),
                "sampler_name": (comfy.samplers.SAMPLER_NAMES, {"default": "er_sde"}),
                "scheduler": (comfy.samplers.SCHEDULER_NAMES, {"default": "beta"}),
                "steps": (
                    "INT",
                    {"default": 4, "min": 1, "max": 10000, "tooltip": "H3 二采步数；推荐 4~6 步。"},
                ),
                "second_pass_denoise": (
                    "FLOAT",
                    {
                        "default": 0.30,
                        "min": 0.05,
                        "max": 0.60,
                        "step": 0.01,
                        "tooltip": "H3 二采重画力度；推荐 0.28~0.35。值越低越保留一采原片，曝光和人物越稳定。",
                    },
                ),
                "second_pass_seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                        "tooltip": "整片固定一个种子；0 = 本次运行随机一次，所有窗口共用该种子。",
                    },
                ),
                "tiled_sampling": (list(base.PASS2_TILED_CHOICES), {"default": base.PASS2_TILED_OFF}),
                "tile_width": (
                    "INT",
                    {
                        "default": base.PASS2_TILE_WIDTH,
                        "min": 32,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 32,
                    },
                ),
                "tile_height": (
                    "INT",
                    {
                        "default": base.PASS2_TILE_HEIGHT,
                        "min": 32,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 32,
                    },
                ),
                "tile_overlap": (
                    "INT",
                    {
                        "default": base.PASS2_TILE_OVERLAP,
                        "min": 32,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 32,
                    },
                ),
                "tile_fade": (
                    "INT",
                    {
                        "default": base.PASS2_TILE_FADE,
                        "min": 0,
                        "max": base.nodes.MAX_RESOLUTION,
                        "step": 32,
                    },
                ),
                "repair_engine": (
                    list(base.PASS2_REPAIR_CHOICES),
                    {
                        "default": base.PASS2_REPAIR_OFF,
                        "tooltip": "在 H3 二采之后做真实画质修复/超分；插件或模型缺失时会明确提示，默认关闭不报错。",
                    },
                ),
                "repair_model": (
                    cls._repair_model_choices(),
                    {"default": base.PASS2_REPAIR_AUTO_MODEL},
                ),
                "repair_scale": (
                    "FLOAT",
                    {
                        "default": base.PASS2_REPAIR_SCALE,
                        "min": 1.0,
                        "max": 4.0,
                        "step": 0.05,
                        "tooltip": "1.0 = 只修画质不继续放大；需要额外超分再设 1.5 / 2.0。",
                    },
                ),
                "repair_batch_size": (
                    "INT",
                    {
                        "default": base.PASS2_REPAIR_BATCH_SIZE,
                        "min": 1,
                        "max": 129,
                        "step": 1,
                    },
                ),
                "repair_temporal_overlap": (
                    "INT",
                    {
                        "default": base.PASS2_REPAIR_TEMPORAL_OVERLAP,
                        "min": 0,
                        "max": 16,
                        "step": 1,
                    },
                ),
                "repair_color_correction": (
                    ["lab", "wavelet", "wavelet_adaptive", "hsv", "adain", "none"],
                    {"default": base.PASS2_REPAIR_COLOR},
                ),
                "repair_quality": (["ULTRA", "HIGH", "MEDIUM", "LOW"], {"default": "ULTRA"}),
                "repair_device": (["cuda", "cpu"], {"default": "cuda"}),
                "repair_blocks_to_swap": (
                    "INT",
                    {"default": 0, "min": 0, "max": 36, "step": 1},
                ),
                "repair_offload_device": (["cpu", "none"], {"default": "cpu"}),
                "repair_vae_tiling": ("BOOLEAN", {"default": True}),
                "lock_source_exposure": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "把每帧最终亮度锁定到未处理成片的对应帧，消除分窗二采造成的忽明忽暗；不改变原音轨。",
                    },
                ),
                "max_window_frames": (
                    "INT",
                    {
                        "default": 362,
                        "min": 39,
                        "max": 1200,
                        "step": 17,
                        "tooltip": "单次 H3 时间窗口最大帧数。362 帧约 15 秒；更长的成片自动分窗。",
                    },
                ),
                "window_overlap_frames": (
                    "INT",
                    {
                        "default": 24,
                        "min": 0,
                        "max": 120,
                        "step": 4,
                        "tooltip": "分窗时前后窗口共享的上下文帧数。共享帧只用于上下文，不会混合到成片。",
                    },
                ),
                "sample_preview": (
                    list(base.RENDER_PREVIEW_CHOICES),
                    {"default": base.RENDER_PREVIEW_OFF},
                ),
                "preview_interval": (
                    "INT",
                    {
                        "default": base.RENDER_PREVIEW_INTERVAL,
                        "min": 1,
                        "max": 1000,
                        "step": 1,
                    },
                ),
                "cleanup_after_run": (
                    list(base.RENDER_CLEANUP_CHOICES),
                    {"default": base.RENDER_CLEANUP_UNLOAD},
                ),
            },
            "optional": {
                "model": (
                    "MODEL",
                    {"tooltip": "可选。建议接加载器的 model 输出；不接时从 h3_bundle 自动加载。"},
                ),
                "sampler": ("SAMPLER",),
                "sigmas": ("SIGMAS",),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # The source is a newly generated final file and may reuse the same name.
        return float("nan")

    @staticmethod
    def _video_source_path(video: Any) -> str | None:
        try:
            source = video.get_stream_source()
        except Exception:
            return None
        if isinstance(source, (str, os.PathLike)):
            path = os.fspath(source)
            if os.path.isfile(path):
                return path
        return None

    @classmethod
    def _source_video_file(
        cls,
        video: Any,
        temp_dir: str,
        fps: float,
    ) -> tuple[str, float, float]:
        """Return a source file plus its active trim window."""
        path = cls._video_source_path(video)
        start, duration = 0.0, 0.0
        if path is not None:
            try:
                start, duration = video.get_active_trim_window()
            except Exception:
                pass
            return path, float(start or 0.0), float(duration or 0.0)

        frames, audio, source_fps = base._video_parts(video)
        frames = base._normalize_video_frames(frames)
        fallback = os.path.join(temp_dir, "source_complete.mp4")
        components = Types.VideoComponents(
            images=frames,
            audio=audio,
            frame_rate=Fraction(str(float(source_fps or fps or h3.FPS))),
        )
        InputImpl.VideoFromComponents(components).save_to(
            fallback,
            format=Types.VideoContainer.MP4,
            codec=Types.VideoCodec.H264,
            crf=14.0,
            preset="medium",
        )
        return fallback, 0.0, 0.0

    @staticmethod
    def _window_plan(
        total_frames: int,
        max_frames: int,
        overlap_frames: int,
    ) -> list[tuple[int, int, int, int]]:
        """Return (decode start, decode end, kept start, kept end) per window."""
        total = max(1, int(total_frames))
        window = max(39, int(max_frames or 362))
        if total <= window:
            return [(0, total, 0, total)]

        overlap = max(0, min(int(overlap_frames or 0), max(0, window - 39)))
        step = max(1, window - overlap)
        starts = [0]
        while starts[-1] + window < total:
            next_start = starts[-1] + step
            if next_start + window >= total:
                next_start = max(0, total - window)
            if next_start <= starts[-1]:
                break
            starts.append(next_start)
        ends = [min(total, start + window) for start in starts]

        kept_starts = [0]
        kept_ends: list[int] = []
        for index in range(len(starts)):
            if index == len(starts) - 1:
                kept_ends.append(total)
            else:
                boundary = (ends[index] + starts[index + 1]) // 2
                kept_ends.append(max(kept_starts[-1], boundary))
            if index + 1 < len(starts):
                kept_starts.append(kept_ends[-1])
        return [
            (starts[index], ends[index], kept_starts[index], kept_ends[index])
            for index in range(len(starts))
        ]

    @classmethod
    def _decode_window(
        cls,
        video: Any,
        start: int,
        count: int,
        fps: float,
    ) -> torch.Tensor:
        trimmed = None
        if callable(getattr(video, "as_trimmed", None)):
            trimmed = video.as_trimmed(
                start_time=float(start) / max(1e-6, fps),
                duration=float(count) / max(1e-6, fps),
                strict_duration=False,
            )
        if trimmed is None:
            frames, _audio, _source_fps = base._video_parts(video)
            frames = base._normalize_video_frames(frames)
            return frames[start:start + count].contiguous()

        frames, _audio, source_fps = base._video_parts(trimmed)
        frames = base._normalize_video_frames(frames)
        frames = base._resample_video_frames(frames, float(source_fps or fps))
        return frames[:count].contiguous()

    @staticmethod
    def _write_video_only(frames: torch.Tensor, fps: float, path: str) -> None:
        frames = (
            frames[..., :3]
            .detach()
            .to(device="cpu", dtype=torch.float32)
            .clamp(0.0, 1.0)
            .contiguous()
        )
        components = Types.VideoComponents(
            images=frames,
            audio=None,
            frame_rate=Fraction(str(float(fps or h3.FPS))),
        )
        InputImpl.VideoFromComponents(components).save_to(
            path,
            format=Types.VideoContainer.MP4,
            codec=Types.VideoCodec.H264,
            crf=14.0,
            preset="medium",
        )

    @staticmethod
    def _run_ffmpeg(args: list[str]) -> None:
        process = subprocess.run(
            [
                base._segment_ffmpeg_path(),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 0:
            detail = (process.stderr or process.stdout or "").strip()
            raise RuntimeError(f"FFmpeg 最终封装失败：{detail[-2000:]}")

    @classmethod
    def _concat_video_only(cls, paths: list[str], output_path: str, temp_dir: str) -> str:
        if len(paths) == 1:
            return paths[0]
        list_path = os.path.join(temp_dir, "concat.txt")
        with open(list_path, "w", encoding="utf-8") as handle:
            for path in paths:
                escaped = os.path.abspath(path).replace("'", "'\\''")
                handle.write(f"file '{escaped}'\n")
        cls._run_ffmpeg(
            [
                "-fflags",
                "+genpts",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                output_path,
            ]
        )
        return output_path

    @classmethod
    def _mux_source_audio(
        cls,
        *,
        source_path: str,
        source_start: float,
        source_duration: float,
        processed_path: str,
        output_path: str,
        output_duration: float = 0.0,
    ) -> None:
        args = ["-i", processed_path]
        if source_start > 1e-6:
            args.extend(["-ss", f"{source_start:.9f}"])
        if source_duration > 1e-6:
            args.extend(["-t", f"{source_duration:.9f}"])
        args.extend(["-i", source_path])
        args.extend(
            [
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-map_metadata",
                "1",
                "-movflags",
                "+faststart",
                *(["-t", f"{output_duration:.9f}"] if output_duration > 1e-6 else []),
                output_path,
            ]
        )
        cls._run_ffmpeg(args)

    @staticmethod
    def _lock_exposure(frames: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        """Match each output frame's luminance gain to the untouched source frame."""
        if not isinstance(frames, torch.Tensor) or not isinstance(reference, torch.Tensor):
            return frames
        count = min(int(frames.shape[0]), int(reference.shape[0]))
        if count <= 0:
            return frames

        output = frames[:count].detach().to(device="cpu", dtype=torch.float32)
        ref = reference[:count].detach().to(device="cpu", dtype=torch.float32)
        if tuple(output.shape[1:3]) != tuple(ref.shape[1:3]):
            ref = h3._resize(
                ref,
                int(output.shape[2]),
                int(output.shape[1]),
                "disabled",
            ).to(device="cpu")
        weights = torch.tensor(
            [0.2126, 0.7152, 0.0722],
            dtype=torch.float32,
        ).view(1, 1, 1, 3)
        out_luma = (output[..., :3] * weights).sum(dim=-1, keepdim=True).mean(
            dim=(1, 2),
            keepdim=True,
        )
        ref_luma = (ref[..., :3] * weights).sum(dim=-1, keepdim=True).mean(
            dim=(1, 2),
            keepdim=True,
        )
        gain = (ref_luma / out_luma.clamp_min(1e-4)).clamp(0.85, 1.18)
        corrected = (output * gain).clamp(0.0, 1.0).contiguous()
        if count < int(frames.shape[0]):
            corrected = torch.cat(
                (
                    corrected,
                    frames[count:].to(device="cpu", dtype=torch.float32),
                ),
                dim=0,
            )
        return corrected

    @classmethod
    def _apply_repair(
        cls,
        frames: torch.Tensor,
        *,
        engine: str,
        model_name: str,
        scale: float,
        seed: int,
        batch_size: int,
        temporal_overlap: int,
        color_correction: str,
        quality: str,
        device: str,
        blocks_to_swap: int,
        offload_device: str,
        vae_tiling: bool,
    ) -> torch.Tensor:
        if engine == base.PASS2_REPAIR_SEEDVR2:
            resolved = base.MiniMaxH3EasyRenderPass2._resolve_repair_model(engine, model_name)
            return base.MiniMaxH3EasyRenderPass2._seedvr2_repair_frames(
                frames,
                model_name=resolved,
                scale=scale,
                seed=seed,
                batch_size=batch_size,
                temporal_overlap=temporal_overlap,
                color_correction=color_correction,
                device=device,
                blocks_to_swap=blocks_to_swap,
                offload_device=offload_device,
                vae_tiling=vae_tiling,
            )
        if engine == base.PASS2_REPAIR_RTX:
            return base.MiniMaxH3EasyRenderPass2._rtx_vsr_repair_frames(
                frames,
                scale=scale,
                quality=quality,
            )
        if engine == base.PASS2_REPAIR_VOSR2:
            resolved = base.MiniMaxH3EasyRenderPass2._resolve_repair_model(engine, model_name)
            return base.MiniMaxH3EasyRenderPass2._vosr2_repair_frames(
                frames,
                model_name=resolved,
                scale=scale,
                seed=seed,
                color_correction=color_correction,
            )
        raise ValueError(f"未知的成片修复引擎：{engine}")

    @classmethod
    def _h3_second_pass(
        cls,
        frames: torch.Tensor,
        *,
        bundle: base.MiniMaxH3Bundle,
        model: Any,
        latent_upscale_model: str,
        upscale_mode: str,
        upscale_scale: float,
        target_width: int,
        target_height: int,
        upscale_device: str,
        upscale_precision: str,
        sampler_name: str,
        scheduler: str,
        steps: int,
        denoise: float,
        seed: int,
        tiled_sampling: str,
        tile_width: int,
        tile_height: int,
        tile_overlap: int,
        tile_fade: int,
        sample_preview: str,
        preview_interval: int,
        sampler: Any,
        sigmas: Any,
    ) -> torch.Tensor:
        if not isinstance(frames, torch.Tensor) or frames.ndim != 4 or frames.shape[0] < 1:
            raise ValueError("最终成片二采需要有效的 VIDEO 帧")

        original_count = int(frames.shape[0])
        aligned_count = h3.align_frame_count(max(5, original_count))
        source_frames = base._fit_video_frame_count(frames, aligned_count)
        source_h = int(source_frames.shape[1])
        source_w = int(source_frames.shape[2])
        width = base._align_canvas_dimension(source_w)
        height = base._align_canvas_dimension(source_h)
        source_grid = h3._resize(source_frames, width, height, "disabled").contiguous()

        video_latent = bundle.video_vae.encode(source_grid)
        if isinstance(video_latent, Mapping):
            video_latent = video_latent.get("samples")
        if not isinstance(video_latent, torch.Tensor) or video_latent.ndim != 5 or video_latent.shape[1] != 24:
            raise ValueError("成片二采无法把最终视频编码成 24 通道 H3 video latent")

        first_latent, _frame_count = h3._empty_av_latent(width, height, aligned_count)
        _empty_video, empty_audio = base._segment_latent_streams(first_latent)
        first_payload = base._segment_pack_latent(
            video_latent.detach().to(device="cpu").contiguous(),
            empty_audio,
        )
        upscaled_video, _audio_latent = base.MiniMaxH3EasyRenderPass2._upscale_video_latent(
            first_payload,
            latent_upscale_model,
            upscale_scale,
            upscale_device,
            upscale_precision,
            True,
            model,
            upscale_mode=upscale_mode,
            target_width=target_width,
            target_height=target_height,
        )

        target_w = int(upscaled_video.shape[-1]) * 16
        target_h = int(upscaled_video.shape[-2]) * 16
        second_conditioning, target_base, _sources = base._empty_image_conditioning(
            bundle,
            "",
            target_w,
            target_h,
            aligned_count,
            first_frame=source_grid[:1],
            last_frame=source_grid[-1:],
        )
        _target_video, target_audio = base._segment_latent_streams(target_base)
        second_input = base._lock_audio_latent(
            base._segment_pack_latent(upscaled_video, target_audio),
            target_audio,
        )

        from aicg3d_h3easy.aicg3d_sampler import AICG3DSamplerAdvanced
        from aicg3d_h3easy.render_progress import (
            SAMPLE_PREVIEW_ENABLED,
            STAGE_SAMPLE_SECOND,
            RenderPreviewEncoder,
            RenderProgressReporter,
        )

        reporter = RenderProgressReporter()
        want_preview = (
            SAMPLE_PREVIEW_ENABLED
            or str(sample_preview or "").strip() == base.RENDER_PREVIEW_ON
        )
        preview = RenderPreviewEncoder(model) if want_preview else None
        on_preview = None
        if preview is not None:
            should_push = base._preview_step_filter(preview_interval)

            def preview_callback(x0, step=None, total=None, *_info):
                if not should_push(step, total):
                    return None
                return reporter.update_preview(preview.decode(x0))

            on_preview = preview_callback

        seed_value = int(seed) & 0xFFFFFFFFFFFFFFFF
        if seed_value == 0:
            seed_value = int(time.time_ns()) & 0xFFFFFFFFFFFFFFFF
        sampling_steps = base._external_sampling_steps(sigmas, steps)
        reporter.begin_stage(STAGE_SAMPLE_SECOND, 0.0, 0.98, sampling_steps)
        if str(tiled_sampling or "").strip() == base.PASS2_TILED_ON:
            sampled = base.MiniMaxH3EasyRenderPass2._tiled_second_pass(
                model,
                second_conditioning,
                second_input,
                upscaled_video,
                sampler_name,
                scheduler,
                steps,
                denoise,
                seed_value,
                tile_width,
                tile_height,
                tile_overlap,
                tile_fade,
                base._StageAbsoluteProgress(reporter),
                on_preview,
                sampler=sampler,
                sigmas=sigmas,
            )
        else:
            sampled, = AICG3DSamplerAdvanced().sample(
                model,
                second_conditioning,
                second_input,
                seed_value,
                sampler_name,
                scheduler,
                steps,
                denoise,
                sampler=sampler,
                sigmas=sigmas,
                on_step=reporter.update_stage,
                on_preview=on_preview,
            )

        reporter.begin_decode()
        decoded = base.nodes.VAEDecode().decode(bundle.video_vae, sampled)[0]
        if not isinstance(decoded, torch.Tensor) or decoded.ndim != 4 or decoded.shape[-1] < 3:
            raise RuntimeError("成片二采没有解码出有效 RGB 帧")
        decoded = decoded[..., :3].detach().to(device="cpu", dtype=torch.float32).contiguous()
        decoded = base._fit_video_frame_count(decoded, original_count)
        reporter.finish(True)
        return decoded

    @classmethod
    def upscale_final_video(
        cls,
        video,
        h3_bundle,
        filename_prefix="video/MiniMax_H3_Final_HD",
        second_pass=True,
        latent_upscale_model="",
        upscale_mode=base.PASS2_UPSCALE_MODE_SCALE,
        upscale_scale=1.5,
        target_width=base.PASS2_TARGET_WIDTH,
        target_height=base.PASS2_TARGET_HEIGHT,
        upscale_device="cuda",
        upscale_precision="fp16",
        sampler_name="er_sde",
        scheduler="beta",
        steps=4,
        second_pass_denoise=0.30,
        second_pass_seed=0,
        tiled_sampling=base.PASS2_TILED_OFF,
        tile_width=base.PASS2_TILE_WIDTH,
        tile_height=base.PASS2_TILE_HEIGHT,
        tile_overlap=base.PASS2_TILE_OVERLAP,
        tile_fade=base.PASS2_TILE_FADE,
        repair_engine=base.PASS2_REPAIR_OFF,
        repair_model=base.PASS2_REPAIR_AUTO_MODEL,
        repair_scale=base.PASS2_REPAIR_SCALE,
        repair_batch_size=base.PASS2_REPAIR_BATCH_SIZE,
        repair_temporal_overlap=base.PASS2_REPAIR_TEMPORAL_OVERLAP,
        repair_color_correction=base.PASS2_REPAIR_COLOR,
        repair_quality="ULTRA",
        repair_device="cuda",
        repair_blocks_to_swap=0,
        repair_offload_device="cpu",
        repair_vae_tiling=True,
        lock_source_exposure=True,
        max_window_frames=362,
        window_overlap_frames=24,
        sample_preview=base.RENDER_PREVIEW_OFF,
        preview_interval=base.RENDER_PREVIEW_INTERVAL,
        cleanup_after_run=base.RENDER_CLEANUP_UNLOAD,
        model=None,
        sampler=None,
        sigmas=None,
    ):
        if not isinstance(h3_bundle, base.MiniMaxH3Bundle):
            raise ValueError("请把 MiniMax H3 Aicg 加载器的 h3_bundle 接到成片高清节点")
        if not hasattr(video, "get_components"):
            raise ValueError("成片高清节点需要连接最终合成的 VIDEO")

        use_second_pass = bool(second_pass)
        repair_engine = str(repair_engine or base.PASS2_REPAIR_OFF).strip()
        repair_active = repair_engine != base.PASS2_REPAIR_OFF
        if repair_engine not in base.PASS2_REPAIR_CHOICES:
            raise ValueError(f"未知的成片修复引擎：{repair_engine}")
        if not use_second_pass and not repair_active:
            raise ValueError("H3 二次采样和超分/修复都没有开启，成片不会有任何处理。")
        if use_second_pass and (
            not latent_upscale_model or str(latent_upscale_model).startswith("(")
        ):
            raise ValueError("请选择 H3 Latent 3D 放大器模型，或关闭 H3 二次采样只使用超分修复。")

        fps = float(video.get_frame_rate() or h3.FPS)
        total_frames = int(video.get_frame_count())
        if total_frames <= 0:
            raise ValueError("最终合成视频没有可用帧")
        plans = cls._window_plan(
            total_frames,
            int(max_window_frames),
            int(window_overlap_frames),
        )
        temp_dir = tempfile.mkdtemp(
            prefix="aicg3d_final_hd_",
            dir=folder_paths.get_temp_directory(),
        )
        window_paths: list[str] = []
        processed_total = 0
        output_width = 0
        output_height = 0
        h3_model = model
        done = False
        try:
            source_path, source_start, source_duration = cls._source_video_file(
                video,
                temp_dir,
                fps,
            )
            if use_second_pass and h3_model is None:
                h3_model = h3_bundle.model_for("fl2va")

            for index, (decode_start, decode_end, kept_start, kept_end) in enumerate(
                plans,
                start=1,
            ):
                decode_count = decode_end - decode_start
                source_frames = cls._decode_window(
                    video,
                    decode_start,
                    decode_count,
                    fps,
                )
                if source_frames.shape[0] <= 0:
                    raise RuntimeError(f"成片第 {index} 个时间窗口没有解出画面")

                working = source_frames
                if use_second_pass:
                    working = cls._h3_second_pass(
                        working,
                        bundle=h3_bundle,
                        model=h3_model,
                        latent_upscale_model=latent_upscale_model,
                        upscale_mode=upscale_mode,
                        upscale_scale=float(upscale_scale),
                        target_width=int(target_width),
                        target_height=int(target_height),
                        upscale_device=upscale_device,
                        upscale_precision=upscale_precision,
                        sampler_name=sampler_name,
                        scheduler=scheduler,
                        steps=int(steps),
                        denoise=float(second_pass_denoise),
                        seed=int(second_pass_seed),
                        tiled_sampling=tiled_sampling,
                        tile_width=int(tile_width),
                        tile_height=int(tile_height),
                        tile_overlap=int(tile_overlap),
                        tile_fade=int(tile_fade),
                        sample_preview=sample_preview,
                        preview_interval=int(preview_interval),
                        sampler=sampler,
                        sigmas=sigmas,
                    )
                if repair_active:
                    working = cls._apply_repair(
                        working,
                        engine=repair_engine,
                        model_name=repair_model,
                        scale=float(repair_scale),
                        seed=int(second_pass_seed),
                        batch_size=int(repair_batch_size),
                        temporal_overlap=int(repair_temporal_overlap),
                        color_correction=repair_color_correction,
                        quality=repair_quality,
                        device=repair_device,
                        blocks_to_swap=int(repair_blocks_to_swap),
                        offload_device=repair_offload_device,
                        vae_tiling=bool(repair_vae_tiling),
                    )

                working = (
                    working[..., :3]
                    .detach()
                    .to(device="cpu", dtype=torch.float32)
                    .clamp(0.0, 1.0)
                )
                working = base._fit_video_frame_count(
                    working,
                    int(source_frames.shape[0]),
                )
                if bool(lock_source_exposure):
                    working = cls._lock_exposure(working, source_frames)

                local_start = max(0, int(kept_start) - int(decode_start))
                local_end = min(
                    int(working.shape[0]),
                    int(kept_end) - int(decode_start),
                )
                if local_end <= local_start:
                    raise RuntimeError(f"成片第 {index} 个时间窗口的有效输出为空")
                kept = working[local_start:local_end].contiguous()
                processed_total += int(kept.shape[0])
                output_height, output_width = int(kept.shape[1]), int(kept.shape[2])
                window_path = os.path.join(temp_dir, f"window_{index:04d}.mp4")
                cls._write_video_only(kept, fps, window_path)
                window_paths.append(window_path)
                print(
                    f"[AICG3D Final HD] 窗口 {index}/{len(plans)}："
                    f"输入 {source_frames.shape[0]} 帧，保留 {kept.shape[0]} 帧，"
                    f"输出 {output_width}x{output_height}"
                )

            if processed_total != total_frames:
                raise RuntimeError(
                    f"成片高清分窗帧数不一致：输入 {total_frames} 帧，输出 {processed_total} 帧。"
                    "请检查源视频帧率或时间戳。"
                )

            concat_path = os.path.join(temp_dir, "processed_video.mp4")
            concat_path = cls._concat_video_only(window_paths, concat_path, temp_dir)
            (
                full_output_folder,
                name,
                counter,
                subfolder,
                _prefix,
            ) = folder_paths.get_save_image_path(
                str(filename_prefix or "video/MiniMax_H3_Final_HD"),
                folder_paths.get_output_directory(),
                output_width,
                output_height,
            )
            os.makedirs(full_output_folder, exist_ok=True)
            file = f"{name}_{counter:05}_.mp4"
            target_path = os.path.join(full_output_folder, file)
            cls._mux_source_audio(
                source_path=source_path,
                source_start=source_start,
                source_duration=source_duration,
                processed_path=concat_path,
                output_path=target_path,
                output_duration=float(total_frames) / max(1e-6, fps),
            )
            report = (
                f"成片高清完成：{total_frames} 帧，{len(plans)} 个时间窗口；"
                f"H3 二采 {'开' if use_second_pass else '关'}；"
                f"修复引擎 {repair_engine}；"
                f"源曝光锁定 {'开' if bool(lock_source_exposure) else '关'}；"
                "音频原轨直接封装。"
            )
            print(
                f"[AICG3D Final HD] {report} -> "
                f"output/{subfolder + '/' if subfolder else ''}{file}"
            )
            done = True
            output_video = InputImpl.VideoFromFile(target_path)
            ui = {
                "images": [
                    {
                        "filename": file,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ],
                "animated": (True,),
            }
            return {
                "ui": ui,
                "result": (
                    output_video,
                    os.path.join(subfolder, file),
                    report,
                ),
            }
        finally:
            if not done:
                print(
                    "[AICG3D Final HD] 处理失败，临时文件仍保留用于排查："
                    + temp_dir
                )
            else:
                base._segment_cleanup_temp_dir(temp_dir)
            base._release_render_resources(cleanup_after_run)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyFinalHighResUpscale": MiniMaxH3EasyFinalHighResUpscale,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyFinalHighResUpscale": "AICG3D H3 成片高清二采放大",
}
