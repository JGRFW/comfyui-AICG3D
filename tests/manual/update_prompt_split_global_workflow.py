# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Add the prompt-split global_text widget without shifting legacy values."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PARSER_TYPES = {"AICG3D_H3PromptSegmentSplit", "AICG3DPromptSegmentSplit"}


def migrate(path: Path) -> list[dict]:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    changed = []
    for node in workflow.get("nodes", []):
        if node.get("type") not in PARSER_TYPES:
            continue
        values = node.setdefault("widgets_values", [])
        before = len(values)
        if before == 9:
            values.extend([0, ""])
        elif before == 10:
            values.append("")
        elif before == 11:
            if not isinstance(values[-1], str):
                raise ValueError(f"{path}: global_text is not a string in node {node.get('id')}")
        else:
            raise ValueError(
                f"{path}: node {node.get('id')} has {before} widget values; expected 9, 10, or 11"
            )

        named = node.get("widgets_values_named")
        if isinstance(named, dict):
            if before == 9:
                named.setdefault("seed_start", 0)
            named.setdefault("global_text", "")

        changed.append({"id": node.get("id"), "before": before, "after": len(values)})

    if not changed:
        raise ValueError(f"{path}: prompt-split node not found")
    path.write_text(
        json.dumps(workflow, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )
    return changed


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: update_prompt_split_global_workflow.py WORKFLOW.json [...]")
    for raw_path in sys.argv[1:]:
        path = Path(raw_path)
        changed = migrate(path)
        print(f"PASS {path}: {json.dumps(changed, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
