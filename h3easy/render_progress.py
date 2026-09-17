# Copyright (c) 2026 nkxx188
# Licensed under the MIT License
#
# 本模块源自 ComfyUI-MiniMaxH3-Easy (MIT License)
# 原始来源: https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy

# -*- coding: utf-8 -*-
"""AICG-渲染器（高级）的阶段进度上报。

渲染节点内部要跑「采样 -> 视频解码 -> 音频解码 -> 合成」四步。ComfyUI 自带的
``comfy.utils.ProgressBar`` 只覆盖采样步数，解码阶段没有任何反馈，节点上看不出
「已经跑了多久、还要多久」。这里把阶段进度通过 WebSocket 的
``aicg3d_render_progress`` 消息推给前端，前端在节点底部画一条百分比进度条。

上报失败一律静默：进度只是观感，绝不能影响出图。
"""
from __future__ import annotations

import base64
import io
import time
from typing import Any, Optional

#: 采样占总进度的比例，剩下的留给解码与合成。
SAMPLE_SHARE = 0.9

STAGE_IDLE = ""
STAGE_SAMPLE = "sample"
STAGE_DECODE = "decode"

#: 两次上报之间的最小间隔（秒），避免高频 WebSocket 消息拖慢采样。
_MIN_INTERVAL = 0.2

#: 预览图最长边（像素），和 ComfyUI 原生预览的 MAX_PREVIEW_RESOLUTION 同量级。
_PREVIEW_MAX_SIDE = 512


def executing_ids() -> tuple[Optional[str], Optional[str]]:
    """取当前执行中的节点 id 与 prompt id（版本不兼容时返回 None）。"""
    try:
        from comfy_execution.utils import get_executing_context
    except Exception:
        return None, None
    try:
        context = get_executing_context()
    except Exception:
        return None, None
    if context is None:
        return None, None
    node_id = getattr(context, "node_id", None)
    prompt_id = getattr(context, "prompt_id", None)
    return (
        str(node_id) if node_id is not None else None,
        str(prompt_id) if prompt_id is not None else None,
    )


def progress_server():
    """拿 PromptServer 单例（导入失败返回 None）。"""
    try:
        from server import PromptServer
    except Exception:
        return None
    return getattr(PromptServer, "instance", None)


class RenderProgressReporter:
    """把渲染节点的阶段进度上报给前端，任何异常都吞掉。"""

    def __init__(self, node_id: Optional[str] = None, prompt_id: Optional[str] = None):
        default_node, default_prompt = executing_ids()
        self.node_id = str(node_id) if node_id is not None else default_node
        self.prompt_id = str(prompt_id) if prompt_id is not None else default_prompt
        self.started_at = time.perf_counter()
        self.stage = STAGE_IDLE
        self.stage_value = 0
        self.stage_total = 0
        self.overall = 0.0
        self.finished = False
        self.ok = True
        #: 最近一张预览（data URL），只在更新过的那次上报里带给前端。
        self.preview = ""
        self._preview_dirty = False
        self._last_sent_at = 0.0

    # ------------------------------------------------------------------ 内部
    def _elapsed(self) -> float:
        return max(0.0, time.perf_counter() - self.started_at)

    def _eta(self) -> Optional[float]:
        elapsed = self._elapsed()
        if self.overall <= 0.01 or elapsed <= 1.0:
            return None
        return max(0.0, elapsed / self.overall * (1.0 - self.overall))

    def _payload(self) -> dict[str, Any]:
        eta = self._eta()
        payload: dict[str, Any] = {
            "node_id": self.node_id,
            "prompt_id": self.prompt_id,
            "stage": self.stage,
            "value": self.stage_value,
            "max": self.stage_total,
            "overall": round(self.overall, 4),
            "elapsed": round(self._elapsed(), 2),
            "eta": None if eta is None else round(eta, 2),
            "done": self.finished,
            "ok": self.ok,
        }
        if self._preview_dirty and self.preview:
            # 只有换图的那一次才带预览，避免每条消息都重复几十 KB 的 base64。
            payload["preview"] = self.preview
        return payload

    def _send(self, force: bool = False) -> None:
        now = time.perf_counter()
        if not force and (now - self._last_sent_at) < _MIN_INTERVAL:
            return
        self._last_sent_at = now
        server = progress_server()
        payload = self._payload()
        self._preview_dirty = False
        if server is None:
            return
        try:
            server.send_sync(
                "aicg3d_render_progress",
                payload,
                getattr(server, "client_id", None),
            )
        except Exception:
            pass

    # -------------------------------------------------------------- 对外接口
    def begin_sample(self, total_steps: int) -> None:
        """采样开始：先占位，让前端立刻看到进度条（第一步往往最慢）。"""
        self.stage = STAGE_SAMPLE
        self.stage_total = max(1, int(total_steps or 1))
        self.stage_value = 0
        self.overall = 0.0
        self._send(force=True)

    def update_sample(self, done: int, total: int = 0) -> None:
        """采样每一步的回调。"""
        if total:
            self.stage_total = max(1, int(total))
        self.stage = STAGE_SAMPLE
        self.stage_value = max(0, int(done))
        ratio = min(1.0, self.stage_value / self.stage_total) if self.stage_total else 0.0
        self.overall = SAMPLE_SHARE * ratio
        self._send(force=self.stage_total > 0 and self.stage_value >= self.stage_total)

    def update_preview(self, data_url: Optional[str]) -> None:
        """收到一张新预览图：立刻推给前端，前端在节点里画出来。"""
        if not data_url:
            return
        self.preview = data_url
        self._preview_dirty = True
        self._send(force=True)

    def begin_decode(self) -> None:
        """解码 / 合成阶段：没有可拆分的步数，只报阶段名。"""
        self.stage = STAGE_DECODE
        self.stage_value = 0
        self.stage_total = 0
        self.overall = SAMPLE_SHARE
        self._send(force=True)

    def finish(self, ok: bool = True) -> None:
        """收尾：成功画到 100%，失败让前端立刻收起进度条。"""
        self.finished = True
        self.ok = bool(ok)
        if self.ok:
            self.overall = 1.0
            self.stage = STAGE_DECODE
        self._send(force=True)

class RenderPreviewEncoder:
    """把采样中间结果 x0 编成 JPEG data URL，供前端在节点里实时预览。

    ComfyUI 自带的预览是挂在「进度条 hook」上发给前端的，只有 Vue 节点模式
    才会画到节点上；本插件跑的是经典画布模式，所以这里自己解码、自己发。
    任何一步失败都直接返回 None，绝不影响出图。
    """

    def __init__(self, model: Any, max_side: Optional[int] = None):
        self.max_side = max(64, int(max_side or _PREVIEW_MAX_SIDE))
        self._previewer = None
        try:
            import latent_preview

            self.max_side = max(64, int(getattr(latent_preview, "MAX_PREVIEW_RESOLUTION", 0) or self.max_side))
            latent_format = model.model.latent_format
            self._previewer = latent_preview.get_previewer(model.load_device, latent_format)
            if self._previewer is None:
                # 用户把全局预览关了（NoPreviews），或者选了 TAESD 但权重没下：
                # 这个节点是显式要预览的，直接用 latent RGB 因子兜底。
                self._previewer = self._rgb_previewer(latent_format)
        except Exception:
            self._previewer = None

    @staticmethod
    def _rgb_previewer(latent_format: Any) -> Any:
        """按 latent 格式的 RGB 因子造一个轻量预览器（H3 自带 24 通道因子）。"""
        try:
            import latent_preview

            factors = getattr(latent_format, "latent_rgb_factors", None)
            if not factors:
                return None
            return latent_preview.Latent2RGBPreviewer(
                factors,
                getattr(latent_format, "latent_rgb_factors_bias", None),
                getattr(latent_format, "latent_rgb_factors_reshape", None),
            )
        except Exception:
            return None

    @property
    def available(self) -> bool:
        return self._previewer is not None

    def encode(self, x0: Any) -> Optional[str]:
        """x0 -> ``data:image/jpeg;base64,...``；拿不到预览就返回 None。"""
        if self._previewer is None or x0 is None:
            return None
        try:
            latent = x0
            # H3 的 AV latent 是嵌套张量（视频 + 音频），预览只看视频那一路。
            if getattr(latent, "is_nested", False):
                tensors = getattr(latent, "tensors", None) or ()
                if not tensors:
                    return None
                latent = tensors[0]
            if getattr(latent, "ndim", 0) == 5:
                latent = latent[:1]
            decoded = self._previewer.decode_latent_to_preview_image("JPEG", latent)
            image = decoded[1] if isinstance(decoded, tuple) else decoded
            if image is None:
                return None
            image = self._upscale(image).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        except Exception:
            return None

    def _upscale(self, image: Any) -> Any:
        """latent 预览只有几十像素，放大到最长边 max_side 再编码，肉眼看得出内容。"""
        try:
            width, height = image.size
            longest = max(int(width), int(height))
            if longest <= 0 or longest >= self.max_side:
                return image
            scale = self.max_side / float(longest)
            return image.resize((max(1, round(width * scale)), max(1, round(height * scale))))
        except Exception:
            return image
