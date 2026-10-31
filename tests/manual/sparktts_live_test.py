# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
"""Live smoke test for the bundled Spark-TTS node."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
os.environ.setdefault("COMFYUI_MODELS_DIR", str(COMFY_ROOT / "models"))


def main() -> None:
    import numpy as np
    import soundfile as sf

    from aicg3d_sparktts import spark_model_status
    from aicg3d_sparktts.builtin_node import SparkTTSRun

    status = spark_model_status()
    if not status["installed"]:
        raise RuntimeError(status["message"])
    result = SparkTTSRun().speak(
        text="你好，这是 AICG3D 内置声线测试。",
        gender="female",
        age="Child",
        pitch="very_high",
        speed="moderate",
        temperature=0.8,
        top_k=50,
        top_p=0.95,
        max_new_tokens=600,
        do_sample=True,
        unload_model=True,
        seed=20261031,
    )
    audio = result[0]
    waveform = audio["waveform"].detach().cpu().float().numpy().squeeze()
    sample_rate = int(audio["sample_rate"])
    rms = float(np.sqrt(np.mean(np.square(waveform))))
    if waveform.size == 0 or rms < 1e-4:
        raise RuntimeError(f"Spark-TTS generated invalid audio: rms={rms}")
    output = COMFY_ROOT / "output" / "audio" / "aicg3d_sparktts_verify.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, waveform, sample_rate, subtype="PCM_16")
    print(f"PASS model={status['model_dir']}")
    print(f"PASS samples={waveform.size} sample_rate={sample_rate} rms={rms:.5f}")
    print(f"PASS output={output}")


if __name__ == "__main__":
    main()
