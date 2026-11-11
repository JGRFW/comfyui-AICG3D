# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Single-line handoff from final sequence assembly to final HD processing.

The legacy final-upscale node keeps its ``video + h3_bundle + model`` inputs.
The wrappers in this module add a packed final-sequence output and a matching
single-input final-upscale node. Old workflows remain loadable through the
legacy node.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aicg3d_h3easy import final_upscale
from aicg3d_h3easy import nodes as base


FINAL_SEQUENCE_TYPE = "MINIMAX_H3_FINAL_SEQUENCE"


@dataclass(frozen=True)
class MiniMaxH3FinalSequence:
    """The assembled film plus the exact H3 state used to create it."""

    video: Any
    h3_bundle: base.MiniMaxH3Bundle
    model: Any = None
    sampler: Any = None
    sigmas: Any = None
    saved_file: str = ""
    seam_report: str = ""


def _is_cache_only(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


class MiniMaxH3EasyFinalSequenceCombine(base.MiniMaxH3EasySequenceCombine):
    """Assemble a sequence chain and expose its complete state as one packet."""

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", FINAL_SEQUENCE_TYPE)
    RETURN_NAMES = ("video", "saved_file", "seam_report", "final_sequence")
    DESCRIPTION = (
        "把整条「视频段落」链拼成成片，并额外输出一条「成片数据」；"
        "这条数据同时携带成片、H3 模型组合和本次采样参数，"
        "可直接接到单线版「成片高清二采放大」。原有视频、保存路径和接缝报告输出保持不变。"
    )

    @classmethod
    def _resolve_chain_for_packet(
        cls,
        *,
        final_segment: Any,
        cache_only: Any,
        cache_scope: str,
        cache_chain_key: str,
        cache_segment_count: int,
        extra_pnginfo: Any,
    ) -> list[base.MiniMaxH3SequenceSegment]:
        if _is_cache_only(cache_only):
            scope = base._sequence_runtime_scope(extra_pnginfo, cache_scope)
            chain_key = str(cache_chain_key or "").strip()
            if not chain_key:
                raise ValueError("抽卡缓存合成缺少段落链标识，请从连接好的最终合成节点重新运行")
            expected_count = int(cache_segment_count or 0)
            chain = base._sequence_cache_read_chain(scope, chain_key, expected_count)
            if expected_count > 0 and len(chain) != expected_count:
                raise ValueError(
                    f"抽卡缓存只找到 {len(chain)} 段，当前工作流需要 {expected_count} 段完整结果；"
                    "请先完整运行一次所有段落，再进行单段抽卡和最终合成。"
                )
            return chain
        if final_segment is None:
            raise ValueError("最终合成需要连接最后一段的 segment，或使用抽卡缓存合成模式")
        return base._sequence_collect_chain(final_segment)

    @classmethod
    def combine(
        cls,
        final_segment=None,
        filename_prefix=base.SEQUENCE_DEFAULT_FILENAME_PREFIX,
        cache_only=False,
        cache_scope="",
        cache_chain_key="",
        cache_segment_count=0,
        extra_pnginfo=None,
        **kwargs,
    ):
        chain = cls._resolve_chain_for_packet(
            final_segment=final_segment,
            cache_only=cache_only,
            cache_scope=cache_scope,
            cache_chain_key=cache_chain_key,
            cache_segment_count=cache_segment_count,
            extra_pnginfo=extra_pnginfo,
        )
        if not chain:
            raise ValueError("最终合成没有找到可用的视频段落")

        config = chain[0].config
        if not isinstance(config.bundle, base.MiniMaxH3Bundle):
            raise ValueError("「视频段落」链里没有可用的 MiniMax H3 模型组合")

        result = super().combine(
            final_segment=final_segment,
            filename_prefix=filename_prefix,
            cache_only=cache_only,
            cache_scope=cache_scope,
            cache_chain_key=cache_chain_key,
            cache_segment_count=cache_segment_count,
            extra_pnginfo=extra_pnginfo,
            **kwargs,
        )
        video, saved_file, seam_report = result["result"][:3]
        if video is None:
            raise ValueError("最终合成没有生成可交给成片高清节点的视频")

        final_sequence = MiniMaxH3FinalSequence(
            video=video,
            h3_bundle=config.bundle,
            model=getattr(config, "model", None),
            sampler=getattr(config, "sampler", None),
            sigmas=getattr(config, "sigmas", None),
            saved_file=str(saved_file or ""),
            seam_report=str(seam_report or ""),
        )
        result["result"] = (video, saved_file, seam_report, final_sequence)
        return result


class MiniMaxH3EasyFinalHighResUpscalePacked(
    final_upscale.MiniMaxH3EasyFinalHighResUpscale
):
    """Final HD processing with one linked input and compact frontend controls."""

    DESCRIPTION = (
        "接「最终合成」的「成片数据」一根线即可。H3 模型组合、采样器和调度器随成片数据传入；"
        "整片二采、画质修复、超分和原始曝光锁定都在这个节点内完成，不会回到分段采样。"
        "可选二采精修 LoRA 只作用于整片二采模型；高级参数默认折叠。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        parent = final_upscale.MiniMaxH3EasyFinalHighResUpscale.INPUT_TYPES()
        parent_required = dict(parent["required"])
        parent_required.pop("video", None)
        parent_required.pop("h3_bundle", None)

        filename_prefix = parent_required.pop("filename_prefix")
        second_pass = parent_required.pop("second_pass")

        required = {
            "filename_prefix": filename_prefix,
            "second_pass": second_pass,
            "refiner_lora": (
                base._lora_choices(),
                {
                    "default": "none",
                    "tooltip": (
                        "可选。只给整片 H3 二采模型叠加一个精修 LoRA，固定强度 1.0；"
                        "关闭二采时不会加载或应用。选择「无」表示不叠加。"
                    ),
                },
            ),
            "show_advanced_settings": (
                "BOOLEAN",
                {
                    "default": False,
                    "tooltip": "关闭时只显示常用二采参数；打开后才显示设备、分块、修复、预览和清理等高级设置。",
                },
            ),
            **parent_required,
        }
        return {
            "required": {
                "final_sequence": (
                    FINAL_SEQUENCE_TYPE,
                    {"tooltip": "接「最终合成」的「成片数据」输出。"},
                ),
                **required,
            }
        }

    def upscale_final_video(
        self,
        final_sequence,
        refiner_lora="none",
        show_advanced_settings=False,
        **kwargs,
    ):
        del show_advanced_settings  # Frontend-only disclosure control.
        if final_sequence is None:
            raise ValueError("成片数据为空，请连接「最终合成」的「成片数据」输出")
        if not isinstance(final_sequence, MiniMaxH3FinalSequence):
            raise ValueError("请把「最终合成」的「成片数据」接到单线版成片高清节点")
        if final_sequence.video is None or not hasattr(final_sequence.video, "get_components"):
            raise ValueError("成片数据里没有可用的最终 VIDEO，请重新运行最终合成")
        if not isinstance(final_sequence.h3_bundle, base.MiniMaxH3Bundle):
            raise ValueError("成片数据里没有可用的 MiniMax H3 模型组合，请重新运行最终合成")

        model = final_sequence.model
        use_second_pass = bool(kwargs.get("second_pass", True))
        if use_second_pass:
            if model is None:
                model = final_sequence.h3_bundle.model_for("fl2va")
            if not base._is_none_model(refiner_lora):
                model = base._apply_secondary_refiner_lora(model, refiner_lora)

        return super().upscale_final_video(
            video=final_sequence.video,
            h3_bundle=final_sequence.h3_bundle,
            model=model,
            sampler=final_sequence.sampler,
            sigmas=final_sequence.sigmas,
            **kwargs,
        )


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyFinalSequenceCombine": MiniMaxH3EasyFinalSequenceCombine,
    "MiniMaxH3EasyFinalHighResUpscalePacked": MiniMaxH3EasyFinalHighResUpscalePacked,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyFinalSequenceCombine": "AICG3D H3 最终合成 · 单线成片",
    "MiniMaxH3EasyFinalHighResUpscalePacked": "AICG3D H3 成片高清二采放大",
}
