# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Strict release audit for node IDs, UI extensions, and bundled workflows."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import nodes as comfy_nodes  # noqa: E402
import folder_paths  # noqa: E402

from aicg3d import registry  # noqa: E402


MAPPING_NAMES = {"NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"}
# ComfyUI loads these from comfy_extras after nodes.py, so they are absent
# from nodes.NODE_CLASS_MAPPINGS during a headless audit.
CORE_NODE_ALLOWLIST = {
    "BasicScheduler",
    "BlockSparseAttention",
    "KSamplerSelect",
    "LoadVideo",
    "MiniMaxH3SigmaShift",
    "ModelAttentionBackend",
    "SaveVideo",
}
# Generic aliases are only registered when no other custom-node pack owns
# the ID. They are compatibility bridges rather than plugin-owned IDs.
CONDITIONAL_COMPAT_IDS = {
    "AICG3DPromptSegmentSplit",
    "MiniMaxH3EasyMediaLoader",
    "MiniMaxH3EasySequenceCombine",
    "MiniMaxH3EasySequenceGlobal",
    "MiniMaxH3EasySequenceSegment",
    "SparkTTSClone",
    "SparkTTSRun",
}
IGNORED_NOTE_TYPES = {
    "Note",
    "MarkdownNote",
    "Label (rgthree)",
    "Label",
    "Reroute",
    "PrimitiveNode",
}


def _mapping_keys_from_dict(node: ast.Dict) -> list[str]:
    return [
        str(key.value)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    ]


def _scan_python_mapping_keys(root: Path, *, skip_root: Path | None = None) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [name for name in dirs if not name.startswith(".") and name != "__pycache__"]
        if skip_root and current_path == skip_root:
            dirs[:] = []
            files = []
        for name in files:
            if not name.endswith(".py"):
                continue
            path = current_path / name
            try:
                source = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(path))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    for target in targets:
                        if not isinstance(target, ast.Name) or target.id not in MAPPING_NAMES:
                            continue
                        if isinstance(value, ast.Dict):
                            result[target.id].extend(_mapping_keys_from_dict(value))
                        elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "dict":
                            if value.args and isinstance(value.args[0], ast.Dict):
                                result[target.id].extend(_mapping_keys_from_dict(value.args[0]))
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr != "update" or not isinstance(node.func.value, ast.Name):
                        continue
                    if node.func.value.id not in MAPPING_NAMES:
                        continue
                    for arg in node.args:
                        if isinstance(arg, ast.Dict):
                            result[node.func.value.id].extend(_mapping_keys_from_dict(arg))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Name)
                            and target.value.id in MAPPING_NAMES
                            and isinstance(target.slice, ast.Constant)
                            and isinstance(target.slice.value, str)
                        ):
                            result[target.value.id].append(target.slice.value)
    return result


def _collect_workflow_node_types(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for file in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
            continue
        subgraphs = {
            str(item.get("id"))
            for item in (payload.get("definitions", {}) or {}).get("subgraphs", [])
            if isinstance(item, dict) and item.get("id")
        }
        for node in payload["nodes"]:
            if isinstance(node, dict) and node.get("type"):
                node_type = str(node["type"])
                if node_type not in subgraphs:
                    result[node_type].append(str(file))
    return result


def _validate_workflow(file: Path, known_types: set[str], errors: list[str], warnings: list[str]) -> None:
    try:
        workflow = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{file}: invalid JSON: {exc}")
        return
    if not isinstance(workflow, dict):
        errors.append(f"{file}: workflow root is not an object")
        return
    nodes = workflow.get("nodes")
    links = workflow.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        errors.append(f"{file}: missing nodes/links arrays")
        return

    node_by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or "id" not in node:
            errors.append(f"{file}: node without id")
            continue
        node_id = node["id"]
        if node_id in node_by_id:
            errors.append(f"{file}: duplicate node id {node_id}")
        node_by_id[node_id] = node

    link_by_id = {}
    for link in links:
        if not isinstance(link, list) or len(link) < 6:
            errors.append(f"{file}: malformed link {link!r}")
            continue
        link_id, source_id, source_slot, target_id, target_slot, link_type = link[:6]
        if link_id in link_by_id:
            errors.append(f"{file}: duplicate link id {link_id}")
        link_by_id[link_id] = link
        source = node_by_id.get(source_id)
        target = node_by_id.get(target_id)
        if source is None:
            errors.append(f"{file}: link {link_id} has missing source node {source_id}")
            continue
        if target is None:
            errors.append(f"{file}: link {link_id} has missing target node {target_id}")
            continue
        outputs = source.get("outputs") or []
        inputs = target.get("inputs") or []
        if not isinstance(source_slot, int) or not 0 <= source_slot < len(outputs):
            errors.append(f"{file}: link {link_id} source slot {source_slot} missing on node {source_id}")
            continue
        if not isinstance(target_slot, int) or not 0 <= target_slot < len(inputs):
            errors.append(f"{file}: link {link_id} target slot {target_slot} missing on node {target_id}")
            continue
        source_type = outputs[source_slot].get("type")
        target_type = inputs[target_slot].get("type")
        if source_type not in (None, "*") and target_type not in (None, "*") and source_type != target_type:
            errors.append(
                f"{file}: link {link_id} type mismatch {source_type!r} -> {target_type!r}"
            )
        source_links = outputs[source_slot].get("links")
        source_links = source_links if isinstance(source_links, list) else []
        if link_id not in source_links:
            errors.append(f"{file}: link {link_id} missing from source output links")
        if inputs[target_slot].get("link") != link_id:
            errors.append(f"{file}: link {link_id} missing from target input link")

    # A link must also be referenced by both endpoint slots. This catches
    # stale ghost wires left behind after segment add/delete operations.
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for slot_index, output in enumerate(node.get("outputs") or []):
            output_links = output.get("links")
            if output_links is None:
                continue
            if not isinstance(output_links, list):
                errors.append(f"{file}: node {node.get('id')} output {slot_index} links is not an array")
                continue
            for link_id in output_links:
                link = link_by_id.get(link_id)
                if link is None:
                    errors.append(f"{file}: node {node.get('id')} output {slot_index} references missing link {link_id}")
                elif link[1] != node.get("id") or link[2] != slot_index:
                    errors.append(f"{file}: link {link_id} does not match source slot {node.get('id')}/{slot_index}")
        for slot_index, input_item in enumerate(node.get("inputs") or []):
            link_id = input_item.get("link")
            if link_id is None:
                continue
            link = link_by_id.get(link_id)
            if link is None:
                errors.append(f"{file}: node {node.get('id')} input {slot_index} references missing link {link_id}")
            elif link[3] != node.get("id") or link[4] != slot_index:
                errors.append(f"{file}: link {link_id} does not match target slot {node.get('id')}/{slot_index}")


    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type") or "")
        if node_type and node_type not in known_types and node_type not in IGNORED_NOTE_TYPES:
            mode = int(node.get("mode") or 0)
            message = f"{file}: unknown active node type {node_type!r} (node {node.get('id')})"
            if mode in (2, 4):
                warnings.append(message + " [muted]")
            else:
                errors.append(message)

    max_node = max((int(node.get("id", 0)) for node in nodes), default=0)
    max_link = max((int(link[0]) for link in links if isinstance(link, list) and link), default=0)
    if int(workflow.get("last_node_id") or 0) < max_node:
        errors.append(f"{file}: last_node_id is smaller than max node id")
    if int(workflow.get("last_link_id") or 0) < max_link:
        errors.append(f"{file}: last_link_id is smaller than max link id")


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []

    mapping, display = registry.build()
    if not mapping:
        errors.append("plugin mapping is empty")
    if set(mapping) - set(display):
        warnings.append(f"nodes without localized display names: {sorted(set(mapping) - set(display))}")

    duplicate_display = [
        name for name, count in Counter(display.values()).items() if count > 1
    ]
    if duplicate_display:
        warnings.append(f"duplicate node display names: {duplicate_display}")

    for node_id, node_class in sorted(mapping.items()):
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9_]+", node_id):
            errors.append(f"invalid node id {node_id!r}")
        if not node_id.startswith("AICG3D") and node_id not in CONDITIONAL_COMPAT_IDS:
            errors.append(
                f"{node_id}: non-namespaced production node ID is not a compatibility alias"
            )
        if node_class is None or not isinstance(node_class, type):
            errors.append(f"{node_id}: mapping is not a class")
            continue
        category = str(getattr(node_class, "CATEGORY", "") or "")
        if not category.startswith("AICG3D"):
            errors.append(f"{node_id}: category is not AICG3D-scoped: {category!r}")
        function_name = getattr(node_class, "FUNCTION", None)
        if function_name and not callable(getattr(node_class, function_name, None)):
            errors.append(f"{node_id}: FUNCTION {function_name!r} is not callable")
        return_types = getattr(node_class, "RETURN_TYPES", None)
        return_names = getattr(node_class, "RETURN_NAMES", None)
        if return_types is not None and return_names is not None:
            if len(return_types) != len(return_names):
                errors.append(f"{node_id}: RETURN_TYPES/RETURN_NAMES length mismatch")
            if len(set(return_names)) != len(return_names):
                errors.append(f"{node_id}: duplicate output names {return_names!r}")
        if hasattr(node_class, "INPUT_TYPES"):
            try:
                inputs = node_class.INPUT_TYPES()
            except Exception as exc:
                errors.append(f"{node_id}: INPUT_TYPES failed: {type(exc).__name__}: {exc}")
            else:
                if not isinstance(inputs, dict) or "required" not in inputs:
                    errors.append(f"{node_id}: INPUT_TYPES missing required section")
        elif not hasattr(node_class, "define_schema"):
            errors.append(f"{node_id}: has neither INPUT_TYPES nor define_schema")

    # Detect duplicate literal mapping keys inside this plugin.
    # A key repeated inside one dict is a real bug. The same key in separate
    # modules can be an intentional registry override and is not a collision.
    for source_file in PLUGIN_ROOT.rglob("*.py"):
        if "__pycache__" in source_file.parts:
            continue
        try:
            source = source_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(source_file))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = [str(key.value) for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
            duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
            if duplicates:
                relative = source_file.relative_to(PLUGIN_ROOT)
                errors.append(f"{relative}:{node.lineno}: duplicate literal dict keys {duplicates}")

    # Scan sibling custom-node packages for real registration collisions.
    external_keys: dict[str, set[str]] = defaultdict(set)
    for root in folder_paths.get_folder_paths("custom_nodes"):
        custom_root = Path(root)
        if not custom_root.is_dir():
            continue
        scanned = _scan_python_mapping_keys(custom_root, skip_root=PLUGIN_ROOT)
        for mapping_name, keys in scanned.items():
            external_keys[mapping_name].update(keys)
    collisions = sorted(set(mapping) & external_keys["NODE_CLASS_MAPPINGS"])
    if collisions:
        namespaced = [node_id for node_id in collisions if node_id not in CONDITIONAL_COMPAT_IDS]
        compatibility = [node_id for node_id in collisions if node_id in CONDITIONAL_COMPAT_IDS]
        if namespaced:
            errors.append(f"namespaced node id collisions with sibling custom nodes: {namespaced}")
        if compatibility:
            warnings.append(
                "conditional compatibility aliases are also registered externally: "
                f"{compatibility}; ComfyUI keeps the first registered class"
            )

    # Validate frontend extension names.
    extension_names = []
    for file in sorted((PLUGIN_ROOT / "web").glob("*.js")):
        source = file.read_text(encoding="utf-8", errors="ignore")
        if "app.queuePrompt" in source and "installRenderFullRunHook.installed" in source:
            errors.append(f"{file.name}: render queue hook uses a per-install function sentinel")
        extension_names.extend(
            re.findall(r"registerExtension\s*\(\s*\{[\s\S]{0,400}?name\s*:\s*[\"']([^\"']+)[\"']", source)
        )
    duplicate_extensions = sorted(
        name for name, count in Counter(extension_names).items() if count > 1
    )
    if duplicate_extensions:
        errors.append(f"duplicate frontend extension names: {duplicate_extensions}")
    for name in extension_names:
        if not (name.startswith("AICG3D") or name.startswith("comfyui-AICG3D")):
            warnings.append(f"frontend extension uses a non-AICG3D name: {name}")

    registry_source = (PLUGIN_ROOT / "aicg3d" / "registry.py").read_text(encoding="utf-8", errors="ignore")
    for risky in ("spec_from_file_location", "exec_module", "importlib.import_module"):
        if risky in registry_source:
            errors.append(f"registry.py contains risky cross-plugin loading API: {risky}")

    # Validate workflows against plugin + core + statically discovered mappings.
    known_types = set(mapping) | set(getattr(comfy_nodes, "NODE_CLASS_MAPPINGS", {}) or {})
    known_types.update(CORE_NODE_ALLOWLIST)
    for workflow_file in sorted((PLUGIN_ROOT / "workflows").glob("*.json")):
        _validate_workflow(workflow_file, known_types, errors, warnings)

    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print(
        f"Release audit summary: {len(mapping)} nodes, "
        f"{len(extension_names)} frontend extensions, "
        f"{len(list((PLUGIN_ROOT / 'workflows').glob('*.json')))} workflows, "
        f"{len(errors)} errors, {len(warnings)} warnings"
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
