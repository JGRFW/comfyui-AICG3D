# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""把三个来源插件的节点汇总成一份注册表。

节点 ID 由这里统一加 AICG3D_H3 前缀，菜单分类统一到 AICG3D 下。

为什么要有前缀：上游 ComfyUI-MiniMaxH3-Easy 注册的是同一批类名，两个插件同时
启用时 ComfyUI 只保留其中一份 —— 被顶掉的那份会连前端界面一起失效，节点上还会
显示成对方插件包。带上自己的前缀以后两边互不干扰。

没装同名插件时（绝大多数用户）仍然沿用上游那套节点 ID，这样以前保存的工作流
不用改就能打开。
"""
from __future__ import annotations

from . import branding, compat, nodes as aicg3d_nodes, routes

NODE_ID_PREFIX = "AICG3D_H3"


def plugin_node_id(node_id: str) -> str:
    """MiniMaxH3EasyLoader -> AICG3D_H3Loader。"""
    if node_id.startswith(compat.UPSTREAM_PREFIX):
        return NODE_ID_PREFIX + node_id[len(compat.UPSTREAM_PREFIX):]
    return node_id


def _h3_easy() -> tuple[dict, dict]:
    from ..h3easy import nodes as h3
    from ..h3easy.aicg3d_sampler import AICG3DSamplerAdvanced

    # 节点表以 h3easy/nodes.py 为准：那里的 ID 与上游 ComfyUI-MiniMaxH3-Easy
    # 一一对应（含分段长视频、二采、Latent 放大、SelfLift 采样策略等全套节点），
    # 显示名同样是 Aicg 风格，前端 web/minimax_h3_easy_ui.js 按这些名字匹配节点面板。
    mapping = dict(h3.NODE_CLASS_MAPPINGS)
    display = dict(h3.NODE_DISPLAY_NAME_MAPPINGS)

    # Aicg 自带的合并采样器不在上游节点表里，单独补进来。
    mapping["MiniMaxH3EasySamplerAdvanced"] = AICG3DSamplerAdvanced
    display["MiniMaxH3EasySamplerAdvanced"] = "AICG-采样器（高级）"
    return mapping, display


def build() -> tuple[dict, dict]:
    part_mapping, part_display = _h3_easy()

    own_mapping: dict = {}
    own_display: dict = {}
    legacy_mapping: dict = {}
    legacy_display: dict = {}
    for node_id, node_class in part_mapping.items():
        own_id = plugin_node_id(node_id)
        own_mapping[own_id] = node_class
        legacy_mapping[node_id] = node_class
        if node_id in part_display:
            own_display[own_id] = part_display[node_id]
            legacy_display[node_id] = part_display[node_id]

    if compat.conflicting_plugins():
        mapping = dict(own_mapping)
        display = dict(own_display)
    else:
        mapping = dict(legacy_mapping)
        display = dict(legacy_display)

    mapping.update(aicg3d_nodes.NODE_CLASS_MAPPINGS)
    display.update(aicg3d_nodes.NODE_DISPLAY_NAME_MAPPINGS)

    for node_id, node_class in mapping.items():
        branding.apply(node_class, node_id)
    routes.register_routes()
    return mapping, display