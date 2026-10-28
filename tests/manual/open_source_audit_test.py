# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Release-safety regressions for node IDs, categories, secrets, and path handling."""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
import tempfile

import folder_paths


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def test_node_categories_and_integration_registration() -> None:
    from aicg3d.branding import CATEGORY_H3, CATEGORY_INTEGRATION, CATEGORY_TEXT, category_for
    from aicg3d.registry import build

    assert category_for("AICG3D_H3Loader") == CATEGORY_H3
    assert category_for("AICG3D_H3PromptSegmentSplit") == CATEGORY_TEXT
    assert category_for("AICG3D_H3IntegrationGH") == CATEGORY_INTEGRATION

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
        "draw_previous_index",
    ):
        assert name in optional, name

    ui = (PLUGIN_ROOT / "web" / "minimax_h3_easy_ui_v4.js").read_text(encoding="utf-8")
    assert "const sequenceDrawTargetNodes = new Map()" in ui
    assert 'sequencePromptNode.inputs.previous_segment = "__aicg3d_cached_previous__"' in ui
    assert "queueNodeIds: [node.id]" in ui


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
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} open-source audit checks")


if __name__ == "__main__":
    main()
