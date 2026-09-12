# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""把三个来源插件的节点汇总成一份注册表。

节点 ID 全部保持原样，旧工作流导入后仍然能找到对应节点；只有菜单分类被
统一到 AICG3D 下。
"""
from __future__ import annotations

from . import branding, nodes as aicg3d_nodes, routes


def _h3_easy() -> tuple[dict, dict]:
    from ..h3easy import nodes as h3
    from ..h3easy.aicg3d_sampler import AICG3DSamplerAdvanced

    # 节点表以 h3easy/nodes.py 为准：那里的 ID 与上游 ComfyUI-MiniMaxH3-Easy
    # 一一对应（含分段长视频、二采、Latent 放大等全套节点），显示名同样是
    # Aicg 风格，前端 web/minimax_h3_easy_ui.js 按这些名字匹配节点面板。
    mapping = dict(h3.NODE_CLASS_MAPPINGS)
    display = dict(h3.NODE_DISPLAY_NAME_MAPPINGS)

    # Aicg 自带的合并采样器不在上游节点表里，单独补进来。
    mapping["MiniMaxH3EasySamplerAdvanced"] = AICG3DSamplerAdvanced
    display["MiniMaxH3EasySamplerAdvanced"] = "AICG-采样器（高级）"
    return mapping, display


def build() -> tuple[dict, dict]:
    mapping: dict = {}
    display: dict = {}
    part_mapping, part_display = _h3_easy()
    mapping.update(part_mapping)
    display.update(part_display)
    mapping.update(aicg3d_nodes.NODE_CLASS_MAPPINGS)
    display.update(aicg3d_nodes.NODE_DISPLAY_NAME_MAPPINGS)
    for node_id, node_class in mapping.items():
        branding.apply(node_class, node_id)
    routes.register_routes()
    return mapping, display
