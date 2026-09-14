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
import os

from .aicg3d.registry import build

NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = build()

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "warn_duplicate_loader_packs"]

_LOADER_CLASS = "MiniMaxH3EasyLoader"
_HERE = os.path.dirname(os.path.abspath(__file__))


def _declares_loader(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return _LOADER_CLASS in handle.read()
    except OSError:
        return False


def warn_duplicate_loader_packs():
    """列出同样注册了 MiniMaxH3EasyLoader 的其他插件目录名。

    两个插件抢同一个节点名时，前端只会认其中一套控件：另一套的界面建不起来，
    而它已经把原生控件藏掉了，用户看到的就是一个只剩标题的空白节点。
    启动时直接把话说清楚，比让人去翻控制台省事。
    """
    try:
        import folder_paths

        roots = folder_paths.get_folder_paths("custom_nodes")
    except Exception:
        return []

    duplicates = []
    for root in roots:
        try:
            entries = sorted(os.scandir(root), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            lowered = name.lower()
            if name.startswith(".") or lowered.endswith(".disabled"):
                continue
            if lowered == os.path.basename(_HERE).lower():
                continue
            if "h3" not in lowered or "minimax" not in lowered:
                continue
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            if _declares_loader(os.path.join(entry.path, "nodes.py")) or _declares_loader(
                os.path.join(entry.path, "__init__.py")
            ):
                duplicates.append(name)
    return duplicates


_duplicates = warn_duplicate_loader_packs()
if _duplicates:
    print(
        "\n".join(
            [
                "",
                "=" * 78,
                "[AICG3D] 检测到同样提供 MiniMaxH3EasyLoader 的插件：" + "、".join(_duplicates),
                "         两者节点同名，同时启用会让「MiniMax H3 Aicg 加载器」显示为空白。",
                "         请只保留一个：把不需要的那个改名为 xxx.disabled，然后重启 ComfyUI。",
                "         Duplicate loader nodes found: " + ", ".join(_duplicates),
                "         Keep only one of them (rename the other to xxx.disabled and restart).",
                "=" * 78,
                "",
            ]
        )
    )