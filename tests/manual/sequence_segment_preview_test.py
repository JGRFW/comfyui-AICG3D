# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify the internal staged VIDEO decoding used by infinite-sequence previews."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = PLUGIN_ROOT.parents[1]
for path in (str(COMFY_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from aicg3d_h3easy import nodes as h3_nodes  # noqa: E402
from aicg3d_h3easy.nodes import (  # noqa: E402
    MiniMaxH3EasySequenceSegment,
    MiniMaxH3SegmentSample,
    MiniMaxH3SequenceConfig,
    MiniMaxH3SequenceSegment,
)


class FakeVAEDecode:
    def decode(self, _vae, latent):
        video, _audio = h3_nodes._segment_latent_streams(latent)
        assert video.shape == (1, 24, 2, 4, 8)
        frames = torch.arange(20, dtype=torch.float32).reshape(20, 1, 1, 1)
        return (frames.repeat(1, 8, 8, 3),)


def main() -> None:
    assert MiniMaxH3EasySequenceSegment.RETURN_TYPES == ("MINIMAX_H3_SEQUENCE_SEGMENT",)
    assert MiniMaxH3EasySequenceSegment.RETURN_NAMES == ("segment",)
    required = MiniMaxH3EasySequenceSegment.INPUT_TYPES()["required"]
    assert "emit_segment_video" not in required
    assert "emit_first_pass_video" not in required

    sample = MiniMaxH3SegmentSample(
        video_latent=torch.zeros((1, 24, 2, 4, 8)),
        audio_latent=torch.zeros((1, 32, 2, 1)),
        head_frames=5,
        delivery_frames=10,
        output_frames=10,
    )
    config = SimpleNamespace(
        fps=24,
        bundle=SimpleNamespace(video_vae=object(), audio_vae=object()),
    )
    result = MiniMaxH3SequenceSegment(
        config=config,
        sample=sample,
        index=2,
        previous=None,
        timeline_start=0,
        source_audio=None,
        voice_cast=None,
        cache_scope="test",
        chain_key="test-chain",
        node_id="74",
        first_pass_sample=sample,
    )

    with (
        patch.object(h3_nodes.nodes, "VAEDecode", FakeVAEDecode),
        patch.object(
            h3_nodes.nodes_audio,
            "vae_decode_audio",
            return_value={"waveform": torch.zeros((1, 1, 1000)), "sample_rate": 24000},
        ),
    ):
        video = MiniMaxH3EasySequenceSegment._deliver_video(config, result)
        first_pass_video = MiniMaxH3EasySequenceSegment._deliver_first_pass_video(config, result)

    components = video.get_components()
    assert components.images.shape[0] == 10
    assert torch.equal(components.images[0, 0, 0, :1], torch.tensor([5.0]))
    assert torch.equal(components.images[-1, 0, 0, :1], torch.tensor([14.0]))
    assert components.audio is not None
    first_pass_components = first_pass_video.get_components()
    assert first_pass_components.images.shape[0] == 10
    assert first_pass_components.audio is not None
    print("Sequence segment staged preview decoding: ok")


if __name__ == "__main__":
    main()
