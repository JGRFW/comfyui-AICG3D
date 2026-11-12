# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = ROOT.parents[1]
for path in (str(COMFY_ROOT), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy.final_upscale import MiniMaxH3EasyFinalHighResUpscale as Node
from aicg3d_h3easy import final_upscale, relay_vsr
from aicg3d_h3easy import nodes as base


def test_window_plan_covers_every_frame_once() -> None:
    for total_frames in (1, 38, 39, 300, 362, 363, 700, 1000, 2500):
        for max_frames in (39, 90, 362, 900):
            for overlap in (0, 4, 24, 120):
                plans = Node._window_plan(total_frames, max_frames, overlap)
                kept = [(start, end) for _decode_start, _decode_end, start, end in plans]
                assert kept[0][0] == 0
                assert kept[-1][1] == total_frames
                assert all(start < end for start, end in kept)
                assert all(left[1] == right[0] for left, right in zip(kept, kept[1:]))


def test_window_plan_reuses_context_without_mixing_output() -> None:
    plans = Node._window_plan(1000, 362, 24)
    assert len(plans) == 3
    first_decode_start, first_decode_end, first_keep_start, first_keep_end = plans[0]
    second_decode_start, _second_decode_end, second_keep_start, _second_keep_end = plans[1]
    assert first_decode_start == first_keep_start == 0
    assert first_keep_end == second_keep_start
    assert second_decode_start < first_decode_end
    assert first_keep_end <= first_decode_end


def test_exposure_lock_matches_source_luminance() -> None:
    reference = torch.full((2, 16, 16, 3), 0.25, dtype=torch.float32)
    processed = torch.full((2, 16, 16, 3), 0.28, dtype=torch.float32)
    corrected = Node._lock_exposure(processed, reference)
    luminance = (corrected[..., :3] * torch.tensor([0.2126, 0.7152, 0.0722])).sum(-1).mean()
    expected = 0.25
    assert abs(float(luminance) - expected) < 1e-3


def test_exposure_lock_preserves_frame_count() -> None:
    reference = torch.rand((7, 12, 10, 3), dtype=torch.float32)
    processed = torch.rand((7, 24, 20, 3), dtype=torch.float32)
    corrected = Node._lock_exposure(processed, reference)
    assert corrected.shape == processed.shape


def test_relay_only_reuses_one_runner_and_muxes_audio_at_the_end() -> None:
    calls = {"runner_init": [], "enhance": [], "decode": [], "write": [], "mux": []}

    class FakeRunner:
        def __init__(self, model_name, vae_name, **kwargs):
            calls["runner_init"].append((model_name, vae_name, kwargs))

        def enhance(self, frames):
            calls["enhance"].append(tuple(frames.shape))
            return frames.repeat_interleave(2, dim=1).repeat_interleave(2, dim=2)

    def decode_window(_video, start, count, _fps):
        calls["decode"].append((start, count))
        return torch.full((count, 8, 6, 3), 0.2, dtype=torch.float32)

    def write_video(frames, _fps, path):
        calls["write"].append((tuple(frames.shape), str(path)))

    def mux_audio(**kwargs):
        calls["mux"].append(kwargs)

    video = SimpleNamespace(
        get_components=lambda: None,
        get_frame_rate=lambda: 24.0,
        get_frame_count=lambda: 50,
    )
    bundle = object.__new__(base.MiniMaxH3Bundle)

    with tempfile.TemporaryDirectory(prefix="aicg3d-relay-test-") as temp_dir, patch.object(
        relay_vsr, "RelayVSRRunner", FakeRunner
    ), patch.object(
        Node, "_source_video_file", return_value=("source.mp4", 0.0, 0.0)
    ), patch.object(Node, "_decode_window", side_effect=decode_window), patch.object(
        Node, "_write_video_only", side_effect=write_video
    ), patch.object(
        Node, "_concat_video_only", return_value=Path(temp_dir, "processed.mp4")
    ), patch.object(Node, "_mux_source_audio", side_effect=mux_audio), patch.object(
        final_upscale.folder_paths, "get_temp_directory", return_value=temp_dir
    ), patch.object(
        final_upscale.folder_paths, "get_output_directory", return_value=temp_dir
    ), patch.object(
        final_upscale.folder_paths,
        "get_save_image_path",
        return_value=(temp_dir, "relay_test", 1, "", ""),
    ), patch.object(
        final_upscale.InputImpl,
        "VideoFromFile",
        side_effect=lambda path: SimpleNamespace(path=str(path)),
    ), patch.object(base, "_segment_cleanup_temp_dir"), patch.object(
        base, "_release_render_resources"
    ):
        result = Node.upscale_final_video(
            video,
            bundle,
            second_pass=False,
            latent_upscale_model="",
            repair_engine=base.PASS2_REPAIR_OFF,
            lock_source_exposure=False,
            max_window_frames=39,
            window_overlap_frames=0,
            relay_vsr_enabled=True,
            relay_vsr_model="RelayVSR/model_x2.safetensors",
            relay_vsr_vae="RelayVSR/vae_x2.safetensors",
            relay_vsr_detail=0.35,
            relay_lock_source_exposure=True,
        )

    assert calls["runner_init"] == [
        (
            "RelayVSR/model_x2.safetensors",
            "RelayVSR/vae_x2.safetensors",
            {"detail": 0.35, "lock_source_exposure": True},
        )
    ]
    assert calls["decode"] == [(0, 39), (11, 39)]
    assert calls["enhance"] == [(39, 8, 6, 3), (39, 8, 6, 3)]
    assert [shape for shape, _path in calls["write"]] == [(25, 16, 12, 3), (25, 16, 12, 3)]
    assert len(calls["mux"]) == 1
    assert calls["mux"][0]["source_path"] == "source.mp4"
    assert calls["mux"][0]["output_duration"] == 50 / 24.0
    assert "RelayVSR 开" in result["result"][2]


if __name__ == "__main__":
    test_window_plan_covers_every_frame_once()
    test_window_plan_reuses_context_without_mixing_output()
    test_exposure_lock_matches_source_luminance()
    test_exposure_lock_preserves_frame_count()
    test_relay_only_reuses_one_runner_and_muxes_audio_at_the_end()
    print("final_upscale_test: ok")
