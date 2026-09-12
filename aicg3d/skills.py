# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""AICG3D 统一技能库。

把三套来源合并成一个可检索的技能目录：

* ``skills/``        —— 原 llama-AI 的技能包（SKILL.md / SKILL.cn.md / references）
* ``prompt_guides/`` —— 原 MiniMaxH3-Easy 的场景提示词方案（guide.md + references）

同一个创作方案在两个来源里都存在时会被合并成一条记录，同时携带
``skill_id``（给多轮对话节点用）和 ``guide_id``（给 H3 主节点用）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SKILLS_DIR = os.path.join(PLUGIN_DIR, "skills")
GUIDES_DIR = os.path.join(PLUGIN_DIR, "prompt_guides")
GUIDE_MANIFEST = os.path.join(GUIDES_DIR, "manifest.json")

AUTO_SKILL = "自动选择"

# 同一套方案在两侧的 id 并不一致，这里手动对齐一次。
_SKILL_TO_GUIDE = {
    "3d-animation-short-generator": "3d_animation_short",
    "brand-promo-video-generator": "brand_promo",
    "co-op-game-intro-generator": "coop_game_intro",
    "handdrawn-live-video-generator": "handdrawn_live",
    "minimalist-product-ad-generator": "minimalist_product_ad",
    "mv-subtitle-skill-confirmed": "music_video_subtitle",
    "paper-collage-explainer-generator": "paper_collage",
    "papercraft-stop-motion-explainer": "papercraft_stop_motion",
    "h3-prompt-writing": "h3_general",
}

_TEXT_SUFFIXES = (".md", ".txt", ".yaml", ".yml", ".json")
_CACHE: dict[str, Any] = {"signature": None, "items": []}


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        return handle.read()


def _read_optional(path: str) -> str:
    try:
        return _read_text(path)
    except OSError:
        return ""


def _front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    lines = text[3:end].splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^([\w-]+):\s*(.*)$", lines[index])
        if not match:
            index += 1
            continue
        key, value = match.groups()
        if value in ("|", ">"):
            index += 1
            parts = []
            while index < len(lines) and (not lines[index].strip() or lines[index][:1].isspace()):
                parts.append(lines[index].strip())
                index += 1
            values[key] = " ".join(part for part in parts if part)
            continue
        values[key] = value.strip().strip("\"'")
        index += 1
    return values


def _meta_value(skill_dir: str, key: str) -> str:
    text = _read_optional(os.path.join(skill_dir, "meta.yaml"))
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else ""


def _list_files(directory: str, base_dir: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    found = []
    for root, _dirs, names in os.walk(directory):
        for name in names:
            if os.path.splitext(name)[1].lower() not in _TEXT_SUFFIXES:
                continue
            relative = os.path.relpath(os.path.join(root, name), base_dir).replace("\\", "/")
            found.append(relative)
    return sorted(found)


def _first_paragraph(text: str) -> str:
    body = re.sub(r"^---.*?\n---\s*", "", text, flags=re.DOTALL)
    for block in re.split(r"\n\s*\n", body):
        line = " ".join(part.strip() for part in block.strip().splitlines())
        line = re.sub(r"^#+\s*", "", line).strip()
        if len(line) > 12 and not line.startswith("```"):
            return line[:220]
    return ""


def _find_body(directory: str) -> str:
    """返回技能包里的正文文件绝对路径。"""
    for name in ("SKILL.cn.md", "SKILL.md", "guide.md", "README.md"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    return ""


def _guides() -> dict[str, dict[str, str]]:
    """读取 H3 场景方案目录：只保留真正带 guide.md 的方案。"""
    result: dict[str, dict[str, str]] = {}
    manifest = {}
    raw = _read_optional(GUIDE_MANIFEST)
    if raw:
        try:
            manifest = json.loads(raw)
        except json.JSONDecodeError:
            manifest = {}
    names: dict[str, dict[str, str]] = {}
    for entry in manifest.get("scene_guides") or []:
        if isinstance(entry, dict) and entry.get("id"):
            names[str(entry["id"])] = entry
    general = manifest.get("general") if isinstance(manifest.get("general"), dict) else {}
    if general.get("id"):
        names[str(general["id"])] = general

    if not os.path.isdir(GUIDES_DIR):
        return result
    for folder in sorted(os.listdir(GUIDES_DIR)):
        directory = os.path.join(GUIDES_DIR, folder)
        if not os.path.isdir(directory):
            continue
        body = _find_body(directory)
        if not body:
            continue
        guide_id = folder
        meta = names.get(guide_id, {})
        result[guide_id] = {
            "id": guide_id,
            "name": str(meta.get("name_zh") or meta.get("name") or guide_id),
            "name_en": str(meta.get("name") or ""),
            "body": body,
            "dir": directory,
        }
    return result


def _skills() -> dict[str, dict[str, Any]]:
    """扫描技能目录，兼容 ``skills/<id>/SKILL.md`` 与多一层子目录的写法。"""
    result: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(SKILLS_DIR):
        return result
    for folder in sorted(os.listdir(SKILLS_DIR)):
        root = os.path.join(SKILLS_DIR, folder)
        if not os.path.isdir(root) or folder.startswith("."):
            continue
        candidates = [root]
        candidates.extend(
            os.path.join(root, name) for name in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, name)) and not name.startswith(".")
        )
        for directory in candidates:
            body = _find_body(directory)
            if not body:
                continue
            skill_id = folder if directory == root else os.path.basename(directory)
            text = _read_text(body)
            metadata = _front_matter(text)
            name = _meta_value(directory, "display-name-zh") or metadata.get("name") or skill_id
            result[skill_id] = {
                "id": skill_id,
                "name": name,
                "name_en": _meta_value(directory, "display-name-en") or metadata.get("name") or "",
                "body": body,
                "dir": directory,
                "summary": _meta_value(directory, "summary-cn") or metadata.get("description") or "",
                "tag": _meta_value(directory, "tag-cn") or "",
            }
            break
    return result


def _tree_stamps(root: str, depth: int = 3) -> list:
    """递归采集目录 mtime，改动任意一层都能让缓存失效。"""
    stamps: list = []
    if not os.path.isdir(root):
        return stamps
    base = os.path.abspath(root).rstrip("\\/").count(os.sep)
    for current, dirs, _names in os.walk(root):
        if os.path.abspath(current).rstrip("\\/").count(os.sep) - base >= depth:
            dirs[:] = []
            continue
        try:
            stamps.append((current, os.stat(current).st_mtime_ns))
        except OSError:
            pass
    return stamps


def _file_stamp(path: str) -> tuple:
    try:
        return (path, os.stat(path).st_mtime_ns)
    except OSError:
        return (path, 0)


def _signature() -> tuple:
    parts = []
    for root in (SKILLS_DIR, GUIDES_DIR):
        parts.extend(_tree_stamps(root))
    parts.append(_file_stamp(GUIDE_MANIFEST))
    return tuple(parts)


def discover() -> list[dict[str, Any]]:
    """返回合并后的技能列表（按来源顺序稳定排序）。"""
    signature = _signature()
    if _CACHE["signature"] == signature:
        return _CACHE["items"]

    guides = _guides()
    skills = _skills()
    consumed_guides: set[str] = set()
    items: list[dict[str, Any]] = []

    for skill_id, skill in skills.items():
        guide_id = _SKILL_TO_GUIDE.get(skill_id, "")
        guide = guides.get(guide_id) if guide_id else None
        if guide:
            consumed_guides.add(guide_id)
        references = _list_files(os.path.join(skill["dir"], "references"), PLUGIN_DIR)
        items.append({
            "id": skill_id,
            "name": skill["name"] or (guide or {}).get("name") or skill_id,
            "name_en": skill["name_en"] or (guide or {}).get("name_en", ""),
            "summary": skill["summary"] or (guide and _first_paragraph(_read_text(guide["body"]))) or "",
            "tag": skill["tag"],
            "kind": "both" if guide else "skill",
            "skill_id": skill_id,
            "guide_id": guide_id if guide else "",
            "body": skill["body"],
            "references": references,
            "dir": skill["dir"],
        })

    for guide_id, guide in guides.items():
        if guide_id in consumed_guides or guide_id == "h3_general":
            continue
        items.append({
            "id": guide_id,
            "name": guide["name"],
            "name_en": guide["name_en"],
            "summary": _first_paragraph(_read_text(guide["body"])),
            "tag": "H3 场景方案",
            "kind": "guide",
            "skill_id": "",
            "guide_id": guide_id,
            "body": guide["body"],
            "references": _list_files(os.path.join(guide["dir"], "references"), PLUGIN_DIR),
            "dir": guide["dir"],
        })

    _CACHE["signature"] = signature
    _CACHE["items"] = items
    return items


# ---------------------------------------------------------------------------
# 提示词模板库（prompt_presets/）
# ---------------------------------------------------------------------------
PRESETS_DIR = os.path.join(PLUGIN_DIR, "prompt_presets")
PRESET_MANIFEST = os.path.join(PRESETS_DIR, "manifest.json")

_PRESET_CACHE: dict[str, Any] = {"signature": None, "items": [], "categories": []}


def _preset_raw() -> list[dict[str, str]]:
    raw = _read_optional(PRESET_MANIFEST)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    result = []
    for entry in data.get("categories") or []:
        if isinstance(entry, dict) and entry.get("id"):
            result.append({
                "id": str(entry["id"]),
                "name": str(entry.get("name") or entry["id"]),
                "summary": str(entry.get("summary") or ""),
            })
    return result


def preset_categories() -> list[dict[str, Any]]:
    """返回模板分类清单（含每个分类的条目数）。"""
    discover_presets()
    return [dict(item) for item in _PRESET_CACHE["categories"]]


def _preset_signature() -> tuple:
    parts: list[Any] = list(_tree_stamps(PRESETS_DIR, depth=3))
    parts.append(_file_stamp(PRESET_MANIFEST))
    return tuple(parts)


def discover_presets() -> list[dict[str, Any]]:
    """扫描 prompt_presets/<分类>/<id>/，返回提示词模板列表。"""
    signature = _preset_signature()
    if _PRESET_CACHE["signature"] == signature:
        return _PRESET_CACHE["items"]

    declared = _preset_raw()
    names = {item["id"]: item["name"] for item in declared}
    order = {item["id"]: index for index, item in enumerate(declared)}
    counts: dict[str, int] = {}

    items: list[dict[str, Any]] = []
    if os.path.isdir(PRESETS_DIR):
        for category in sorted(os.listdir(PRESETS_DIR)):
            directory = os.path.join(PRESETS_DIR, category)
            if category.startswith(".") or not os.path.isdir(directory):
                continue
            for preset_id in sorted(os.listdir(directory)):
                pack = os.path.join(directory, preset_id)
                if not os.path.isdir(pack):
                    continue
                body = _find_body(pack)
                if not body:
                    continue
                text = _read_text(body)
                metadata = _front_matter(text)
                name = _meta_value(pack, "display-name-zh") or metadata.get("name") or preset_id
                category_name = names.get(category, category)
                counts[category] = counts.get(category, 0) + 1
                items.append({
                    "id": preset_id,
                    "name": name,
                    "name_en": _meta_value(pack, "display-name-en") or "",
                    "label": f"{category_name}｜{name}",
                    "summary": _meta_value(pack, "summary-cn") or _first_paragraph(text),
                    "tag": _meta_value(pack, "tag-cn") or category_name,
                    "keywords": _meta_value(pack, "keywords"),
                    "kind": "preset",
                    "source": _meta_value(pack, "source"),
                    "category": category,
                    "category_name": category_name,
                    "chars": len(text),
                    "skill_id": "",
                    "guide_id": "",
                    "body": body,
                    "references": [],
                    "dir": pack,
                })

    items.sort(key=lambda item: (order.get(item["category"], 99), item["name"]))
    categories = [
        {
            "id": entry["id"],
            "name": entry["name"],
            "summary": entry["summary"],
            "count": counts.get(entry["id"], 0),
        }
        for entry in declared
    ]

    _PRESET_CACHE["signature"] = signature
    _PRESET_CACHE["items"] = items
    _PRESET_CACHE["categories"] = categories
    return items


def preset_catalogue() -> str:
    """给 LLM 用的模板目录（只列分类与名称，控制 token）。"""
    lines = []
    for category in preset_categories():
        lines.append(f'# {category["name"]}（{category["count"]}）')
        for item in discover_presets():
            if item["category"] == category["id"]:
                lines.append(f'- {item["label"]}: {item["summary"][:160]}')
    return "\n".join(lines)


def get(skill_id: str) -> dict[str, Any] | None:
    wanted = str(skill_id or "").strip()
    # 节点下拉用的是 “名称 [id]” 形式，这里同时接受标签与纯 id。
    label = re.fullmatch(r".*\[([^\[\]]+)\]\s*", wanted)
    if label:
        wanted = label.group(1).strip()
    if not wanted or wanted == AUTO_SKILL:
        return None
    for item in discover():
        if item["id"] == wanted or item["skill_id"] == wanted or item["guide_id"] == wanted:
            return item
    for item in discover_presets():
        if item["id"] == wanted or item["label"] == wanted or item["name"] == wanted:
            return item
    return None


def read_body(skill: dict[str, Any]) -> str:
    return _read_text(skill["body"])


def read_reference(skill: dict[str, Any], relative_path: str) -> str:
    """读取技能包内的 reference，并保证不会跳出自有目录。"""
    normalized = str(relative_path or "").replace("\\", "/").strip("/")
    if normalized not in skill["references"]:
        raise ValueError(f"Skill reference 不存在：{normalized}")
    root = os.path.realpath(PLUGIN_DIR)
    path = os.path.realpath(os.path.join(root, normalized))
    if os.path.commonpath([root, path]) != root:
        raise ValueError("Skill reference 路径超出插件目录。")
    return _read_text(path)


def relative(path: str) -> str:
    return os.path.relpath(path, PLUGIN_DIR).replace("\\", "/")


def catalogue() -> str:
    return "\n".join(
        f'- {item["id"]}: {item["name"]}；{item["summary"][:500]}' for item in discover()
    )
