# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""AICG3D 前端接口。

只提供展示层需要的数据（技能目录、LoRA 元信息、素材库），模型加载与执行
仍然完全由 ComfyUI 自己负责。所有路由都挂在 ``/aicg3d/api`` 下。
"""
from __future__ import annotations

import json
import os
import struct
from typing import Any

import folder_paths
from aiohttp import web

import aicg3d.prompt_guides as guide_lib
import aicg3d.skills as skill_lib

VERSION = "1.1.16"
PROJECT_NAME = "短剧工作台"
PROJECT_DESCRIPTION = "无限时长视频的 MiniMax H3 ComfyUI 工作流与插件"
REPOSITORY_URL = "https://github.com/JGRFW/comfyui-AICG3D"
SEARCH_ALIASES = [
    "短剧工作台",
    "无限时长视频的 MiniMax H3 工作流",
    "ComfyUI MiniMax H3 无限长视频",
    "MiniMax H3 本地短剧工作流",
    "MiniMax H3 无限分段生视频",
]
MEDIA_KINDS = {
    "image": (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"),
    "video": (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".mpg", ".mpeg", ".wmv", ".flv"),
    "audio": (".mp3", ".wav", ".flac", ".ogg", ".oga", ".m4a", ".aac", ".opus", ".wma"),
}
_PREVIEW_SUFFIXES = (".preview.png", ".preview.jpeg", ".preview.jpg", ".preview.webp", ".png", ".jpeg", ".jpg", ".webp")
_LORA_CACHE: dict[str, Any] = {}
_REGISTERED = False


def _lora_metadata(path: str) -> dict[str, Any]:
    """从 safetensors 头部读取 LoRA 的基础信息，结果按文件指纹缓存。"""
    try:
        stat = os.stat(path)
        key = f"{path}|{stat.st_mtime_ns}|{stat.st_size}"
    except OSError:
        return {}
    cached = _LORA_CACHE.get(path)
    if cached and cached.get("key") == key:
        return cached["value"]

    info: dict[str, Any] = {"size": stat.st_size}
    if path.lower().endswith(".safetensors"):
        try:
            with open(path, "rb") as handle:
                header_size = struct.unpack("<Q", handle.read(8))[0]
                if 0 < header_size < 64 * 1024 * 1024:
                    header = json.loads(handle.read(header_size).decode("utf-8"))
            meta = header.get("__metadata__") or {}
            mapping = {
                "ss_base_model_version": "base_model",
                "ss_sd_model_name": "source_model",
                "ss_network_module": "network",
                "ss_network_dim": "rank",
                "ss_network_alpha": "alpha",
                "ss_output_name": "title",
                "modelspec.title": "title",
                "modelspec.description": "description",
            }
            for source, target in mapping.items():
                value = meta.get(source)
                if value not in (None, "", "None") and target not in info:
                    info[target] = str(value)[:300]
            tensors = [name for name in header if name != "__metadata__"]
            info["tensor_count"] = len(tensors)
        except (OSError, ValueError, struct.error):
            pass

    for suffix in (".civitai.info", ".json"):
        sidecar = path[: -len(".safetensors")] + suffix if path.lower().endswith(".safetensors") else path + suffix
        if not os.path.isfile(sidecar):
            continue
        try:
            with open(sidecar, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            info.setdefault("title", str(payload.get("model", {}).get("name") or "")[:200])
            words = payload.get("trainedWords") or payload.get("trained_words")
            if isinstance(words, list) and words:
                info["trigger"] = ", ".join(str(word) for word in words[:8])[:300]
            info["base_model"] = info.get("base_model") or str(payload.get("baseModel") or "")
        except (OSError, ValueError):
            pass
        break

    _LORA_CACHE[path] = {"key": key, "value": info}
    return info


def _lora_preview(path: str) -> str:
    stem = os.path.splitext(path)[0]
    for candidate in (path + suffix for suffix in _PREVIEW_SUFFIXES[:4]):
        if os.path.isfile(candidate):
            return candidate
    for candidate in (stem + suffix for suffix in _PREVIEW_SUFFIXES[4:]):
        if os.path.isfile(candidate):
            return candidate
    return ""


def _entry_url(filename: str, storage: str = "input", subfolder: str = "") -> str:
    params = [f"filename={web_quote(filename)}", f"type={storage}"]
    if subfolder:
        params.append(f"subfolder={web_quote(subfolder)}")
    return "/view?" + "&".join(params)


def web_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(str(value), safe="")


def list_loras() -> list[dict[str, Any]]:
    entries = []
    for name in folder_paths.get_filename_list("loras"):
        try:
            path = folder_paths.get_full_path("loras", name)
        except Exception:
            path = None
        if not path or not os.path.isfile(path):
            continue
        info = _lora_metadata(path)
        entries.append({
            "name": name,
            "label": os.path.splitext(os.path.basename(name))[0],
            "group": os.path.dirname(name).replace("\\", "/"),
            "size": info.get("size", 0),
            "title": info.get("title", ""),
            "base_model": info.get("base_model", ""),
            "rank": info.get("rank", ""),
            "trigger": info.get("trigger", ""),
            "description": info.get("description", ""),
            "preview": f"/aicg3d/api/lora/preview?name={web_quote(name)}" if _lora_preview(path) else "",
        })
    entries.sort(key=lambda item: (item["group"], item["label"].lower()))
    return entries


def lora_preview_path(name: str) -> str:
    path = folder_paths.get_full_path("loras", name)
    if not path:
        return ""
    preview = _lora_preview(path)
    return preview if preview and os.path.isfile(preview) else ""


def list_media(kind: str = "", limit: int = 400) -> list[dict[str, Any]]:
    root = folder_paths.get_input_directory()
    wanted = MEDIA_KINDS.get(kind.lower())
    entries: list[dict[str, Any]] = []
    for current, _dirs, names in os.walk(root):
        for name in names:
            extension = os.path.splitext(name)[1].lower()
            if wanted:
                media_kind = kind.lower() if extension in wanted else ""
            else:
                media_kind = next(
                    (key for key, suffixes in MEDIA_KINDS.items() if extension in suffixes), ""
                )
            if not media_kind:
                continue
            absolute = os.path.join(current, name)
            subfolder = os.path.relpath(current, root).replace("\\", "/")
            subfolder = "" if subfolder == "." else subfolder
            try:
                stat = os.stat(absolute)
            except OSError:
                continue
            entries.append({
                "filename": name,
                "subfolder": subfolder,
                "kind": media_kind,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "path": f"{subfolder}/{name}" if subfolder else name,
                "url": _entry_url(name, "input", subfolder),
            })
            if len(entries) >= max(1, min(4000, int(limit))):
                break
    entries.sort(key=lambda item: item["mtime"], reverse=True)
    return entries


def _normalized_media_reference(value: Any) -> str:
    filename = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not filename or "\x00" in filename:
        return ""
    parts = [part for part in filename.split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def media_reference_exists(filename: str) -> bool:
    normalized = _normalized_media_reference(filename)
    if not normalized:
        return False
    try:
        input_root = os.path.realpath(folder_paths.get_input_directory())
        path = os.path.realpath(
            folder_paths.get_annotated_filepath(normalized, input_root)
        )
        if os.path.commonpath((input_root, path)) != input_root:
            return False
        return os.path.isfile(path)
    except (OSError, ValueError):
        return False

def _skill_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "name_en": item.get("name_en", ""),
        "summary": item.get("summary", ""),
        "tag": item.get("tag", ""),
        "kind": item.get("kind", "skill"),
        "skill_id": item.get("skill_id", ""),
        "guide_id": item.get("guide_id", ""),
        "references": item.get("references", []),
        "label": item.get("label", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "category_name": item.get("category_name", ""),
        "chars": item.get("chars", 0),
    }


def register_routes() -> bool:
    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        from server import PromptServer

        routes = PromptServer.instance.routes
    except Exception:
        return False

    @routes.get("/aicg3d/api/meta")
    async def aicg3d_meta(_request):
        return web.json_response({
            "name": PROJECT_NAME,
            "description": PROJECT_DESCRIPTION,
            "repository": REPOSITORY_URL,
            "search_aliases": SEARCH_ALIASES,
            "version": VERSION,
            "skills": len(skill_lib.discover()),
            "presets": len(skill_lib.discover_presets()),
            "prompt_guides": len(guide_lib.items()),
            "loras": len(folder_paths.get_filename_list("loras")),
        })

    @routes.get("/aicg3d/api/prompt-guides")
    async def aicg3d_prompt_guides(_request):
        """提示词方案列表：直接来自 prompt_guides/ 目录扫描，增删文件夹即时生效。"""
        return web.json_response({"guides": guide_lib.payload()})

    @routes.get("/aicg3d/api/skills")
    async def aicg3d_skills(_request):
        return web.json_response({"skills": [_skill_payload(item) for item in skill_lib.discover()]})

    @routes.get("/aicg3d/api/skills/{skill_id}")
    async def aicg3d_skill_detail(request):
        item = skill_lib.get(request.match_info.get("skill_id", ""))
        if item is None:
            return web.json_response({"error": "找不到该 Skill"}, status=404)
        payload = _skill_payload(item)
        payload["body"] = skill_lib.read_body(item)
        return web.json_response(payload)

    @routes.get("/aicg3d/api/presets")
    async def aicg3d_presets(_request):
        return web.json_response({
            "categories": skill_lib.preset_categories(),
            "presets": [_skill_payload(item) for item in skill_lib.discover_presets()],
        })

    @routes.get("/aicg3d/api/presets/{preset_id}")
    async def aicg3d_preset_detail(request):
        item = skill_lib.get(request.match_info.get("preset_id", ""))
        if item is None or item.get("kind") != "preset":
            return web.json_response({"error": "找不到该提示词模板"}, status=404)
        payload = _skill_payload(item)
        payload["body"] = skill_lib.read_body(item)
        return web.json_response(payload)

    @routes.get("/aicg3d/api/loras")
    async def aicg3d_loras(_request):
        return web.json_response({"loras": list_loras()})

    @routes.get("/aicg3d/api/lora/preview")
    async def aicg3d_lora_preview(request):
        path = lora_preview_path(request.query.get("name", ""))
        if not path:
            return web.Response(status=404)
        return web.FileResponse(path)

    @routes.get("/aicg3d/api/media")
    async def aicg3d_media(request):
        try:
            limit = int(request.query.get("limit", 400))
        except ValueError:
            limit = 400
        return web.json_response({
            "files": list_media(request.query.get("kind", ""), limit),
        })

    @routes.post("/aicg3d/api/media/validate")
    async def aicg3d_media_validate(request):
        try:
            payload = await request.json()
        except (TypeError, ValueError):
            return web.json_response({"error": "请求内容不是有效 JSON"}, status=400)
        raw_files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(raw_files, list):
            return web.json_response({"error": "files 必须是数组"}, status=400)

        checked = []
        missing = []
        seen = set()
        for item in raw_files[:1000]:
            if not isinstance(item, dict):
                continue
            filename = _normalized_media_reference(item.get("filename"))
            if not filename:
                continue
            owner_id = str(item.get("owner_id") or "")
            kind = str(item.get("kind") or "")
            key = (owner_id, kind, filename)
            if key in seen:
                continue
            seen.add(key)
            exists = media_reference_exists(filename)
            entry = {
                "owner_id": owner_id,
                "kind": kind,
                "filename": filename,
                "exists": exists,
            }
            checked.append(entry)
            if not exists:
                missing.append(entry)
        return web.json_response({
            "checked": len(checked),
            "missing": missing,
        })
    _REGISTERED = True
    return True


