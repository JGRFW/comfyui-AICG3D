# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Release-safety regressions for node IDs, categories, secrets, and path handling."""

from __future__ import annotations

import asyncio
import ast
import json
import sys
import os
from collections import Counter
from pathlib import Path
import tempfile

import folder_paths


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def test_node_categories_and_integration_registration() -> None:
    from aicg3d.branding import CATEGORY_H3, CATEGORY_INTEGRATION, CATEGORY_TEXT, category_for
    from aicg3d.registry import build
    from aicg3d.branding import CATEGORY_VOICE

    assert category_for("AICG3D_H3Loader") == CATEGORY_H3
    assert category_for("AICG3D_H3PromptSegmentSplit") == CATEGORY_TEXT
    assert category_for("AICG3D_H3IntegrationGH") == CATEGORY_INTEGRATION
    assert category_for("AICG3D_SparkTTSRun") == CATEGORY_VOICE

    mapping, _display = build()
    assert "AICG3D_H3Loader" in mapping
    assert "AICG3D_H3PromptSegmentSplit" in mapping
    assert "AICG3D_H3IntegrationGH" in mapping
    assert "MiniMaxH3IntegrationGH" not in mapping
    assert mapping["AICG3D_H3Loader"].CATEGORY == CATEGORY_H3
    assert mapping["AICG3D_H3IntegrationGH"].CATEGORY == CATEGORY_INTEGRATION


def test_optimizer_config_is_stored_outside_checkout() -> None:
    import aicg3d_h3easy.nodes as nodes_mod

    original = folder_paths.get_user_directory
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder_paths.get_user_directory = lambda: temp_dir
            target = Path(nodes_mod._prompt_optimizer_config_path())
            assert not target.is_relative_to(PLUGIN_ROOT)
            payload = nodes_mod._normalize_prompt_optimizer_config({
                "mode": "api",
                "api_url": "https://example.invalid/v1",
                "api_key": "audit-secret",
                "model": "audit-model",
            })
            nodes_mod._write_prompt_optimizer_config(payload)
            assert target.is_file()
            assert json.loads(target.read_text(encoding="utf-8"))["api_key"] == "audit-secret"
    finally:
        folder_paths.get_user_directory = original


def test_goohai_config_redacts_api_key() -> None:
    import aicg3d_h3goohai.prompt_optimizer as optimizer

    original_path = optimizer._config_path
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "config.json"
            optimizer._config_path = lambda: target
            stored = optimizer._write_stored_config({**optimizer.DEFAULT_CONFIG, "api_key": "audit-secret"})
            assert stored["api_key"] == "audit-secret"
            public = optimizer._public_config(optimizer._read_stored_config())
            assert "api_key" not in public
            assert public["has_api_key"] is True
    finally:
        optimizer._config_path = original_path


def test_input_file_resolution_rejects_escape() -> None:
    import aicg3d_h3goohai.prompt_optimizer as optimizer

    original_input = folder_paths.get_input_directory
    original_annotated = folder_paths.get_annotated_filepath
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder_paths.get_input_directory = lambda: temp_dir
            folder_paths.get_annotated_filepath = lambda value, *args, **kwargs: os.path.join(temp_dir, value)
            safe = Path(temp_dir) / "safe.png"
            safe.write_bytes(b"test")
            assert optimizer._resolve_input_file("safe.png") == safe.resolve()
            for invalid in ("../outside.png", "nested/../../outside.png", "/etc/passwd"):
                try:
                    optimizer._resolve_input_file(invalid)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"Unsafe input path accepted: {invalid}")
    finally:
        folder_paths.get_input_directory = original_input
        folder_paths.get_annotated_filepath = original_annotated


def test_frontend_globals_are_namespaced() -> None:
    ui = (PLUGIN_ROOT / "web" / "minimax_h3_easy_ui_v4.js").read_text(encoding="utf-8")
    integration = (PLUGIN_ROOT / "web" / "minimax_h3_integration.js").read_text(encoding="utf-8")
    assert "__AICG3D_H3_PROMPT_UNDO_SHIELD_INSTALLED" in ui
    assert "__AICG3D_H3_PROMPT_PROCESS_KEY_PATCHED" not in ui
    assert ui.count("proto.processKey = function") == 1
    assert "__H3_PROMPT_UNDO_SHIELD_INSTALLED" not in ui
    assert "__H3_PROMPT_PROCESS_KEY_PATCHED" not in ui
    assert "optimizer: optimizerForWorkflow(optimizerSettings)" in integration
    assert "beforeConfigureGraph" in integration
    assert "MiniMaxH3IntegrationGH" in integration


def test_manager_legacy_node_ids_are_registered() -> None:
    from aicg3d.registry import _LEGACY_H3_COMPAT_IDS, build

    mapping, _display = build()
    for node_id in _LEGACY_H3_COMPAT_IDS:
        assert node_id in mapping, node_id
    assert "AICG3DPromptSegmentSplit" in mapping
    assert "AICG3D_H3PromptSegmentSplit" in mapping
    assert "AICG3D_SparkTTSRun" in mapping
    assert "AICG3D_SparkTTSClone" in mapping


def test_media_picker_and_nodes2_mode_guards() -> None:
    ui = (PLUGIN_ROOT / "web" / "minimax_h3_easy_ui_v4.js").read_text(encoding="utf-8")
    assert "function openMediaLoaderFilePicker" in ui
    assert "input.className = \"h3-media-loader-file-input\"" in ui
    assert "document.body.append(input)" in ui
    assert "if (inlinePanel && isVueNodesMode())" in ui


def test_sequence_draw_uses_cached_previous_contract() -> None:
    from aicg3d_h3easy.nodes import MiniMaxH3EasySequenceSegment

    optional = MiniMaxH3EasySequenceSegment.INPUT_TYPES().get("optional", {})
    for name in (
        "draw_previous_from_cache",
        "draw_previous_scope",
        "draw_previous_chain_key",
        "draw_previous_node_id",
        "draw_previous_index",
    ):
        assert name in optional, name

    ui = (PLUGIN_ROOT / "web" / "minimax_h3_easy_ui_v4.js").read_text(encoding="utf-8")
    assert "const sequenceDrawTargetNodes = new Map()" in ui
    assert 'sequencePromptNode.inputs.previous_segment = "__aicg3d_cached_previous__"' in ui
    assert "queueNodeIds: [String(node.id)]" in ui
    assert "function sequenceEffectiveChain(tail)" in ui
    assert "cache_segment_nodes" in ui
    assert "...cacheOnlyIds.flatMap((id) => sequenceNodeIdList" in ui
    assert "scheduleNextSequenceCleanupPrompt" in ui


def test_no_private_module_injection() -> None:
    source = (PLUGIN_ROOT / "aicg3d_h3easy" / "character_motion.py").read_text(encoding="utf-8")
    assert "sys.modules[" not in source
    assert "importlib.import_module" not in source
    assert "_registered_node_class(\"ModelPreviewOverrideKJ\")" in source


def test_jpeg_payload_is_a_valid_data_url() -> None:
    from PIL import Image
    from aicg3d_h3goohai import prompt_optimizer

    payload = prompt_optimizer._downscaled_jpeg(Image.new("RGB", (8, 8), "black"))
    assert payload.startswith("data:" + "image/jpeg;base64,")
    assert payload.split(",", 1)[1]


def test_project_version_and_display_names_are_release_safe() -> None:
    import re

    import aicg3d.routes as routes
    from aicg3d.registry import build

    pyproject = (PLUGIN_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_table = pyproject.split("[project]", 1)[-1]
    match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', project_table)
    assert match is not None
    assert routes.VERSION == match.group(1)

    mapping, display = build()
    assert set(mapping) == set(display)
    duplicates = [name for name, count in Counter(display.values()).items() if count > 1]
    assert not duplicates, duplicates


def test_optional_runtime_dependencies_are_not_top_level_hard_imports() -> None:
    def top_level_imports(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, ast.Import):
                names.update(alias.name.split(".", 1)[0] for alias in statement.names)
            elif isinstance(statement, ast.ImportFrom) and statement.module:
                names.add(statement.module.split(".", 1)[0])
        return names

    nodes_imports = top_level_imports(PLUGIN_ROOT / "aicg3d_h3easy" / "nodes.py")
    motion_imports = top_level_imports(PLUGIN_ROOT / "aicg3d_h3easy" / "character_motion.py")
    assert "requests" not in nodes_imports
    assert "psutil" not in nodes_imports
    assert "psutil" not in motion_imports


def test_sequence_helper_bodies_and_cleanup_boundaries() -> None:
    import aicg3d_h3easy.nodes as nodes_mod

    source = (PLUGIN_ROOT / "aicg3d_h3easy" / "nodes.py").read_text(encoding="utf-8")
    assert source.count("def _sequence_fit_frame(") == 1

    original_temp = nodes_mod.folder_paths.get_temp_directory
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir) / "comfy-temp"
            outside_root = Path(temp_dir) / "outside"
            temp_root.mkdir()
            outside_root.mkdir()
            safe = temp_root / "minimax_h3_segments_safe"
            wrong_prefix = temp_root / "unrelated_directory"
            nested = temp_root / "nested" / "minimax_h3_segments_nested"
            outside = outside_root / "minimax_h3_segments_outside"
            for directory in (safe, wrong_prefix, nested, outside):
                directory.mkdir(parents=True)

            nodes_mod.folder_paths.get_temp_directory = lambda: str(temp_root)
            nodes_mod._segment_cleanup_temp_dir(str(safe))
            nodes_mod._segment_cleanup_temp_dir(str(wrong_prefix))
            nodes_mod._segment_cleanup_temp_dir(str(nested))
            nodes_mod._segment_cleanup_temp_dir(str(outside))

            assert not safe.exists()
            assert wrong_prefix.exists()
            assert nested.exists()
            assert outside.exists()

            removable = temp_root / "AICG3D_segment_001.mp4"
            wrong_suffix = temp_root / "AICG3D_segment_002.txt"
            arbitrary = temp_root / "important.mp4"
            removable.write_bytes(b"segment")
            wrong_suffix.write_bytes(b"not a segment")
            arbitrary.write_bytes(b"keep")
            deleted, failed = nodes_mod._sequence_delete_files(
                [str(removable), str(wrong_suffix), str(arbitrary)]
            )
            assert (deleted, failed) == (1, 0)
            assert not removable.exists()
            assert wrong_suffix.exists()
            assert arbitrary.exists()
    finally:
        nodes_mod.folder_paths.get_temp_directory = original_temp


def test_route_and_frontend_patches_are_idempotent() -> None:
    from types import SimpleNamespace

    from server import PromptServer

    import aicg3d.routes as routes
    import aicg3d_h3easy.nodes as nodes_mod
    from aicg3d_h3goohai import prompt_optimizer as goohai_optimizer

    class FakeRoutes:
        def __init__(self) -> None:
            self.items: list[tuple[str, str]] = []
            self.handlers: dict[tuple[str, str], object] = {}

        def get(self, path: str):
            def register(handler):
                self.items.append(("GET", path))
                self.handlers[("GET", path)] = handler
                return handler

            return register

        def post(self, path: str):
            def register(handler):
                self.items.append(("POST", path))
                self.handlers[("POST", path)] = handler
                return handler

            return register

    had_instance = hasattr(PromptServer, "instance")
    original_instance = getattr(PromptServer, "instance", None)
    original_routes_registered = routes._REGISTERED
    original_optimizer_registered = getattr(nodes_mod._register_prompt_optimizer_route, "_registered", False)
    original_goohai_registered = goohai_optimizer._ROUTES_REGISTERED
    fake_routes = FakeRoutes()
    try:
        PromptServer.instance = SimpleNamespace(routes=fake_routes)
        routes._REGISTERED = False
        nodes_mod._register_prompt_optimizer_route._registered = False
        goohai_optimizer._ROUTES_REGISTERED = False

        assert routes.register_routes() is True
        core_route_count = len(fake_routes.items)
        assert core_route_count > 0
        assert routes.register_routes() is True
        assert len(fake_routes.items) == core_route_count

        assert nodes_mod._register_prompt_optimizer_route() is True
        optimizer_route_count = len(fake_routes.items)
        assert optimizer_route_count > core_route_count
        assert nodes_mod._register_prompt_optimizer_route() is True
        assert len(fake_routes.items) == optimizer_route_count

        class MalformedJsonRequest:
            async def json(self):
                raise ValueError("invalid JSON")

        for path in (
            "/aicg3d/h3easy/prompt-optimize",
            "/aicg3d/h3easy/sequence/cleanup-segments",
        ):
            response = asyncio.run(fake_routes.handlers[("POST", path)](MalformedJsonRequest()))
            assert response.status == 400
            assert "有效 JSON" in json.loads(response.body.decode("utf-8"))["error"]
    finally:
        if had_instance:
            PromptServer.instance = original_instance
        else:
            delattr(PromptServer, "instance")
        routes._REGISTERED = original_routes_registered
        nodes_mod._register_prompt_optimizer_route._registered = original_optimizer_registered
        goohai_optimizer._ROUTES_REGISTERED = original_goohai_registered

    ui = (PLUGIN_ROOT / "web" / "minimax_h3_easy_ui_v4.js").read_text(encoding="utf-8")
    integration = (PLUGIN_ROOT / "web" / "minimax_h3_integration.js").read_text(encoding="utf-8")
    bridge = (PLUGIN_ROOT / "web" / "aicg3d_voice_bridge_v1.js").read_text(encoding="utf-8")
    assert "if (sequenceQueueHookInstalled || typeof app.queuePrompt" in ui
    assert "if (renderFullRunQueueHookInstalled || typeof app.queuePrompt" in ui
    assert "if (autoOptimizerQueueInstalled || typeof app.queuePrompt" in integration
    assert "if (globalThis[PATCH_FLAG] || typeof app.graphToPrompt" in bridge


def main() -> None:
    tests = (
        test_node_categories_and_integration_registration,
        test_optimizer_config_is_stored_outside_checkout,
        test_goohai_config_redacts_api_key,
        test_input_file_resolution_rejects_escape,
        test_frontend_globals_are_namespaced,
        test_no_private_module_injection,
        test_manager_legacy_node_ids_are_registered,
        test_media_picker_and_nodes2_mode_guards,
        test_sequence_draw_uses_cached_previous_contract,
        test_jpeg_payload_is_a_valid_data_url,
        test_project_version_and_display_names_are_release_safe,
        test_optional_runtime_dependencies_are_not_top_level_hard_imports,
        test_sequence_helper_bodies_and_cleanup_boundaries,
        test_route_and_frontend_patches_are_idempotent,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} open-source audit checks")


if __name__ == "__main__":
    main()
