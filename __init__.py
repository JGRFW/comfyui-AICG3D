# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 包含来自以下项目的代码（各自许可证见 THIRD_PARTY_NOTICES.md）：
# - ComfyUI-MiniMaxH3-Easy (MIT, nkxx188)
# - Goohai-MiniMax-H3_Integration (GPL-3.0-or-later, goohai)
#
# skills/ 与 prompt_guides/ 中的 MiniMax 官方提示词内容适用 MiniMax H3
# Community License Agreement，不属于本插件 GPL 作品的组成部分。

# -*- coding: utf-8 -*-
"""comfyui-AICG3D

基于 MiniMax H3 Easy 节点合并优化，加入统一的素材、技能与加载器界面。
"""
from .aicg3d.registry import build

NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = build()

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
