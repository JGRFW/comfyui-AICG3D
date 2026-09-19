# Copyright (c) 2026 nkxx188
# Licensed under the MIT License
#
# 本模块改编自 ComfyUI-MiniMaxH3-Easy (MIT License)
# 原始来源: https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy

# -*- coding: utf-8 -*-
"""AICG-采样器（高级）

把原生链路里散开的五个采样节点合并成一个节点，只留一个 LATENT 输出：

    RandomNoise          -> noise_seed
    BasicScheduler       -> sampler / scheduler / steps / denoise
    KSamplerSelect       -> sampler_name
    BasicGuider          -> model + conditioning
    SamplerCustomAdvanced -> 采样，输出 LATENT

合并后画布上的采样链路从 5 个节点收敛成 1 个，参数集中在一个面板里，
输出可以直接接到解码节点（例如 MiniMaxH3AVDecodeT8 的 av_latent）。
执行逻辑与原生 SamplerCustomAdvanced 完全一致，保证接上前端解码器
能拿到同样的 latent 结构。
"""
from __future__ import annotations

import random

import torch

import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview
from comfy_extras import nodes_custom_sampler


def _roll_inference_seed() -> int:
    """取一个 64 位随机种子（和 ComfyUI 自带 RandomNoise 的范围一致）。

    ComfyUI 0.35 的 comfy.model_management 里没有 roll_inference_rng，
    直接调用会抛 AttributeError。这里做兼容：有该接口就用它，没有就退回
    Python 随机数，保证节点在任何版本上都能跑。
    """
    roll = getattr(comfy.model_management, "roll_inference_rng", None)
    if callable(roll):
        try:
            return int(roll()) & 0xFFFFFFFFFFFFFFFF
        except Exception:
            pass
    return random.randint(0, 0xFFFFFFFFFFFFFFFF)


class AICG3DSamplerAdvanced:
    """一站式采样：噪声 / 调度器 / 采样器 / 引导器四合一。"""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "sample"
    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    DESCRIPTION = (
        "把 RandomNoise / BasicScheduler / KSamplerSelect / BasicGuider / "
        "SamplerCustomAdvanced 合并为一个节点，直接输出 LATENT。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "conditioning": ("CONDITIONING",),
                "noise_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "sampler_name": (comfy.samplers.SAMPLER_NAMES, {"default": "euler"}),
                "scheduler": (comfy.samplers.SCHEDULER_NAMES, {"default": "normal"}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "latent": ("LATENT",),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        keys = ("noise_seed", "sampler_name", "scheduler", "steps", "denoise")
        return "|".join(str(kwargs.get(key, "")) for key in keys)

    @classmethod
    def calculate_sigmas(cls, model, scheduler, steps, denoise):
        """按 denoise 截断 sigma 调度表（和 ComfyUI 自带 BasicScheduler 一致）。

        denoise < 1 时先把整条调度表按 ``int(steps / denoise)`` 铺满，再取末尾
        ``steps + 1`` 个 sigma 当作本次要走的区间：起点落在调度表中段，实际步数仍
        是 steps。以前这里没有截断，denoise 控件等于摆设（永远按 1.0 跑）。
        """
        steps = max(1, int(steps))
        denoise = min(1.0, max(0.0, float(denoise)))
        model_sampling = model.get_model_object("model_sampling")
        if denoise >= 1.0:
            return comfy.samplers.calculate_sigmas(model_sampling, scheduler, steps)
        if denoise <= 0.0:
            # 空 sigma：guider.sample 会原样返回输入 latent，等于不采样。
            return torch.FloatTensor([])
        total_steps = max(steps, int(steps / denoise))
        sigmas = comfy.samplers.calculate_sigmas(model_sampling, scheduler, total_steps)
        return sigmas[-(steps + 1):]

    def sample(
        self,
        model,
        conditioning,
        latent,
        noise_seed,
        sampler_name,
        scheduler,
        steps,
        denoise,
        on_step=None,
        on_preview=None,
    ):
        """一次完整采样：等价于 RandomNoise + BasicScheduler + KSamplerSelect + BasicGuider + SamplerCustomAdvanced。"""
        sigmas = self.calculate_sigmas(model, scheduler, steps, denoise)
        # 上一个节点（渲染器）的 seed 是 64 位控件，可能大于 32 位；这里统一落到
        # 64 位无符号区间，0 表示随机，避免大 seed / 负 seed 传进采样器时出问题。
        noise_seed = int(noise_seed) & 0xFFFFFFFFFFFFFFFF
        if noise_seed == 0:
            noise_seed = _roll_inference_seed()

        noise = comfy.sample.prepare_noise(latent["samples"], noise_seed)
        sampler = comfy.samplers.sampler_object(sampler_name)
        # 新版 ComfyUI 把 BasicGuider 迁成了 V3 节点（io.ComfyNode），直接 new 会抛
        # “__init__() takes 1 positional argument but 2 were given”，这里改用底层 Guider_Basic。
        guider = nodes_custom_sampler.Guider_Basic(model)
        guider.set_conds(conditioning)
        latent = latent.copy()
        latent["noise_mask"] = None

        # 进度条按「实际采样步数」算：父节点（渲染器）会把每步回调转成前端进度条，
        # 这里的 pbar 继续走 ComfyUI 原生进度，两边互不影响。
        total_steps = max(1, len(sigmas) - 1)
        pbar = comfy.utils.ProgressBar(total_steps)
        completed_steps = 0

        def _progress_callback(*args):
            nonlocal completed_steps
            completed_steps += 1
            if on_step is not None:
                try:
                    on_step(completed_steps, total_steps)
                except Exception:
                    pass
            preview = None
            if on_preview is not None:
                # 采样器回调签名是 (step, x0, x, total_steps)，这里只取第 2 个参数，
                # 兼容个别采样器额外塞参数的情况。父节点（渲染器）会把这一步的预览图
                # 解出来，并按 ComfyUI 原生格式返回，好让 Nodes 2.0（Vue 节点）的节点
                # 预览图也能显示，所以这里要接住它的返回值。
                x0 = args[1] if len(args) > 1 else None
                try:
                    preview = on_preview(x0, completed_steps, total_steps)
                except Exception:
                    preview = None
            # preview 是 (格式, PIL 图, 最大边) 或 None：带预览时 ComfyUI 原生的进度
            # hook 会把图作为二进制预览消息发给前端，Vue 节点模式就画在节点上。
            pbar.update_absolute(completed_steps, total_steps, preview)

        samples = guider.sample(
            noise,
            latent["samples"],
            sampler,
            sigmas,
            denoise_mask=None,
            callback=_progress_callback,
            disable_pbar=False,
            seed=noise_seed,
        )
        samples = samples.to(comfy.model_management.intermediate_device())

        out = latent.copy()
        out.pop("downscale_ratio_spacial", None)
        out.pop("downscale_ratio_temporal", None)
        out["samples"] = samples
        return (out,)


NODE_CLASS_MAPPINGS = {"MiniMaxH3EasySamplerAdvanced": AICG3DSamplerAdvanced}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasySamplerAdvanced": "AICG-采样器（高级）"
}
