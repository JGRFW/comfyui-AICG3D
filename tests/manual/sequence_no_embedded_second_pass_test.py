# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify the Smart Drama node has no embedded second-pass upscale stage."""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import fields
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3EasySequenceGlobal,
    MiniMaxH3SequenceConfig,
)


SECOND_PASS_WIDGETS = {
    "second_pass",
    "second_pass_model",
    "second_pass_scale",
    "second_pass_sampler_name",
    "second_pass_scheduler",
    "second_pass_steps",
    "second_pass_denoise",
}


def main() -> None:
    required = MiniMaxH3EasySequenceGlobal.INPUT_TYPES()["required"]
    assert SECOND_PASS_WIDGETS.isdisjoint(required), (
        "Smart Drama must not expose the embedded second-pass controls"
    )

    build_parameters = set(inspect.signature(MiniMaxH3EasySequenceGlobal.build_config).parameters)
    assert SECOND_PASS_WIDGETS.isdisjoint(build_parameters), (
        "Smart Drama must not accept embedded second-pass execution arguments"
    )

    config_fields = {field.name for field in fields(MiniMaxH3SequenceConfig)}
    assert SECOND_PASS_WIDGETS.isdisjoint(config_fields), (
        "Smart Drama sequence config must not carry per-segment second-pass state"
    )

    workflow_path = (
        PLUGIN_ROOT
        / "workflows"
        / "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json"
    )
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    node = next(
        item for item in workflow["nodes"]
        if item.get("type") == "AICG3D_H3SequenceGlobal"
    )
    named = node.get("widgets_values_named") or {}
    assert SECOND_PASS_WIDGETS.isdisjoint(named), (
        "The 13 workflow must remain free of embedded Smart Drama second-pass values"
    )

    print("Smart Drama embedded second pass removed: ok")


if __name__ == "__main__":
    main()
