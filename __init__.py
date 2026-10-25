# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import traceback


def _safe_log(message=""):
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe)


plugin_dir = os.path.dirname(os.path.abspath(__file__))
path_was_added = plugin_dir not in sys.path
if path_was_added:
    # Absolute imports are used during package initialization. Keep the path
    # only for this load and remove it afterwards so other plugins cannot be
    # shadowed by whatever files happen to be in this directory.
    sys.path.insert(0, plugin_dir)

try:
    import aicg3d.registry as registry
    res = registry.build()
    NODE_CLASS_MAPPINGS = res[0]
    NODE_DISPLAY_NAME_MAPPINGS = res[1]
    WEB_DIRECTORY = "./web"
    _safe_log("\n" + "!" * 60)
    _safe_log("\n" + "=" * 50 + "\n")
    _safe_log("[AICG3D-Integrated] System Initialized")
    _safe_log("Namespace: AICG3D_H3_ (Conflict-Free Mode)")
    _safe_log(f"Loaded {len(NODE_CLASS_MAPPINGS)} production-ready nodes")
    _safe_log("=" * 50 + "\n")
    _safe_log("!" * 60 + "\n")
except Exception:
    _safe_log("\n" + "=" * 60)
    _safe_log("[AICG3D] FATAL ERROR LOADING PLUGIN:")
    _safe_log(traceback.format_exc())
    _safe_log("=" * 60 + "\n")
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    # Avoid loading a half-initialized frontend after a backend failure.
    WEB_DIRECTORY = None
finally:
    if path_was_added:
        try:
            sys.path.remove(plugin_dir)
        except ValueError:
            pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
