# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Static safeguards for the prompt-split clear-all action."""

from __future__ import annotations

from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def test_clear_button_and_safe_scope_exist() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert "✕ 一键清除全部提示词" in ui
    assert "function clearAllPrompts(node)" in ui
    assert "function clearPromptValue(node)" in ui
    assert "delete node?.properties?.[H3_PROMPT_DOC_PROP]" in ui
    assert "setButtonLabel(node, 0)" in ui
    assert "段落连线和生成参数保持不变" in ui
    assert "clearTimeout(node.__aicg3dAutoFillTimer)" in ui


def test_silent_autofill_does_not_show_empty_errors() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert ui.count('if (options.silent !== true) notify(') >= 3


def test_fill_button_reads_clipboard_before_batch_fill() -> None:
    ui = (PLUGIN_ROOT / "web" / "aicg3d_prompt_split.js").read_text(encoding="utf-8")
    assert "async function fillSegmentsFromClipboard(node)" in ui
    assert "navigator.clipboard.readText()" in ui
    assert "fillSegmentsFromClipboard(node);" in ui
    assert 'source: "clipboard"' in ui
    assert "取消文本框上一次还没执行的自动填入" in ui
    assert "请允许浏览器剪贴板权限" in ui


def main() -> None:
    tests = (
        test_clear_button_and_safe_scope_exist,
        test_silent_autofill_does_not_show_empty_errors,
        test_fill_button_reads_clipboard_before_batch_fill,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} prompt split clear checks")


if __name__ == "__main__":
    main()
