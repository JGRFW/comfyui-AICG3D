# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""节点归类与前端配色。

三个来源插件原本各有自己的节点菜单分类，合并后统一收敛到 ``AICG3D``
命名空间下，用户在节点搜索里输入 AICG3D 就能看到整套节点。
H3 节点统一映射到 ``AICG3D_H3*`` 命名空间，避免与上游同名插件抢占注册表；旧工作流中的兼容 ID 仍按需保留。
"""
from __future__ import annotations

CATEGORY_H3 = "AICG3D/H3 工作流"
CATEGORY_INTEGRATION = "AICG3D/H3 集成"
CATEGORY_TEXT = "AICG3D/提示词与 Skill"

# 每个分组的主色，前端用同一套色板绘制节点头部与面板。
GROUP_COLORS = {
    CATEGORY_H3: "#3f6fa8",
    CATEGORY_INTEGRATION: "#7a5bb5",
    CATEGORY_TEXT: "#2f8f7f",
}

_H3_EASY_PREFIXES = ("MiniMaxH3Easy", "AICG3D_H3")
_INTEGRATION_IDS = {
    "MiniMaxH3IntegrationGH",
    "MiniMaxH3IntegrationAdapterGH",
    "MiniMaxH3DualClockT8GH",
    "MiniMaxH3AVDecodeT8GH",
    "AICG3D_H3IntegrationGH",
    "AICG3D_H3IntegrationAdapterGH",
    "AICG3D_H3DualClockT8GH",
    "AICG3D_H3AVDecodeT8GH",
}
_TEXT_NODE_IDS = {
    "AICG3DPromptSegmentSplit",
    "AICG3D_H3PromptSegmentSplit",
    "AICG3D_PromptPreset",
    "AICG3D_SkillLoader",
}


def category_for(node_id: str) -> str:
    if node_id in _INTEGRATION_IDS:
        return CATEGORY_INTEGRATION
    if node_id in _TEXT_NODE_IDS:
        return CATEGORY_TEXT
    if node_id.startswith(_H3_EASY_PREFIXES):
        return CATEGORY_H3
    return CATEGORY_TEXT


def apply(node_class, node_id: str) -> None:
    """把节点归到 AICG3D 分类下。

    V3（MiniMaxH3IntegrationGH 等）节点的分类写在 schema 里，改动会破坏
    前端已有的节点匹配逻辑，因此只处理 V1 节点。
    """
    if node_id in _INTEGRATION_IDS:
        return
    try:
        node_class.CATEGORY = category_for(node_id)
    except (AttributeError, TypeError):
        pass


# 显示名沿用原插件，避免破坏前端按名字匹配的逻辑；这里只补充分组前缀，
# 让节点菜单里同一来源的节点排在一起。
DISPLAY_PREFIX = {
    CATEGORY_H3: "",
    CATEGORY_INTEGRATION: "",
    CATEGORY_TEXT: "",
}

