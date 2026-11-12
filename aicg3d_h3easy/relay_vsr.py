# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""RelayVSR integration shared by AICG3D render and final-upscale nodes.

RelayVSR is a ComfyUI core capability. It uses a RelayVSR diffusion model and
its matching Flash VAE to reconstruct every frame from the every-15th-frame
latents produced by the model. Audio is deliberately handled outside this
module and always comes from the original video.
"""

from __future__ import annotations

import importlib
import os
import re
from fractions import Fraction
from typing import Any, Iterable

import folder_paths
import torch


RELAY_MODEL_PLACEHOLDER = "(未找到 RelayVSR 放大模型)"
RELAY_VAE_PLACEHOLDER = "(未找到 RelayVSR Flash VAE)"
RELAY_MODEL_REQUIRED_HINT = (
    "请安装 RelayVSR 模型到 models/diffusion_models/RelayVSR/，"
    "并安装对应倍数的 Flash VAE 到 models/vae/RelayVSR/"
)


def _relay_names(category: str) -> list[str]:
    try:
        names = list(folder_paths.get_filename_list(category) or [])
    except Exception:
        return []
    result = []
    for name in names:
        normalised = str(name or "").replace("\\", "/").lower()
        if "relayvsr" in normalised or "relay_vsr" in normalised:
            result.append(str(name))
    return sorted(dict.fromkeys(result), key=lambda value: value.lower())


def relay_model_choices() -> list[str]:
    choices = _relay_names("diffusion_models")
    return choices or [RELAY_MODEL_PLACEHOLDER]


def relay_vae_choices() -> list[str]:
    choices = _relay_names("vae")
    return choices or [RELAY_VAE_PLACEHOLDER]


def relay_scale(value: Any) -> int | None:
    name = os.path.basename(str(value or "").replace("\\", "/")).lower()
    matches = re.findall(r"(?:^|[_-])x([24])(?=[._-]|$)", name)
    if not matches:
        matches = re.findall(r"x([24])", name)
    if not matches:
        return None
    return int(matches[-1])


def default_relay_model() -> str:
    choices = relay_model_choices()
    for name in choices:
        compact = str(name).replace("\\", "/").lower()
        if relay_scale(name) == 2 and "lightx2v" in compact:
            return name
    for name in choices:
        if relay_scale(name) == 2:
            return name
    return choices[0]


def default_relay_vae(model_name: Any) -> str:
    choices = relay_vae_choices()
    wanted = relay_scale(model_name)
    if wanted is not None:
        for name in choices:
            if relay_scale(name) == wanted:
                return name
    for name in choices:
        if relay_scale(name) == 2:
            return name
    return choices[0]


def _require_choice(value: Any, choices: Iterable[str], label: str) -> str:
    resolved = str(value or "").strip()
    available = [str(item) for item in choices]
    if not resolved or resolved.startswith("(") or resolved not in available:
        raise ValueError(
            f"{label}无效。{RELAY_MODEL_REQUIRED_HINT}；"
            f"当前可选：{', '.join(available) if available else '无'}"
        )
    return resolved


def _output_values(output: Any) -> tuple[Any, ...]:
    values = getattr(output, "result", None)
    if values is None:
        values = getattr(output, "args", None)
    if values is None:
        values = output
    if not isinstance(values, (tuple, list)):
        values = (values,)
    return tuple(values)


def _core_node_class(node_id: str) -> type:
    if node_id == "RelayVSRConditioning":
        try:
            from comfy_extras.nodes_wan import RelayVSRConditioning

            return RelayVSRConditioning
        except Exception:
            pass
    if node_id == "VSRDecode":
        try:
            from comfy_extras.nodes_wan import VSRDecode

            return VSRDecode
        except Exception:
            pass

    try:
        core_nodes = importlib.import_module("nodes")
    except Exception as exc:
        raise RuntimeError(
            "无法加载 ComfyUI 核心节点。请把 ComfyUI 更新到包含 RelayVSR / VSR Decode 的版本。"
        ) from exc
    mapping = getattr(core_nodes, "NODE_CLASS_MAPPINGS", {}) or {}
    node_class = mapping.get(node_id)
    if node_class is None:
        raise RuntimeError(
            f"当前 ComfyUI 缺少核心节点 {node_id}。"
            "请更新 ComfyUI 到包含 RelayVSR 与 VSR Decode 的版本。"
        )
    return node_class


def _normalise_frames(frames: Any) -> torch.Tensor:
    if not isinstance(frames, torch.Tensor) or frames.ndim != 4:
        raise ValueError("RelayVSR 需要 [帧数, 高, 宽, 通道] 的 RGB 视频帧")
    if frames.shape[0] < 1 or frames.shape[-1] < 3:
        raise ValueError("RelayVSR 输入视频没有可用画面")
    output = frames[..., :3].detach().to(device="cpu", dtype=torch.float32).contiguous()
    if float(output.max()) > 1.5:
        output = output / 255.0
    return output.clamp(0.0, 1.0)


def _fit_frame_count(frames: torch.Tensor, count: int) -> torch.Tensor:
    wanted = max(1, int(count))
    current = int(frames.shape[0])
    if current >= wanted:
        return frames[:wanted].contiguous()
    if current < 1:
        raise ValueError("RelayVSR 没有输出可用画面")
    return torch.cat(
        (frames, frames[-1:].repeat(wanted - current, 1, 1, 1)),
        dim=0,
    ).contiguous()


def _lock_source_exposure(frames: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    """Keep each frame's luminance aligned with the untouched source frame."""
    if not isinstance(frames, torch.Tensor) or not isinstance(reference, torch.Tensor):
        return frames
    count = min(int(frames.shape[0]), int(reference.shape[0]))
    if count <= 0:
        return frames

    output = frames[:count].detach().to(device="cpu", dtype=torch.float32)
    ref = reference[:count].detach().to(device="cpu", dtype=torch.float32)
    if tuple(output.shape[1:3]) != tuple(ref.shape[1:3]):
        ref = torch.nn.functional.interpolate(
            ref.permute(0, 3, 1, 2),
            size=(int(output.shape[1]), int(output.shape[2])),
            mode="bilinear",
            align_corners=False,
        ).permute(0, 2, 3, 1)
    weights = torch.tensor(
        [0.2126, 0.7152, 0.0722],
        dtype=torch.float32,
    ).view(1, 1, 1, 3)
    output_luma = (output[..., :3] * weights).sum(dim=-1, keepdim=True).mean(
        dim=(1, 2),
        keepdim=True,
    )
    reference_luma = (ref[..., :3] * weights).sum(dim=-1, keepdim=True).mean(
        dim=(1, 2),
        keepdim=True,
    )
    gain = (reference_luma / output_luma.clamp_min(1e-4)).clamp(0.85, 1.18)
    corrected = (output * gain).clamp(0.0, 1.0).contiguous()
    if count < int(frames.shape[0]):
        corrected = torch.cat(
            (
                corrected,
                frames[count:].detach().to(device="cpu", dtype=torch.float32),
            ),
            dim=0,
        )
    return corrected


class RelayVSRRunner:
    """Load one RelayVSR model/VAE pair and reuse it for every time window."""

    def __init__(
        self,
        model_name: Any,
        vae_name: Any,
        *,
        detail: float = 0.5,
        lock_source_exposure: bool = True,
    ) -> None:
        self.model_name = _require_choice(
            model_name,
            relay_model_choices(),
            "RelayVSR 放大模型",
        )
        self.vae_name = _require_choice(
            vae_name,
            relay_vae_choices(),
            "RelayVSR Flash VAE",
        )
        model_scale = relay_scale(self.model_name)
        vae_scale = relay_scale(self.vae_name)
        if model_scale is not None and vae_scale is not None and model_scale != vae_scale:
            raise ValueError(
                f"RelayVSR 模型是 x{model_scale}，VAE 是 x{vae_scale}；两者必须使用相同倍数。"
            )

        self.detail = max(0.0, min(1.0, float(detail)))
        self.lock_source_exposure = bool(lock_source_exposure)

        core_nodes = importlib.import_module("nodes")
        loaded_model = core_nodes.UNETLoader().load_unet(self.model_name, "default")
        self.model = loaded_model[0] if isinstance(loaded_model, (tuple, list)) else loaded_model
        loaded_vae = core_nodes.VAELoader().load_vae(self.vae_name)
        self.vae = loaded_vae[0] if isinstance(loaded_vae, (tuple, list)) else loaded_vae
        print(
            f"[AICG3D RelayVSR] 已加载 {self.model_name} + {self.vae_name}，"
            f"细节强度 {self.detail:.2f}，曝光锁定 {'开' if self.lock_source_exposure else '关'}"
        )

    def enhance(self, frames: Any) -> torch.Tensor:
        source = _normalise_frames(frames)
        original_count = int(source.shape[0])


        # ComfyUI normally runs node execution under inference mode. Keep that
        # guarantee here as well so direct node calls and embedded runners cannot
        # leave autograd leaves inside the Flash VAE decode.
        with torch.inference_mode():
            conditioning_class = _core_node_class("RelayVSRConditioning")
            conditioning_output = conditioning_class.execute(self.model, source)
            conditioning_values = _output_values(conditioning_output)
            if len(conditioning_values) < 2:
                raise RuntimeError("RelayVSR 条件节点没有返回 positive / latent")
            positive, latent = conditioning_values[:2]

            core_nodes = importlib.import_module("nodes")
            sampled_output = core_nodes.KSampler().sample(
                self.model,
                0,
                1,
                1.0,
                "euler",
                "simple",
                positive,
                positive,
                latent,
                1.0,
            )
            sampled = sampled_output[0] if isinstance(sampled_output, (tuple, list)) else sampled_output

            decode_class = _core_node_class("VSRDecode")
            decode_output = decode_class.execute(
                self.vae,
                sampled,
                source,
                detail=self.detail,
            )
            decoded_values = _output_values(decode_output)
            if not decoded_values:
                raise RuntimeError("RelayVSR 解码节点没有返回画面")
            decoded = _normalise_frames(decoded_values[0])
            decoded = _fit_frame_count(decoded, original_count)
        if self.lock_source_exposure:
            decoded = _lock_source_exposure(decoded, source)
        return decoded


def apply_to_video(video: Any, runner: RelayVSRRunner) -> Any:
    """Enhance VIDEO frames and retain the exact original audio and frame rate."""
    if video is None or not hasattr(video, "get_components"):
        raise ValueError("RelayVSR 需要有效的 VIDEO 输入")
    components = video.get_components()
    frames = _normalise_frames(components.images)
    enhanced = runner.enhance(frames)

    from comfy_api.latest import InputImpl, Types

    fps = float(getattr(components, "frame_rate", 0.0) or 24.0)
    return InputImpl.VideoFromComponents(
        Types.VideoComponents(
            images=enhanced.contiguous(),
            audio=getattr(components, "audio", None),
            frame_rate=Fraction(str(fps)),
        )
    )
