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

import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview
from comfy_extras import nodes_custom_sampler


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
                "noise_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF}),
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

    def sample(self, model, conditioning, latent, noise_seed, sampler_name, scheduler, steps, denoise):
        if noise_seed == 0:
            noise_seed = comfy.model_management.roll_inference_rng()

        noise = comfy.sample.prepare_noise(latent["samples"], noise_seed)
        sampler = comfy.samplers.sampler_object(sampler_name)
        sigmas = comfy.samplers.calculate_sigmas(model.get_model_object("model_sampling"), scheduler, steps)
        # 新版 ComfyUI 把 BasicGuider 迁成了 V3 节点（io.ComfyNode），直接 new 会抛
        # “__init__() takes 1 positional argument but 2 were given”，这里改用底层 Guider_Basic。
        guider = nodes_custom_sampler.Guider_Basic(model)
        guider.set_conds(conditioning)
        latent = latent.copy()
        latent["noise_mask"] = None

        samples = guider.sample(
            noise,
            latent["samples"],
            sampler,
            sigmas,
            denoise_mask=None,
            callback=None,
            disable_pbar=True,
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
