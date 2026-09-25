# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import traceback

# 强制将插件根目录加入 sys.path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

try:
    # 绝对导入
    import aicg3d.registry as registry
    res = registry.build()
    NODE_CLASS_MAPPINGS = res[0]
    NODE_DISPLAY_NAME_MAPPINGS = res[1]
    WEB_DIRECTORY = "./web"
    print("\n" + "!"*60)
    print(f"[AICG3D] SUCCESS: Loaded {len(NODE_CLASS_MAPPINGS)} nodes!")
    print("!"*60 + "\n")
except Exception as e:
    print("\n" + "="*60)
    print("[AICG3D] FATAL ERROR LOADING PLUGIN:")
    traceback.print_exc()
    print("="*60 + "\n")
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
