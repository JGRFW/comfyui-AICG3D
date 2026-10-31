# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: Apache-2.0
"""Bundled Spark-TTS integration for comfyui-AICG3D."""
from __future__ import annotations

from aicg3d_sparktts.model_status import (
    MODEL_DOWNLOAD_URL,
    find_model_dir,
    find_speaker_dir,
    load_speaker_catalog,
    spark_model_status,
)
from aicg3d_sparktts.builtin_node import (
    LEGACY_NODE_CLASS_MAPPINGS,
    LEGACY_NODE_DISPLAY_NAME_MAPPINGS,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

__all__ = [
    "LEGACY_NODE_CLASS_MAPPINGS",
    "LEGACY_NODE_DISPLAY_NAME_MAPPINGS",
    "MODEL_DOWNLOAD_URL",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "find_model_dir",
    "find_speaker_dir",
    "load_speaker_catalog",
    "spark_model_status",
]
