# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
"""AICG3D 的统一节点注册表。"""
from __future__ import annotations

import importlib
import os
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


def _sparktts_nodes() -> tuple[dict, dict]:
    """Load the bundled Spark-TTS nodes without requiring an external plugin."""
    try:
        import aicg3d_sparktts
    except Exception as exc:
        print(f"[AICG3D] Bundled Spark-TTS unavailable: {exc}")
        return {}, {}
    return (
        dict(aicg3d_sparktts.NODE_CLASS_MAPPINGS),
        dict(aicg3d_sparktts.NODE_DISPLAY_NAME_MAPPINGS),
    )


_LEGACY_H3_COMPAT_IDS = {
    "MiniMaxH3EasyMediaLoader",
    "MiniMaxH3EasySequenceGlobal",
    "MiniMaxH3EasySequenceSegment",
    "MiniMaxH3EasySequenceCombine",
}


def _find_pose_plugin_module():
    """Locate the comfyui-aicg3d-PoseSwap plugin module.

    ComfyUI registers custom-node packages under a path-derived name
    (module_path.replace('.', '_x_')), so `importlib.import_module("comfyui-aicg3d-PoseSwap")`
    does not resolve the already-loaded package. Strategy, in order:
    1. Scan sys.modules for the package whose __file__ lives in a comfyui-aicg3d-PoseSwap dir
       (covers normal ComfyUI startup when this plugin loads after the sibling).
    2. Load the plugin's __init__.py directly from custom_nodes on disk, so the pose
       nodes work even when comfyui-AICG3D imports before comfyui-aicg3d-PoseSwap.
    """
    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        module_file = getattr(module, "__file__", None) or ""
        if "comfyui-aicg3d-PoseSwap" in module_file.replace("\\", "/") and "__init__.py" in module_file:
            return module
    try:
        import folder_paths
        base = folder_paths.get_folder_paths("custom_nodes")
    except Exception:
        base = []
    for custom_nodes_dir in base:
        pkg_dir = os.path.join(custom_nodes_dir, "comfyui-aicg3d-PoseSwap")
        init_file = os.path.join(pkg_dir, "__init__.py")
        if not os.path.isfile(init_file):
            continue
        try:
            import importlib.util
            import types
            pkg_name = "comfyui-aicg3d-PoseSwap"
            # 注册父包，让 __init__.py 里的 "from . import pose_data" 相对导入可解析
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [pkg_dir]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg
            data_file = os.path.join(pkg_dir, "pose_data.py")
            if os.path.isfile(data_file):
                data_spec = importlib.util.spec_from_file_location(pkg_name + ".pose_data", data_file)
                data_mod = importlib.util.module_from_spec(data_spec)
                sys.modules[pkg_name + ".pose_data"] = data_mod
                data_spec.loader.exec_module(data_mod)
            init_spec = importlib.util.spec_from_file_location(pkg_name, init_file)
            init_mod = importlib.util.module_from_spec(init_spec)
            sys.modules[pkg_name] = init_mod
            init_spec.loader.exec_module(init_mod)
            return init_mod
        except Exception as exc:
            print(f"[AICG3D] Could not load comfyui-aicg3d-PoseSwap from disk: {exc}")
            return None
    try:
        return importlib.import_module("comfyui-aicg3d-PoseSwap")
    except Exception as exc:
        print(f"[AICG3D] PoseQwen21 nodes unavailable (install comfyui-aicg3d-PoseSwap): {exc}")
        return None


def _pose_qwen21() -> tuple[dict, dict]:
    """Adopt the standalone comfyui-aicg3d-PoseSwap nodes under the AICG3D namespace.

    Uses a lazy import so AICG3D loads even when the sibling plugin is missing
    or fails to import (older ComfyUI core without native Qwen 2.1 nodes).
    """
    plugin = _find_pose_plugin_module()
    if plugin is None:
        return {}, {}

    mapping = {}
    display = {}
    for node_id in ("PoseQwen21PoseSelect", "PoseQwen21GarmentSelect", "PoseQwen21", "PoseQwen21PoseSwap"):
        base = getattr(plugin, node_id, None)
        if base is None:
            continue
        child = type(
            f"{base.__name__}AICG3D",
            (base,),
            {"__module__": base.__module__},
        )
        child.CATEGORY = branding.CATEGORY_POSE
        own_id = f"AICG3D_{node_id}"
        mapping[own_id] = child
        display[own_id] = {
            "PoseQwen21PoseSelect": "AICG3D PoseSwap → 姿势姿态控制",
            "PoseQwen21GarmentSelect": "AICG3D PoseSwap → 服装选择",
            "PoseQwen21": "AICG3D PoseSwap → Qwen2.1 姿态换姿生成",
            "PoseQwen21PoseSwap": "AICG3D PoseSwap → Qwen Edit 2511 换装生成",
        }[node_id]
    return mapping, display


def _add_legacy_h3_compat(mapping: dict, display: dict, part_mapping: dict, part_display: dict) -> None:
    """Expose a few old MiniMaxH3Easy* IDs when no upstream pack owns them."""
    comfy_nodes = sys.modules.get("nodes")
    external_mappings = getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {}) or {}
    for legacy_id in _LEGACY_H3_COMPAT_IDS:
        if legacy_id in external_mappings or legacy_id in mapping or legacy_id not in part_mapping:
            continue
        base_class = part_mapping[legacy_id]
        legacy_class = type(
            f"{base_class.__name__}LegacyCompat",
            (base_class,),
            {"DEPRECATED": True, "__module__": base_class.__module__},
        )
        mapping[legacy_id] = legacy_class
        legacy_display = part_display.get(legacy_id)
        if legacy_display:
            display[legacy_id] = f"{legacy_display}（旧版兼容）"


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

    spark_mapping, spark_display = _sparktts_nodes()
    mapping.update(spark_mapping)
    display.update(spark_display)

    pose_mapping, pose_display = _pose_qwen21()
    for node_id, node_class in pose_mapping.items():
        if node_id in mapping:
            continue
        mapping[node_id] = node_class
        if node_id in pose_display:
            display[node_id] = pose_display[node_id]

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

    try:
        import aicg3d_sparktts

        for node_id, node_class in aicg3d_sparktts.LEGACY_NODE_CLASS_MAPPINGS.items():
            if node_id in mapping or node_id in external_mappings:
                continue
            mapping[node_id] = node_class
            legacy_name = aicg3d_sparktts.LEGACY_NODE_DISPLAY_NAME_MAPPINGS.get(node_id)
            if legacy_name:
                display[node_id] = legacy_name
    except Exception:
        pass

    _add_legacy_h3_compat(mapping, display, part_mapping, part_display)

    for node_id, node_class in mapping.items():
        branding.apply(node_class, node_id)

    routes.register_routes()
    return mapping, display
