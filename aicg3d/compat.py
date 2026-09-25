# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""上游同名插件探测。

ComfyUI-MiniMaxH3-Easy 与本插件注册的是同一批节点类名
（MiniMaxH3EasyLoader、MiniMaxH3Easy……）。ComfyUI 只会保留其中一份，
被顶掉的那份连同它的前端界面一起失效，节点上还会挂上对方插件包的名字。

所以这里在启动阶段扫一遍 custom_nodes，把"谁在跟我们抢名字"查清楚：
拿到结果后，注册表会改用本插件自己的 AICG3D_H3* 节点 ID。
"""
from __future__ import annotations

import os

UPSTREAM_PREFIX = "MiniMaxH3Easy"
LOADER_CLASS = f"{UPSTREAM_PREFIX}Loader"

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR_NAME = os.path.basename(PLUGIN_ROOT).lower()

_cache: list[str] | None = None


def _declares_upstream_nodes(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
            return LOADER_CLASS in content or "class MiniMaxH3" in content or "class MiniMax" in content
    except OSError:
        return False


def _looks_like_h3_pack(name: str) -> bool:
    lowered = name.lower()
    return "h3" in lowered and "minimax" in lowered


def conflicting_plugins(*, refresh: bool = False) -> list[str]:
    """返回同样提供 MiniMaxH3Easy* 节点的、已启用的插件目录名。"""
    global _cache
    if _cache is not None and not refresh:
        return list(_cache)

    names: list[str] = []
    try:
        import folder_paths

        roots = folder_paths.get_folder_paths("custom_nodes")
    except Exception:
        roots = []

    for root in roots or []:
        try:
            entries = sorted(os.scandir(root), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            lowered = name.lower()
            if name.startswith(".") or lowered.endswith(".disabled"):
                continue
            if lowered == PLUGIN_DIR_NAME or not _looks_like_h3_pack(name):
                continue
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            if _declares_upstream_nodes(os.path.join(entry.path, "nodes.py")) or _declares_upstream_nodes(
                os.path.join(entry.path, "__init__.py")
            ):
                names.append(name)

    _cache = list(names)
    return list(names)