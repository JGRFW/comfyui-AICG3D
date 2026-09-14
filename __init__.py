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
from .aicg3d import compat
from .aicg3d.registry import build, NODE_ID_PREFIX, plugin_node_id

NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = build()

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

_conflicts = compat.conflicting_plugins()
if _conflicts:
    print(
        "\n".join(
            [
                "",
                "=" * 78,
                "[AICG3D] 检测到同样提供 MiniMaxH3Easy* 节点的插件：" + "、".join(_conflicts),
                "         两者节点同名，同时启用会让重复的那份失效。",
                f"         本插件已自动改用自带前缀的节点 ID（{NODE_ID_PREFIX}*），两边互不干扰。",
                "         注意：以前保存、引用 MiniMaxH3Easy* 的旧工作流会连接到对方插件上；",
                "         本插件新保存的工作流则使用带前缀的节点 ID。",
                "         Duplicate MiniMaxH3Easy* nodes found: " + ", ".join(_conflicts),
                f"         Using prefixed node ids ({NODE_ID_PREFIX}*) for this pack.",
                "=" * 78,
                "",
            ]
        )
    )