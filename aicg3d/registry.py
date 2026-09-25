# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
"""整合注册表：绝对导入终极版。"""
from __future__ import annotations
import sys
import os

# 绝不使用 "." 相对导入
import aicg3d.branding as branding
import aicg3d.compat as compat
import aicg3d.nodes as aicg3d_nodes
import aicg3d.routes as routes
import aicg3d.prompt_split as prompt_split
import h3easy.nodes as h3
from h3easy.aicg3d_sampler import AICG3DSamplerAdvanced

NODE_ID_PREFIX = "AICG3D_H3"

def plugin_node_id(node_id: str) -> str:
    if compat and node_id.startswith(compat.UPSTREAM_PREFIX):
        return NODE_ID_PREFIX + node_id[len(compat.UPSTREAM_PREFIX):]
    return node_id

def _h3_easy() -> tuple[dict, dict]:
    mapping = dict(h3.NODE_CLASS_MAPPINGS)
    display = dict(h3.NODE_DISPLAY_NAME_MAPPINGS)
    mapping["MiniMaxH3EasySamplerAdvanced"] = AICG3DSamplerAdvanced
    display["MiniMaxH3EasySamplerAdvanced"] = "AICG-采样器（高级）"
    return mapping, display

def build() -> tuple[dict, dict]:
    part_mapping, part_display = _h3_easy()
    own_mapping, own_display = {}, {}
    
    for node_id, node_class in part_mapping.items():
        own_id = plugin_node_id(node_id)
        own_mapping[own_id] = node_class
        if node_id in part_display:
            own_display[own_id] = part_display[node_id]

    mapping = dict(own_mapping)
    display = dict(own_display)

    mapping.update(aicg3d_nodes.NODE_CLASS_MAPPINGS)
    display.update(aicg3d_nodes.NODE_DISPLAY_NAME_MAPPINGS)

    mapping.update(prompt_split.NODE_CLASS_MAPPINGS)
    display.update(prompt_split.NODE_DISPLAY_NAME_MAPPINGS)

    for node_id, node_class in mapping.items():
        branding.apply(node_class, node_id)
    
    routes.register_routes()
    return mapping, display
