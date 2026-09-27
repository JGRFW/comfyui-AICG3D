# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
"""AICG3D H3 加速设置：注意力加速 + 运动缓存（MotionCache）。

这里补上 MiniMax H3 流水线上最常用的两类加速开关：

* 注意力加速：直接复用 ComfyUI 的注意力后端注册表（SageAttention / SageAttention3 /
  FlashAttention / Comfy 厨房 INT8 / xFormers / PyTorch SDPA / Sub-Quadratic / Split），
  通过 ``ModelPatcher.set_model_optimized_attention`` 打到模型上，不碰采样器。
* 运动缓存（MotionCache）：TeaCache 式的跳步复用。按"复用阈值 / 运动强度 / 预热步数 /
  最大连跳 / 起始% / 结束% / 采样间隔"判断某一步能不能直接复用上一步的残差，
  通过 ``WrappersMP.DIFFUSION_MODEL`` 包装模型前向实现。

两者都统一走 :func:`apply_acceleration`，配置挂在 ``MINIMAX_H3_BUNDLE.accel`` 上，
所以"加载器里内置一段加速设置"和"单独一个加速节点串在加载器后面"共用同一份实现。
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

import torch

import comfy.ldm.modules.attention as attention_lib
import comfy.patcher_extension


LOG_PREFIX = "[MiniMax H3 Aicg 加速]"

# 运动缓存挂在 transformer_options 里的键名。
MOTION_CACHE_KEY = "aicg3d_h3_motion_cache"

ATTENTION_AUTO = "自动（Sage 优先）"
ATTENTION_OFF = "关闭"

# 注意力后端的 (注册表键, 界面显示名)。顺序即"自动"之外的界面顺序。
_ATTENTION_BACKENDS: tuple[tuple[str, str], ...] = (
    ("sage", "SageAttention"),
    ("sage3", "SageAttention3（Blackwell）"),
    ("flash", "FlashAttention"),
    ("comfy_kitchen_int8", "Comfy Kitchen INT8"),
    ("xformers", "xFormers"),
    ("pytorch", "PyTorch SDPA"),
    ("sub_quad", "Sub-Quadratic"),
    ("split", "Split"),
)

# "自动（Sage 优先）"按这个顺序挑。
_AUTO_PRIORITY: tuple[str, ...] = ("sage", "sage3")


def _log(message: str) -> None:
    logging.info("%s %s", LOG_PREFIX, message)


def _warn(message: str) -> None:
    logging.warning("%s %s", LOG_PREFIX, message)


def _backend_present(key: str) -> bool:
    """后端是否已在 ComfyUI 里注册（等价于依赖装好且可用）。"""
    try:
        return attention_lib.get_attention_function(key, None) is not None
    except Exception:
        return False


def available_attention_backends() -> list[tuple[str, str]]:
    """返回当前环境真正可用的注意力后端 (键, 显示名)。"""
    return [(key, label) for key, label in _ATTENTION_BACKENDS if _backend_present(key)]


def attention_choices() -> list[str]:
    return [ATTENTION_AUTO, ATTENTION_OFF] + [label for _, label in available_attention_backends()]


def _label_to_backend(choice: str) -> str | None:
    for key, label in _ATTENTION_BACKENDS:
        if choice == label:
            return key
    return None


def resolve_attention_backend(choice: str) -> tuple[str | None, str]:
    """把界面选项翻译成 (后端键, 说明)。返回 None 表示"不改动"。"""
    choice = (choice or "").strip()
    if choice in ("", ATTENTION_OFF, "关", "False", "false"):
        return None, "注意力加速已关闭"
    backend = _label_to_backend(choice)
    if backend is not None:
        if _backend_present(backend):
            return backend, f"注意力后端 → {choice}"
        return None, f"{choice} 当前不可用（依赖没装或后端没注册），保持 ComfyUI 默认后端"
    # 自动模式：Sage 优先，没有就用 ComfyUI 当前后端。
    for key in _AUTO_PRIORITY:
        if _backend_present(key):
            label = dict(_ATTENTION_BACKENDS)[key]
            return key, f"注意力后端 → {label}（自动选择）"
    return None, "未检测到 SageAttention，保持 ComfyUI 默认注意力后端"


# 已知的第三方 H3 加速插件：装了就提示用户可以直接串在链路里。
_EXTERNAL_ACCELERATORS: tuple[tuple[str, str], ...] = (
    ("blockcache", "MiniMax H3 Block Cache（块缓存）"),
    ("sol-attn", "Sol-Attention（长序列稀疏注意力）"),
    ("solattn", "Sol-Attention（长序列稀疏注意力）"),
    ("selflift", "SelfLift（自举放大加速）"),
    ("pdd-acc", "PDD-Acc（参数下降加速）"),
    ("spectrum", "Spectrum MiniMax H3"),
    ("kjnodes", "KJNodes（含 H3 显存友好 Sage 补丁）"),
    ("reservedvram", "ReservedVRAM（预留显存）"),
)


def detect_external_accelerators() -> list[str]:
    """扫描 custom_nodes 目录，列出本机已安装的第三方加速插件。"""
    found: list[str] = []
    try:
        import os
        import folder_paths

        roots = folder_paths.get_folder_paths("custom_nodes") or []
    except Exception:
        return found
    for root in roots:
        try:
            names = os.listdir(root)
        except Exception:
            continue
        for name in names:
            low = name.lower()
            for token, label in _EXTERNAL_ACCELERATORS:
                if token in low and label not in found:
                    found.append(label)
    return found


# --------------------------------------------------------------------------------------
# 配置对象
# --------------------------------------------------------------------------------------


@dataclass
class AccelConfig:
    """一次运行要用的加速配置。字段名与界面控件一一对应。"""

    attention: str = ATTENTION_AUTO
    motion_cache: bool = False
    mc_reuse_threshold: float = 0.08
    mc_motion_strength: float = 0.1
    mc_warmup_steps: int = 4
    mc_max_skip: int = 2
    mc_start_percent: float = 0.15
    mc_end_percent: float = 0.95
    mc_metric_stride: int = 8
    # 同一个 (模型对象, 配置) 只打一次补丁，避免每步重复 clone。
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def enabled(self) -> bool:
        return bool(self.motion_cache) or (self.attention or "").strip() not in ("", ATTENTION_OFF)

    def signature(self) -> tuple:
        return (
            self.attention,
            bool(self.motion_cache),
            round(float(self.mc_reuse_threshold), 5),
            round(float(self.mc_motion_strength), 5),
            int(self.mc_warmup_steps),
            int(self.mc_max_skip),
            round(float(self.mc_start_percent), 5),
            round(float(self.mc_end_percent), 5),
            int(self.mc_metric_stride),
        )

    def describe(self) -> str:
        if not self.enabled:
            return "加速：全部关闭"
        parts = []
        if (self.attention or "").strip() not in ("", ATTENTION_OFF):
            parts.append(f"注意力={self.attention}")
        if self.motion_cache:
            parts.append(
                "运动缓存(阈值%.3f/强度%.2f/预热%d/连跳%d/%.0f%%-%.0f%%/间隔%d)"
                % (
                    self.mc_reuse_threshold,
                    self.mc_motion_strength,
                    self.mc_warmup_steps,
                    self.mc_max_skip,
                    self.mc_start_percent * 100.0,
                    self.mc_end_percent * 100.0,
                    self.mc_metric_stride,
                )
            )
        return "加速：" + "，".join(parts)


# 界面控件名（与参考图一致）。顺序 = 界面顺序。
ACCEL_WIDGET_NAMES: tuple[str, ...] = (
    "注意力加速(Sage)",
    "运动缓存(MotionCache)",
    "MC复用阈值",
    "MC运动强度",
    "MC预热步数",
    "MC最大连跳",
    "MC起始%",
    "MC结束%",
    "MC采样间隔",
)


def accel_widget_input_types() -> dict[str, tuple]:
    """返回可以合并进节点 INPUT_TYPES["required"] 的加速控件定义。"""
    return {
        ACCEL_WIDGET_NAMES[0]: (
            attention_choices(),
            {
                "default": ATTENTION_AUTO,
                "tooltip": (
                    "注意力加速。自动=SageAttention 优先，没装就保持 ComfyUI 当前后端；"
                    "也可以手动指定 SageAttention3 / FlashAttention / 厨房 INT8 / xFormers 等。"
                ),
            },
        ),
        ACCEL_WIDGET_NAMES[1]: (
            "BOOLEAN",
            {
                "default": False,
                "tooltip": "运动缓存（MotionCache）：跳步复用上一步结果，明显提速；调大越激进、越容易掉细节。",
            },
        ),
        ACCEL_WIDGET_NAMES[2]: (
            "FLOAT",
            {"default": 0.08, "min": 0.0, "max": 1.0, "step": 0.005, "tooltip": "复用阈值：累积变化小于它才跳步，越大越激进。"},
        ),
        ACCEL_WIDGET_NAMES[3]: (
            "FLOAT",
            {"default": 0.1, "min": 0.0, "max": 4.0, "step": 0.01, "tooltip": "运动强度：画面动得越厉害越容易放弃复用，调大更保守。"},
        ),
        ACCEL_WIDGET_NAMES[4]: (
            "INT",
            {"default": 4, "min": 0, "max": 60, "step": 1, "tooltip": "预热步数：开头这些步永远实算，保证画面先立住。"},
        ),
        ACCEL_WIDGET_NAMES[5]: (
            "INT",
            {"default": 2, "min": 0, "max": 60, "step": 1, "tooltip": "最大连跳：连续跳步上限，防止一路复用跑偏。"},
        ),
        ACCEL_WIDGET_NAMES[6]: (
            "FLOAT",
            {"default": 0.15, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "起始%：从采样进度的这个位置才开始允许跳步。"},
        ),
        ACCEL_WIDGET_NAMES[7]: (
            "FLOAT",
            {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "结束%：到这个进度之后不再跳步，收尾实算。"},
        ),
        ACCEL_WIDGET_NAMES[8]: (
            "INT",
            {"default": 8, "min": 1, "max": 64, "step": 1, "tooltip": "采样间隔：算变化量时的抽样步长，越大越省显存/越快判断。"},
        ),
    }


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def accel_config_from_mapping(values: Mapping[str, Any]) -> AccelConfig:
    """从节点 kwargs（键为界面控件名）构造配置，缺项自动取默认。"""
    get = values.get
    config = AccelConfig(
        attention=str(get(ACCEL_WIDGET_NAMES[0]) or ATTENTION_AUTO),
        motion_cache=bool(get(ACCEL_WIDGET_NAMES[1])),
        mc_reuse_threshold=_coerce_float(get(ACCEL_WIDGET_NAMES[2]), 0.08),
        mc_motion_strength=_coerce_float(get(ACCEL_WIDGET_NAMES[3]), 0.1),
        mc_warmup_steps=_coerce_int(get(ACCEL_WIDGET_NAMES[4]), 4),
        mc_max_skip=_coerce_int(get(ACCEL_WIDGET_NAMES[5]), 2),
        mc_start_percent=_coerce_float(get(ACCEL_WIDGET_NAMES[6]), 0.15),
        mc_end_percent=_coerce_float(get(ACCEL_WIDGET_NAMES[7]), 0.95),
        mc_metric_stride=_coerce_int(get(ACCEL_WIDGET_NAMES[8]), 8),
    )
    low, high = config.mc_start_percent, config.mc_end_percent
    if low > high:
        config.mc_start_percent, config.mc_end_percent = high, low
    config.mc_warmup_steps = max(0, config.mc_warmup_steps)
    config.mc_max_skip = max(0, config.mc_max_skip)
    config.mc_metric_stride = max(1, config.mc_metric_stride)
    return config


def attach_accel(bundle: Any, config: AccelConfig | None) -> Any:
    """把配置挂到 bundle 上（浅拷贝，不污染上游对象）。"""
    if bundle is None or config is None:
        return bundle
    try:
        cloned = copy.copy(bundle)
    except Exception:
        cloned = bundle
    try:
        cloned.accel = config
    except Exception:
        return bundle
    return cloned


def accel_of(bundle: Any) -> AccelConfig | None:
    return getattr(bundle, "accel", None) if bundle is not None else None


def log_accel_config(config: AccelConfig | None, source: str = "") -> None:
    """统一打印加速配置，并顺带提示本机还装了哪些第三方加速插件。"""
    if config is None:
        return
    prefix = f"{source}：" if source else ""
    _log(prefix + config.describe())
    extras = detect_external_accelerators()
    if extras:
        _log("检测到本机已装的其它加速插件：" + "、".join(extras) + "（可串在链路里叠加使用）")


# --------------------------------------------------------------------------------------
# 应用加速
# --------------------------------------------------------------------------------------


def apply_acceleration(model: Any, config: AccelConfig | None) -> Any:
    """给已经加载好的 MODEL 叠加加速补丁。返回（可能是 clone 出来的）MODEL。"""
    if model is None or config is None or not config.enabled:
        return model
    key = (id(model), config.signature())
    cached = config._cache.get(key)
    if cached is not None:
        return cached
    patched = model
    try:
        patched = _apply_attention(patched, config)
        patched = _apply_motion_cache(patched, config)
    except Exception as exc:  # 加速只是锦上添花，失败不要拖垮出片
        _warn(f"加速设置应用失败，已回退到未加速模型：{exc}")
        patched = model
    config._cache = {key: patched}
    return patched


def _apply_attention(model: Any, config: AccelConfig) -> Any:
    backend, note = resolve_attention_backend(config.attention)
    if backend is None:
        _log(note)
        return model
    func = attention_lib.get_attention_function(backend, None)
    if func is None:
        _warn(f"{note}，但后端没注册成功，保持默认。")
        return model
    patched = model.clone()
    patched.set_model_optimized_attention(func)
    _log(note)
    return patched


def _apply_motion_cache(model: Any, config: AccelConfig) -> Any:
    if not config.motion_cache:
        return model
    patched = model.clone()
    options = patched.model_options
    transformer_options = options.setdefault("transformer_options", {})
    if "easycache" in transformer_options:
        _warn("检测到 ComfyUI 自带 EasyCache/LazyCache，本次只保留运动缓存，请去掉其中一个。")
    transformer_options[MOTION_CACHE_KEY] = MotionCacheHolder(config)
    patched.add_wrapper_with_key(
        comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, MOTION_CACHE_KEY, motion_cache_outer_sample_wrapper
    )
    patched.add_wrapper_with_key(
        comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL, MOTION_CACHE_KEY, motion_cache_forward_wrapper
    )
    _log(
        "运动缓存已开启（阈值=%.3f，运动强度=%.2f，预热=%d步，最大连跳=%d，区间=%.0f%%~%.0f%%，采样间隔=%d）"
        % (
            config.mc_reuse_threshold,
            config.mc_motion_strength,
            config.mc_warmup_steps,
            config.mc_max_skip,
            config.mc_start_percent * 100.0,
            config.mc_end_percent * 100.0,
            config.mc_metric_stride,
        )
    )
    return patched


# --------------------------------------------------------------------------------------
# 运动缓存（TeaCache 式跳步复用）
# --------------------------------------------------------------------------------------


def _as_streams(value: Any) -> list[torch.Tensor] | None:
    """把模型输入/输出统一成张量列表；H3 是 [video, audio]。"""
    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, (list, tuple)) and value and all(isinstance(v, torch.Tensor) for v in value):
        return list(value)
    return None


def _restore_like(original: Any, streams: list[torch.Tensor]) -> Any:
    if isinstance(original, torch.Tensor):
        return streams[0]
    if isinstance(original, tuple):
        return tuple(streams)
    return streams


class MotionCacheHolder:
    """单个模型实例上的运动缓存状态机。"""

    def __init__(self, config: AccelConfig):
        self.threshold = float(config.mc_reuse_threshold)
        self.motion_strength = float(config.mc_motion_strength)
        self.warmup_steps = int(config.mc_warmup_steps)
        self.max_skip = int(config.mc_max_skip)
        self.start_percent = float(config.mc_start_percent)
        self.end_percent = float(config.mc_end_percent)
        self.stride = max(1, int(config.mc_metric_stride))
        self.total_steps = 0
        self.skipped_steps = 0
        self.reset()

    # -- 状态 ------------------------------------------------------------------
    def reset(self) -> None:
        self._prev_inputs: list[torch.Tensor] | None = None
        self._prev_residuals: list[torch.Tensor] | None = None
        self._cumulative = 0.0
        self._consecutive_skips = 0
        self._last_step: int | None = None
        self._shape_key: tuple | None = None

    # -- 工具 ------------------------------------------------------------------
    def _sample(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor.detach().reshape(-1)[:: self.stride].float()

    def _change(self, streams: list[torch.Tensor]) -> float | None:
        if self._prev_inputs is None or len(self._prev_inputs) != len(streams):
            return None
        total = 0.0
        for current, previous in zip(streams, self._prev_inputs):
            if current.shape != previous.shape:
                return None
            total += float((self._sample(current) - self._sample(previous)).abs().mean())
        return total

    def _store(self, streams: list[torch.Tensor], output: list[torch.Tensor]) -> None:
        if len(streams) != len(output):
            self._prev_inputs = None
            self._prev_residuals = None
            return
        inputs: list[torch.Tensor] = []
        residuals: list[torch.Tensor] = []
        for x, y in zip(streams, output):
            if x.shape != y.shape:
                self._prev_inputs = None
                self._prev_residuals = None
                return
            inputs.append(x.detach().clone())
            residuals.append((y.detach() - x.detach()).clone())
        self._prev_inputs = inputs
        self._prev_residuals = residuals

    def _reuse(self, streams: list[torch.Tensor]) -> list[torch.Tensor]:
        assert self._prev_residuals is not None
        return [x + residual.to(x.dtype) for x, residual in zip(streams, self._prev_residuals)]

    # -- 主流程 ----------------------------------------------------------------
    def run(self, executor: Any, args: tuple, kwargs: dict, transformer_options: Mapping[str, Any]) -> Any:
        inputs = _as_streams(args[0] if args else None)
        if inputs is None:
            return executor(*args, **kwargs)

        shape_key = tuple((tuple(t.shape), t.dtype) for t in inputs)
        step, total = self._progress(args, transformer_options)
        if shape_key != self._shape_key:
            self.reset()
            self._shape_key = shape_key
        if step is not None and (step == 0 or (self._last_step is not None and step < self._last_step)):
            self.reset()
        self._last_step = step
        self.total_steps += 1

        percent = step / float(total) if (step is not None and total) else None
        in_range = True if percent is None else (self.start_percent <= percent <= self.end_percent)
        past_warmup = step is None or step >= self.warmup_steps

        if not in_range or not past_warmup:
            # 该步必须实算，顺手清掉复用残留，避免跨区间复用旧结果。
            self._prev_inputs = None
            self._prev_residuals = None
            self._cumulative = 0.0
            self._consecutive_skips = 0
            output = executor(*args, **kwargs)
            out_streams = _as_streams(output)
            if out_streams is not None:
                self._store(inputs, out_streams)
            return output

        change = self._change(inputs)
        if change is not None and self._prev_residuals is not None:
            self._cumulative += change * self.motion_strength
            if self._cumulative < self.threshold and self._consecutive_skips < self.max_skip:
                self._consecutive_skips += 1
                self.skipped_steps += 1
                return _restore_like(args[0], self._reuse(inputs))
            self._cumulative = 0.0

        output = executor(*args, **kwargs)
        self._consecutive_skips = 0
        out_streams = _as_streams(output)
        if out_streams is not None:
            self._store(inputs, out_streams)
        else:
            self._prev_inputs = None
            self._prev_residuals = None
        return output

    def _progress(self, args: tuple, transformer_options: Mapping[str, Any]) -> tuple[int | None, int | None]:
        sigmas = transformer_options.get("sigmas")
        if sigmas is None or len(args) < 2:
            return None, None
        try:
            sigma = float(torch.as_tensor(args[1]).reshape(-1)[0]) / 1000.0
            schedule = torch.as_tensor(sigmas).reshape(-1).float()
            total = int(schedule.shape[0]) - 1
            if total <= 0:
                return None, None
            index = int(torch.argmin((schedule - sigma).abs()).item())
            return index, total
        except Exception:
            return None, None

    def report(self) -> None:
        if not self.total_steps:
            return
        speedup = self.total_steps / max(1, self.total_steps - self.skipped_steps)
        _log("运动缓存复用了 %d/%d 次前向（约 %.2fx 提速）" % (self.skipped_steps, self.total_steps, speedup))


def _holder_from(transformer_options: Any) -> MotionCacheHolder | None:
    if isinstance(transformer_options, Mapping):
        holder = transformer_options.get(MOTION_CACHE_KEY)
        if isinstance(holder, MotionCacheHolder):
            return holder
    return None


def motion_cache_forward_wrapper(executor: Any, *args: Any, **kwargs: Any) -> Any:
    transformer_options = kwargs.get("transformer_options")
    if transformer_options is None and args and isinstance(args[-1], Mapping):
        transformer_options = args[-1]
    holder = _holder_from(transformer_options)
    if holder is None:
        return executor(*args, **kwargs)
    return holder.run(executor, args, kwargs, transformer_options)


def motion_cache_outer_sample_wrapper(executor: Any, *args: Any, **kwargs: Any) -> Any:
    """每次采样开始前重置状态，结束后打印复用统计。"""
    guider = getattr(executor, "class_obj", None)
    model_options = getattr(guider, "model_options", None)
    holder = _holder_from(model_options.get("transformer_options")) if isinstance(model_options, Mapping) else None
    if holder is not None:
        holder.reset()
        holder.total_steps = 0
        holder.skipped_steps = 0
    try:
        return executor(*args, **kwargs)
    finally:
        if holder is not None:
            holder.report()


# --------------------------------------------------------------------------------------
# 独立节点：MiniMax H3 Aicg 加速设置
# --------------------------------------------------------------------------------------


class MiniMaxH3EasyAccel:
    """加载器与生成节点之间串一个"加速设置"，专门管加速，不动加载器。"""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "apply"
    RETURN_TYPES = ("MINIMAX_H3_BUNDLE",)
    RETURN_NAMES = ("h3_bundle",)
    DESCRIPTION = (
        "专门配置 MiniMax H3 的加速：注意力后端（SageAttention 等）与运动缓存（MotionCache）。"
        "用法：MiniMax H3 Aicg 加载器 → 本节点 → 生成/渲染节点。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        required: dict[str, tuple] = {"h3_bundle": ("MINIMAX_H3_BUNDLE",)}
        required.update(accel_widget_input_types())
        return {"required": required}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return "|".join(f"{name}={kwargs.get(name)!r}" for name in ACCEL_WIDGET_NAMES)

    def apply(self, h3_bundle, **kwargs):
        config = accel_config_from_mapping(kwargs)
        log_accel_config(config, "加速设置节点")
        return (attach_accel(h3_bundle, config),)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyAccel": MiniMaxH3EasyAccel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyAccel": "MiniMax H3 Aicg 加速设置",
}
