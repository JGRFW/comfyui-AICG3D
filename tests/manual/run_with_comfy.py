# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a manual test with both ComfyUI and the plugin on sys.path."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(PLUGIN_ROOT), str(COMFY_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

if len(sys.argv) != 2:
    raise SystemExit("usage: run_with_comfy.py <test-script>")
runpy.run_path(sys.argv[1], run_name="__main__")
