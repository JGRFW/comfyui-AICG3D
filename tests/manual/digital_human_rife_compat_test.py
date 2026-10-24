"""Manual regression test for legacy digital-human RIFE widget values.

Run from the ComfyUI root:
    python custom_nodes/comfyui-AICG3D/tests/manual/digital_human_rife_compat_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
sys.path.insert(0, str(COMFY_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT))

from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3Easy,
    _normalize_digital_human_rife_settings,
)


def main() -> None:
    expected = {
        "enabled": True,
        "model": "rife47.pth",
        "multiplier": 4,
        "fast_mode": True,
        "ensemble": True,
        "clear_cache": 10,
    }
    legacy = {
        "digital_human_rife": True,
        "digital_human_rife_model": 1,
        "digital_human_rife_multiplier": 1,
        "digital_human_rife_clear_cache": True,
    }
    valid = {
        "digital_human_rife": True,
        "digital_human_rife_model": "rife47.pth",
        "digital_human_rife_multiplier": 4,
        "digital_human_rife_clear_cache": 10,
    }

    assert _normalize_digital_human_rife_settings(legacy) == expected
    assert _normalize_digital_human_rife_settings(valid) == expected
    assert MiniMaxH3Easy.VALIDATE_INPUTS(1, 1, True) is True
    print("digital-human RIFE compatibility: ok")


if __name__ == "__main__":
    main()
