# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
# 本模块为新增代码（整合三个来源插件）

# -*- coding: utf-8 -*-
"""AICG3D 自有节点：统一的技能调用入口。"""
from __future__ import annotations

from . import branding, skills

AUTO = skills.AUTO_SKILL


def _choices() -> list[str]:
    return [AUTO] + [f'{item["name"]} [{item["id"]}]' for item in skills.discover()]


class AICG3DSkillLoader:
    """把一个 Skill 的完整创作规范转成可直接连线的提示词文本。"""

    CATEGORY = branding.CATEGORY_TEXT
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("提示词", "技能ID", "技能正文")
    DESCRIPTION = "选择 Skill 后输出规范正文，并把你的任务描述拼成一条完整提示词，可直接接到 H3 主节点或对话节点。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "skill": (
                    _choices(),
                    {
                        "default": AUTO,
                        "tooltip": "自动选择：不下发技能正文，由下游 LLM 自行挑选（配合多轮对话节点使用）。",
                    },
                ),
                "task": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "default": "",
                        "tooltip": "你的创作需求。留空时只输出技能正文。",
                    },
                ),
            },
            "optional": {
                "task_override": ("STRING", {"forceInput": True, "tooltip": "从上游节点覆盖任务描述"}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return False

    def run(self, skill, task, task_override=None):
        idea = str(task_override or task or "").strip()
        selected = skills.get(str(skill or ""))
        if selected is None:
            return (idea, "", "")
        body = skills.read_body(selected)
        composed = idea
        if body.strip():
            header = f'===== 技能：{selected["name"]} ({selected["id"]}) ====='
            composed = f"{header}\n{body}\n\n===== 任务 =====\n{idea}" if idea else f"{header}\n{body}"
        return (composed, selected["id"], body)


class AICG3DPromptPreset:
    """选择提示词模板，把模板正文和你的任务拼成一条可直接使用的提示词。"""

    CATEGORY = branding.CATEGORY_TEXT
    FUNCTION = "run"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("提示词", "模板ID", "模板正文")
    DESCRIPTION = (
        "从插件模板库（prompt_presets/）里挑一条提示词模板，输出模板正文；"
        "填了任务描述时会拼成“模板 + 任务”的完整提示词，可直接接到 H3 主节点或对话节点。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        choices = [item["label"] for item in skills.discover_presets()]
        return {
            "required": {
                "preset": (
                    choices,
                    {
                        "default": choices[0] if choices else "",
                        "tooltip": "“分类｜名称”格式，输入关键字可快速过滤。",
                    },
                ),
                "task": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "default": "",
                        "tooltip": "你的创作需求。留空时只输出模板正文。",
                    },
                ),
            },
            "optional": {
                "task_override": ("STRING", {"forceInput": True, "tooltip": "从上游节点覆盖任务描述"}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return False

    def run(self, preset, task, task_override=None):
        idea = str(task_override or task or "").strip()
        selected = skills.get(str(preset or ""))
        if selected is None or selected.get("kind") != "preset":
            return (idea, "", "")
        body = skills.read_body(selected)
        header = f'===== 提示词模板：{selected["name"]}（{selected["category_name"]}）====='
        composed = f"{header}\n{body}" if not idea else f"{header}\n{body}\n\n===== 任务 =====\n{idea}"
        return (composed, selected["id"], body)


NODE_CLASS_MAPPINGS = {
    "AICG3D_SkillLoader": AICG3DSkillLoader,
    "AICG3D_PromptPreset": AICG3DPromptPreset,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AICG3D_SkillLoader": "AICG3D 技能加载器",
    "AICG3D_PromptPreset": "AICG3D 提示词模板",
}
