# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""提示词方案目录（``prompt_guides/``）的单一数据源。

增删方案只要动文件夹，不用改代码、也不用重启 ComfyUI：

    prompt_guides/
        我的方案/             <- 新建一个目录就是一个新方案，目录名就是它的 id
            guide-zh.md       <- 中文正文
            guide.md          <- 英文正文；只有一份时中英共用
            meta.json         <- 可选，见下
            references/       <- 可选：附带的参考文件（.md / .txt），会一起喂给模型

``meta.json``（可选）::

    {"id": "my_guide", "name": "My Scheme", "name_zh": "我的方案", "languages": ["zh", "en"]}

``manifest.json`` 的优先级高于目录扫描：它固定了随插件一起发布的那些方案的 id、显示名与
语言，以及「H3 通用 / 基础模式 / 完整参考模式」三份公共规则，所以旧工作流里已经选好的
方案不会因为目录改名而错位。``h3_general`` 目录是常驻的通用规则，不会出现在可选方案里。
删掉目录或文件后本模块的缓存按 mtime 自动失效，不需要重启 ComfyUI。
"""
from __future__ import annotations

import json
import os
from typing import Any

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
GUIDES_DIR = os.path.join(PLUGIN_DIR, "prompt_guides")
MANIFEST_PATH = os.path.join(GUIDES_DIR, "manifest.json")

#: 「不使用场景方案，只走 H3 通用规则」的固定选项。
GENERAL_ONLY_ID = "none"
GENERAL_ONLY_NAME = "通用"
GENERAL_ONLY_NAME_EN = "General only"

#: 「H3 通用」规则的默认目录名（manifest 缺失时按它找）。
GENERAL_FOLDER = "h3_general"

_LANGUAGES = ("zh", "en")
_ZH_BODY_NAMES = ("guide-zh.md", "guide.cn.md", "SKILL.cn.md")
_EN_BODY_NAMES = ("guide-en.md", "guide.en.md", "SKILL.en.md")
_NEUTRAL_BODY_NAMES = ("guide.md", "SKILL.md", "README.md")
_REFERENCE_SUFFIXES = (".md", ".txt")
#: 公共规则参考文件的文件名前缀 -> 结果字段名。
_REFERENCE_KINDS = (("base", "base_reference_by_language"), ("ref", "ref_reference_by_language"))

_CACHE: dict[str, Any] = {
    "signature": None,
    "items": [],
    "by_id": {},
    "aliases": {},
    "manifest": {},
    "general_item": None,
}


# --------------------------------------------------------------------- 基础工具
def _normalize_language(value: Any) -> str:
    return "zh" if str(value or "").strip().lower() in {"zh", "zh-cn", "zh-hans", "chinese", "中文"} else "en"


def _languages(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)) or not values:
        return list(_LANGUAGES)
    resolved = {_normalize_language(item) for item in values}
    return [language for language in _LANGUAGES if language in resolved]


def _key(value: Any) -> str:
    return str(value or "").strip().lower()


def _read_json(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _first_existing(directory: str, names: tuple[str, ...]) -> str:
    for name in names:
        if os.path.isfile(os.path.join(directory, name)):
            return name
    return ""


def _subdirectories(directory: str) -> list[str]:
    """目录本身 + 紧邻的一层子目录：兼容 ``方案/guide.md`` 与 ``方案/包/SKILL.md`` 两种摆法。"""
    found = [directory]
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return found
    for name in names:
        if name.startswith("."):
            continue
        candidate = os.path.join(directory, name)
        if os.path.isdir(candidate):
            found.append(candidate)
    return found


def _body_names(directory: str) -> tuple[dict[str, str], str]:
    """按语言找正文文件名，返回 (语言 -> 文件名, 正文所在目录)。"""
    for candidate in _subdirectories(directory):
        zh_only = _first_existing(candidate, _ZH_BODY_NAMES)
        en_only = _first_existing(candidate, _EN_BODY_NAMES)
        neutral = _first_existing(candidate, _NEUTRAL_BODY_NAMES)
        if not (zh_only or en_only or neutral):
            continue
        return {"zh": zh_only or neutral, "en": en_only or neutral}, candidate
    return {}, directory


def _relative(path: str) -> str:
    return os.path.relpath(path, GUIDES_DIR).replace(os.sep, "/")


def _reference_files(body_dir: str) -> list[str]:
    root = os.path.join(body_dir, "references")
    if not os.path.isdir(root):
        return []
    found = []
    for current, _dirs, names in os.walk(root):
        for name in sorted(names):
            if os.path.splitext(name)[1].lower() not in _REFERENCE_SUFFIXES:
                continue
            found.append(_relative(os.path.join(current, name)))
    return sorted(found)


def _folder_of(item: dict[str, Any]) -> str:
    path = str(item.get("path") or "").replace("\\", "/").strip("/")
    return path.split("/")[0] if path else ""


# --------------------------------------------------------------------- 目录 -> 方案
def _build_entry(folder: str, override: dict[str, Any]) -> dict[str, Any] | None:
    """把一个目录整理成方案条目；没有正文就返回 None（等同于这个方案不存在）。"""
    directory = os.path.join(GUIDES_DIR, folder)
    if not os.path.isdir(directory):
        return None
    meta = _read_json(os.path.join(directory, "meta.json"))
    bodies, body_dir = _body_names(directory)
    if not bodies:
        # 少数包把正文放在更深一层，manifest 里直接写死了路径，按它兜底。
        fallback = str(override.get("path") or "").replace("\\", "/")
        if not fallback or not os.path.isfile(os.path.join(GUIDES_DIR, fallback)):
            return None
        bodies = {"zh": os.path.basename(fallback), "en": os.path.basename(fallback)}
        body_dir = os.path.dirname(os.path.join(GUIDES_DIR, fallback))

    guide_id = str(meta.get("id") or override.get("id") or folder).strip() or folder
    name_zh = str(meta.get("name_zh") or override.get("name_zh") or meta.get("name") or override.get("name") or folder).strip() or folder
    name_en = str(meta.get("name_en") or meta.get("name") or override.get("name") or folder).strip() or folder

    path_by_language = {
        language: _relative(os.path.join(body_dir, name))
        for language, name in bodies.items()
        if name
    }
    declared = meta.get("languages") or override.get("languages")
    languages = _languages(declared) if declared else [item for item in _LANGUAGES if item in path_by_language]

    return {
        "id": guide_id,
        "name": name_zh,
        "name_zh": name_zh,
        "name_en": name_en,
        "languages": languages,
        "folder": folder,
        "dir": directory,
        "body_dir": body_dir,
        "path": path_by_language.get("en") or path_by_language.get("zh") or "",
        "path_by_language": path_by_language,
        "references": _reference_files(body_dir),
        "source": "manifest" if override else "folder",
    }


def _general_only_entry() -> dict[str, Any]:
    return {
        "id": GENERAL_ONLY_ID,
        "name": GENERAL_ONLY_NAME,
        "name_zh": GENERAL_ONLY_NAME,
        "name_en": GENERAL_ONLY_NAME_EN,
        "languages": list(_LANGUAGES),
        "folder": "",
        "dir": "",
        "body_dir": "",
        "path": "",
        "path_by_language": {},
        "references": [],
        "source": "builtin",
    }


def _scan(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """返回 (可选方案列表, H3 通用目录条目)。"""
    general_raw = manifest.get("general") if isinstance(manifest.get("general"), dict) else {}
    general_folder = _folder_of(general_raw) or GENERAL_FOLDER
    general_item = _build_entry(general_folder, general_raw)
    reserved = {general_folder, str(general_raw.get("id") or "").strip(), GENERAL_FOLDER}

    items: list[dict[str, Any]] = []
    consumed: set[str] = set()
    seen_ids: set[str] = set()

    for raw in manifest.get("scene_guides") or []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        guide_id = str(raw["id"]).strip()
        folder = _folder_of(raw)
        if not folder:
            # 没有指向目录的条目（例如「none」）：只保留它自己的说明。
            if guide_id in seen_ids or guide_id in reserved:
                continue
            seen_ids.add(guide_id)
            name_zh = str(raw.get("name_zh") or raw.get("name") or guide_id).strip() or guide_id
            name_en = str(raw.get("name") or name_zh).strip() or name_zh
            items.append({
                **_general_only_entry(),
                "id": guide_id,
                "name": name_zh,
                "name_zh": name_zh,
                "name_en": name_en,
                "languages": _languages(raw.get("languages")),
                "source": "manifest",
            })
            continue
        if folder in consumed or folder in reserved:
            consumed.add(folder)
            continue
        entry = _build_entry(folder, raw)
        consumed.add(folder)
        if entry is None or entry["id"] in seen_ids:
            # 目录被删掉了：这个方案跟着消失。
            continue
        seen_ids.add(entry["id"])
        items.append(entry)

    # 目录里多出来的方案：目录名排序后追加在后面。
    try:
        folders = sorted(os.listdir(GUIDES_DIR))
    except OSError:
        folders = []
    for folder in folders:
        if folder.startswith(".") or folder in consumed or folder in reserved:
            continue
        if not os.path.isdir(os.path.join(GUIDES_DIR, folder)):
            continue
        entry = _build_entry(folder, {})
        if entry is None or entry["id"] in seen_ids:
            continue
        seen_ids.add(entry["id"])
        items.append(entry)

    if GENERAL_ONLY_ID not in seen_ids:
        items.insert(0, _general_only_entry())
    return items, general_item


# --------------------------------------------------------------------- 缓存
def _file_stamp(path: str) -> tuple:
    try:
        stat = os.stat(path)
    except OSError:
        return (path, 0, 0)
    return (path, stat.st_mtime_ns, stat.st_size)


def _tree_stamps(root: str, depth: int = 4) -> list:
    stamps: list = []
    if not os.path.isdir(root):
        return stamps
    base = os.path.abspath(root).rstrip("\\/").count(os.sep)
    for current, dirs, names in os.walk(root):
        if os.path.abspath(current).rstrip("\\/").count(os.sep) - base >= depth:
            dirs[:] = []
            continue
        try:
            stamps.append((current, os.stat(current).st_mtime_ns))
        except OSError:
            pass
        for name in sorted(names):
            stamps.append(_file_stamp(os.path.join(current, name)))
    return stamps


def _signature() -> tuple:
    return (_file_stamp(MANIFEST_PATH), tuple(_tree_stamps(GUIDES_DIR)))


def _refresh() -> None:
    signature = _signature()
    if _CACHE["signature"] == signature:
        return
    manifest = _read_json(MANIFEST_PATH)
    items, general_item = _scan(manifest)
    aliases: dict[str, str] = {}
    for item in items:
        for candidate in (item["id"], item["folder"], item["name"], item["name_zh"], item["name_en"]):
            key = _key(candidate)
            if key:
                aliases.setdefault(key, item["id"])
    _CACHE.update({
        "signature": signature,
        "manifest": manifest,
        "items": items,
        "by_id": {item["id"]: item for item in items},
        "aliases": aliases,
        "general_item": general_item,
    })


# --------------------------------------------------------------------- 对外接口
def manifest() -> dict[str, Any]:
    """``prompt_guides/manifest.json`` 的内容。"""
    _refresh()
    return _CACHE["manifest"]


def items() -> list[dict[str, Any]]:
    """全部可选方案（含「通用」）。"""
    _refresh()
    return _CACHE["items"]


def find(value: Any) -> dict[str, Any] | None:
    """按 id、目录名或显示名找方案；找不到返回 None。"""
    _refresh()
    return _CACHE["by_id"].get(_CACHE["aliases"].get(_key(value), ""))


def resolve(value: Any) -> str:
    """把 id / 目录名 / 显示名统一成方案 id；认不出来就回落到「通用」。"""
    found = find(value)
    return found["id"] if found else GENERAL_ONLY_ID


def ids() -> list[str]:
    """给节点参数用的候选列表。"""
    return [item["id"] for item in items()] or [GENERAL_ONLY_ID]


def is_allowed(value: Any, language: str = "") -> bool:
    """方案是否存在、且支持该提示词语言。"""
    found = find(value)
    if found is None:
        return False
    if found["id"] == GENERAL_ONLY_ID:
        return True
    languages = found.get("languages") or []
    return not languages or _normalize_language(language) in languages


def guide_path(value: Any, language: str = "") -> str:
    """方案正文相对 ``prompt_guides/`` 的路径。"""
    found = find(value)
    if found is None:
        return ""
    paths = found.get("path_by_language") or {}
    return str(paths.get(_normalize_language(language)) or found.get("path") or "")


def references(value: Any) -> list[str]:
    """方案自带参考文件的相对路径。"""
    found = find(value)
    return list(found.get("references") or []) if found else []


def general_entry() -> dict[str, Any]:
    """「H3 通用 / 基础模式 / 完整参考模式」三份公共规则。"""
    _refresh()
    manifest_data = _CACHE["manifest"]
    general = manifest_data.get("general")
    if isinstance(general, dict) and general.get("path"):
        if os.path.isfile(os.path.join(GUIDES_DIR, str(general["path"]).replace("\\", "/"))):
            return dict(general)
    item = _CACHE["general_item"]
    if not item:
        return {}
    resolved: dict[str, Any] = {
        "id": item["id"],
        "path": item["path"],
        "path_by_language": dict(item["path_by_language"]),
    }
    for prefix, target in _REFERENCE_KINDS:
        found: dict[str, str] = {}
        for relative in item["references"]:
            stem, extension = os.path.splitext(os.path.basename(relative).lower())
            if extension not in _REFERENCE_SUFFIXES or not stem.startswith(prefix + "-"):
                continue
            language = stem[len(prefix) + 1:]
            if language in _LANGUAGES:
                found.setdefault(language, relative)
        if found:
            resolved[target] = found
    return resolved


def payload() -> list[dict[str, Any]]:
    """给前端下拉用的列表（不含任何绝对路径）。"""
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "name_zh": item["name_zh"],
            "name_en": item["name_en"],
            "languages": list(item["languages"]),
        }
        for item in items()
    ]
