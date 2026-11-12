# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Static and behavior safeguards for the prompt-split batch-fill flow."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def load_prompt_module():
    path = PLUGIN_ROOT / "aicg3d" / "prompt_split.py"
    spec = importlib.util.spec_from_file_location("aicg3d_prompt_split_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_clear_button_and_global_scope_exist() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert "✕ 一键清除全部提示词" in ui
    assert "function clearAllPrompts(node)" in ui
    assert "function clearPromptValue(node)" in ui
    assert "delete node?.properties?.[H3_PROMPT_DOC_PROP]" in ui
    assert 'writeWidget(node, "global_text", "")' in ui
    assert "段落连线和生成参数保持不变" in ui
    assert 'const GLOBAL_PROMPT_TOGGLE_LABEL = "显示全局提示词";' in ui
    assert "function setGlobalPromptExpanded(node, expanded" in ui
    assert 'setGlobalPromptExpanded(node, false);' in ui
    assert "__aicg3dAutoFillTimer" not in ui


def test_silent_autofill_does_not_show_empty_errors() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert ui.count("if (options.silent !== true) notify(") >= 3


def test_fill_button_uses_only_node_text() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert "function fillSegmentsFromText(node)" in ui
    assert "fillSegmentsFromText(node);" in ui
    assert 'readWidget(node, "global_text", "")' in ui
    assert "composeSegmentPrompt(globalText, prompts[index])" in ui
    assert "navigator.clipboard" not in ui
    assert "readText()" not in ui
    assert "fillSegmentsFromClipboard" not in ui
    assert "已填 ${count} 段" not in ui
    assert "button.name = BUTTON_PREFIX;" in ui


def test_global_prompt_is_optional_and_not_duplicated() -> None:
    module = load_prompt_module()
    compose = module.compose_global_prompt

    assert compose("", "第1段剧情") == "第1段剧情"
    assert compose("  全局画风  ", "第1段剧情") == "全局画风\n\n第1段剧情"
    assert compose("全局画风", "") == "全局画风"
    assert compose("全局画风", "全局画风\n\n第1段剧情") == "全局画风\n\n第1段剧情"
    assert compose("全局", "全局设定下的第1段剧情") == "全局\n\n全局设定下的第1段剧情"


def test_global_output_is_appended_without_breaking_widget_order() -> None:
    module = load_prompt_module()
    required = module.AICG3DPromptSegmentSplit.INPUT_TYPES()["required"]
    assert list(required)[-1] == "global_text"
    assert required["global_text"][0] == "STRING"
    assert required["global_text"][1]["multiline"] is True

    node = module.AICG3DPromptSegmentSplit()
    output = node.run(
        "第1段（3秒）：女孩抬头看向门口。",
        mode=module.MODE_HEADER,
        custom_regex="",
        keep_header=False,
        seconds_mode=module.SECONDS_FROM_TEXT,
        default_seconds=5,
        auto_fill=False,
        randomize_seed=False,
        max_segments=64,
        seed_start=0,
        global_text="统一古风画风，角色参考 @图片1。",
    )
    assert output == ("统一古风画风，角色参考 @图片1。\n\n女孩抬头看向门口。",)


def test_repository_13_workflows_include_global_text_without_shifting_seed() -> None:
    import json

    workflow_paths = (
        PLUGIN_ROOT / "workflows" / "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json",
        PLUGIN_ROOT / "workflows" / "13.AICG3D_无限分段 生视频.json",
        PLUGIN_ROOT / "workflows" / "13.AICG3D_参考无限生成视频.json",
    )
    for path in workflow_paths:
        workflow = json.loads(path.read_text(encoding="utf-8"))
        nodes = [node for node in workflow["nodes"] if str(node.get("type", "")).endswith("PromptSegmentSplit")]
        assert len(nodes) == 1, path
        values = nodes[0]["widgets_values"]
        named = nodes[0]["widgets_values_named"]
        assert len(values) == 11, path
        assert values[-2] == 0, path
        assert values[-1] == "", path
        assert named.get("seed_start") == 0, path
        assert named.get("global_text") == "", path


def main() -> None:
    tests = (
        test_clear_button_and_global_scope_exist,
        test_silent_autofill_does_not_show_empty_errors,
        test_fill_button_uses_only_node_text,
        test_global_prompt_is_optional_and_not_duplicated,
        test_global_output_is_appended_without_breaking_widget_order,
        test_repository_13_workflows_include_global_text_without_shifting_seed,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} prompt split checks")


if __name__ == "__main__":
    main()
