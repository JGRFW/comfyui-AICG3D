# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
"""AICG3D 的统一节点注册表。"""
from __future__ import annotations

import sys

# 绝不使用 "." 相对导入
import aicg3d.branding as branding
import aicg3d.compat as compat
import aicg3d.nodes as aicg3d_nodes
import aicg3d.routes as routes
import aicg3d.prompt_split as prompt_split
import aicg3d_h3easy.nodes as h3
import aicg3d_h3easy.character_motion as character_motion
from aicg3d_h3easy.aicg3d_sampler import AICG3DSamplerAdvanced

NODE_ID_PREFIX = "AICG3D_H3"


def plugin_node_id(node_id: str) -> str:
    if compat and node_id.startswith(compat.UPSTREAM_PREFIX):
        return NODE_ID_PREFIX + node_id[len(compat.UPSTREAM_PREFIX):]
    return node_id


def _integration_nodes() -> tuple[dict, dict]:
    """V3 integration nodes kept optional for older ComfyUI cores."""
    try:
        from aicg3d_h3goohai import nodes as goohai_nodes
    except Exception as exc:
        print(f"[AICG3D] Optional H3 integration nodes unavailable: {exc}")
        return {}, {}
    mapping = {
        "AICG3D_H3IntegrationGH": goohai_nodes.MiniMaxH3IntegrationGH,
        "AICG3D_H3IntegrationAdapterGH": goohai_nodes.MiniMaxH3IntegrationAdapterGH,
        "AICG3D_H3DualClockT8GH": goohai_nodes.MiniMaxH3DualClockT8GH,
        "AICG3D_H3AVDecodeT8GH": goohai_nodes.MiniMaxH3AVDecodeT8GH,
    }
    display = {
        "AICG3D_H3IntegrationGH": "MiniMax H3 Aicg 集成面板",
        "AICG3D_H3IntegrationAdapterGH": "MiniMax H3 Aicg 集成分离",
        "AICG3D_H3DualClockT8GH": "MiniMax H3 Aicg 双时钟采样器 T8",
        "AICG3D_H3AVDecodeT8GH": "MiniMax H3 Aicg AV 解码 T8",
    }
    return mapping, display


def _h3_easy() -> tuple[dict, dict]:
    mapping = dict(h3.NODE_CLASS_MAPPINGS)
    display = dict(h3.NODE_DISPLAY_NAME_MAPPINGS)
    mapping.update(character_motion.NODE_CLASS_MAPPINGS)
    display.update(character_motion.NODE_DISPLAY_NAME_MAPPINGS)
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

    integration_mapping, integration_display = _integration_nodes()
    for node_id, node_class in integration_mapping.items():
        if node_id in own_mapping:
            continue
        own_mapping[node_id] = node_class
        if node_id in integration_display:
            own_display[node_id] = integration_display[node_id]

    mapping = dict(own_mapping)
    display = dict(own_display)

    mapping.update(aicg3d_nodes.NODE_CLASS_MAPPINGS)
    display.update(aicg3d_nodes.NODE_DISPLAY_NAME_MAPPINGS)

    mapping.update(prompt_split.NODE_CLASS_MAPPINGS)
    display.update(prompt_split.NODE_DISPLAY_NAME_MAPPINGS)

    # Keep old workflows working without competing for the generic upstream ID.
    # If another PromptSplit plugin already registered it, ours uses only the
    # namespaced ID and cannot overwrite that plugin's class.
    comfy_nodes = sys.modules.get("nodes")
    external_mappings = getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {}) or {}
    for node_id, node_class in prompt_split.LEGACY_NODE_CLASS_MAPPINGS.items():
        if node_id in mapping or node_id in external_mappings:
            continue
        mapping[node_id] = node_class
        legacy_name = prompt_split.LEGACY_NODE_DISPLAY_NAME_MAPPINGS.get(node_id)
        if legacy_name:
            display[node_id] = legacy_name

    for node_id, node_class in mapping.items():
        branding.apply(node_class, node_id)

    routes.register_routes()
    return mapping, display
