# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline checks for the bundled Spark-TTS integration."""

from __future__ import annotations

import sys
import tempfile
import os
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def test_bundled_nodes_and_speakers_are_present() -> None:
    import aicg3d_sparktts

    assert "AICG3D_SparkTTSRun" in aicg3d_sparktts.NODE_CLASS_MAPPINGS
    assert "AICG3D_SparkTTSClone" in aicg3d_sparktts.NODE_CLASS_MAPPINGS
    assert "SparkTTSRun" in aicg3d_sparktts.LEGACY_NODE_CLASS_MAPPINGS
    assert len(aicg3d_sparktts.load_speaker_catalog()) >= 5


def test_missing_model_message_is_actionable() -> None:
    from aicg3d_sparktts.model_status import MODEL_DOWNLOAD_URL, spark_model_status

    with tempfile.TemporaryDirectory() as temp_dir:
        status = spark_model_status(Path(temp_dir))
    assert status["installed"] is False
    assert MODEL_DOWNLOAD_URL in status["message"]
    assert "Spark-TTS-0.5B" in status["message"]
    normalized = status["expected_dir"].replace("\\", "/")
    assert normalized.endswith("tts/Spark-TTS-0.5B")


def test_local_model_status_when_available() -> None:
    from aicg3d_sparktts.model_status import spark_model_status

    comfy_root = PLUGIN_ROOT.parents[1]
    status = spark_model_status(comfy_root / "models")
    assert status["speaker_count"] >= 5
    if status["installed"]:
        assert Path(status["model_dir"]).is_dir()
        assert not status["missing_files"]


def test_node_reports_missing_model_before_inference() -> None:
    from aicg3d_sparktts.builtin_node import SparkTTSRun

    previous = os.environ.get("AICG3D_SPARK_TTS_MODEL")
    previous_root = os.environ.get("COMFYUI_MODELS_DIR")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ.pop("AICG3D_SPARK_TTS_MODEL", None)
            os.environ["COMFYUI_MODELS_DIR"] = temp_dir
            try:
                SparkTTSRun().speak(
                    text="test",
                    gender="female",
                    age="Child",
                    pitch="very_high",
                    speed="moderate",
                    temperature=0.8,
                    top_k=50,
                    top_p=0.95,
                    max_new_tokens=128,
                    do_sample=True,
                    unload_model=True,
                    seed=1,
                )
            except RuntimeError as exc:
                assert "Spark-TTS-0.5B" in str(exc)
                assert "huggingface.co/SparkAudio/Spark-TTS-0.5B" in str(exc)
            else:
                raise AssertionError("missing model must fail with an actionable error")
    finally:
        if previous is None:
            os.environ.pop("AICG3D_SPARK_TTS_MODEL", None)
        else:
            os.environ["AICG3D_SPARK_TTS_MODEL"] = previous
        if previous_root is None:
            os.environ.pop("COMFYUI_MODELS_DIR", None)
        else:
            os.environ["COMFYUI_MODELS_DIR"] = previous_root




def main() -> None:
    tests = (
        test_bundled_nodes_and_speakers_are_present,
        test_missing_model_message_is_actionable,
        test_local_model_status_when_available,
        test_node_reports_missing_model_before_inference,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} bundled Spark-TTS checks")


if __name__ == "__main__":
    main()
