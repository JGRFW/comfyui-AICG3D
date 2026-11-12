# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later

"""Apply the RelayVSR workflow migration to local workflows and repo copies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
COMFY_ROOT = ROOT.parents[1]
WORKFLOW_DIR = COMFY_ROOT / "user" / "default" / "workflows"

RELAY_MODEL = "RelayVSR\\relayvsr_x2_lightx2v_int8_convrot.safetensors"
RELAY_VAE = "RelayVSR\\relayvsr_flash_vae_x2_fp32.safetensors"
RELAY_DEFAULTS = [False, RELAY_MODEL, RELAY_VAE, 0.5, True]
RELAY_NAMED = {
    "relay_vsr_enabled": False,
    "relay_vsr_model": RELAY_MODEL,
    "relay_vsr_vae": RELAY_VAE,
    "relay_vsr_detail": 0.5,
    "relay_lock_source_exposure": True,
}
FINAL_SEQUENCE_TYPE = "MINIMAX_H3_FINAL_SEQUENCE"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, workflow: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _find_node(workflow: dict[str, Any], node_id: int) -> dict[str, Any] | None:
    for node in workflow.get("nodes", []):
        if int(node.get("id", -1)) == node_id:
            return node
    return None


def _append_relay_values(node: dict[str, Any]) -> bool:
    values = node.setdefault("widgets_values", [])
    named = node.setdefault("widgets_values_named", {})
    changed = False
    if "relay_vsr_enabled" not in named:
        values.extend(RELAY_DEFAULTS)
        named.update(RELAY_NAMED)
        changed = True
    return changed


def update_render_workflow(path: Path) -> bool:
    if not path.is_file():
        return False
    workflow = _read(path)
    node = _find_node(workflow, 945)
    if not node or node.get("type") != "AICG3D_H3RenderAdvancedWithModel":
        raise RuntimeError(f"{path}: node 945 is not the advanced renderer")
    changed = _append_relay_values(node)
    if changed:
        _write(path, workflow)
    return changed


def _packed_values() -> list[Any]:
    return [
        "video/MiniMax_H3_Final_HD",
        True,
        "none",
        False,
        "minimax_h3_latent_upscaler_3d_fp16_V2.safetensors",
        "按倍数放大",
        1.5,
        1920,
        1088,
        "cuda",
        "fp16",
        "er_sde",
        "beta",
        4,
        0.3,
        888888,
        "fixed",
        "关",
        512,
        512,
        128,
        32,
        "关闭（仅 H3 二采）",
        "自动选择",
        1,
        5,
        2,
        "lab",
        "ULTRA",
        "cuda",
        0,
        "cpu",
        True,
        True,
        362,
        24,
        "关",
        1,
        "卸载模型",
        *RELAY_DEFAULTS,
    ]


def _packed_named() -> dict[str, Any]:
    return {
        "filename_prefix": "video/MiniMax_H3_Final_HD",
        "second_pass": True,
        "latent_upscale_model": "minimax_h3_latent_upscaler_3d_fp16_V2.safetensors",
        "upscale_mode": "按倍数放大",
        "upscale_scale": 1.5,
        "target_width": 1920,
        "target_height": 1088,
        "upscale_device": "cuda",
        "upscale_precision": "fp16",
        "sampler_name": "er_sde",
        "scheduler": "beta",
        "steps": 4,
        "second_pass_denoise": 0.3,
        "second_pass_seed": 888888,
        "control_after_generate": "fixed",
        "tiled_sampling": "关",
        "tile_width": 512,
        "tile_height": 512,
        "tile_overlap": 128,
        "tile_fade": 32,
        "repair_engine": "关闭（仅 H3 二采）",
        "repair_model": "自动选择",
        "repair_scale": 1,
        "repair_batch_size": 5,
        "repair_temporal_overlap": 2,
        "repair_color_correction": "lab",
        "repair_quality": "ULTRA",
        "repair_device": "cuda",
        "repair_blocks_to_swap": 0,
        "repair_offload_device": "cpu",
        "repair_vae_tiling": True,
        "lock_source_exposure": True,
        "max_window_frames": 362,
        "window_overlap_frames": 24,
        "sample_preview": "关",
        "preview_interval": 1,
        "cleanup_after_run": "卸载模型",
        "refiner_lora": "none",
        "show_advanced_settings": False,
        **RELAY_NAMED,
    }


def update_packed_workflow(path: Path) -> bool:
    if not path.is_file():
        return False
    workflow = _read(path)
    packed_nodes = [
        node
        for node in workflow.get("nodes", [])
        if node.get("type") == "AICG3D_H3FinalHighResUpscalePacked"
    ]
    if not packed_nodes:
        raise RuntimeError(f"{path}: packed final-upscale node is missing")
    changed = False
    for node in packed_nodes:
        changed = _append_relay_values(node) or changed
    if changed:
        _write(path, workflow)
    return changed


def add_packed_node_to_short_drama(path: Path) -> bool:
    if not path.is_file():
        return False
    workflow = _read(path)
    if any(
        node.get("type") == "AICG3D_H3FinalHighResUpscalePacked"
        for node in workflow.get("nodes", [])
    ):
        return update_packed_workflow(path)

    combine = _find_node(workflow, 60)
    if not combine or combine.get("type") != "AICG3D_H3FinalSequenceCombine":
        raise RuntimeError(f"{path}: final sequence combine node 60 is missing")

    outputs = combine.setdefault("outputs", [])
    while len(outputs) < 4:
        outputs.append(
            {
                "localized_name": "成片数据",
                "name": "final_sequence",
                "type": FINAL_SEQUENCE_TYPE,
                "links": [],
            }
        )
    outputs[3]["localized_name"] = "成片数据"
    outputs[3]["name"] = "final_sequence"
    outputs[3]["type"] = FINAL_SEQUENCE_TYPE

    node_id = max(int(workflow.get("last_node_id", 0)), *(int(n["id"]) for n in workflow["nodes"])) + 1
    link_id = max(int(workflow.get("last_link_id", 0)), *(int(link[0]) for link in workflow.get("links", []))) + 1
    output_links = outputs[3].get("links")
    if not isinstance(output_links, list):
        output_links = [] if output_links is None else [output_links]
    output_links.append(link_id)
    outputs[3]["links"] = output_links

    max_order = max(int(node.get("order", 0)) for node in workflow["nodes"])
    node = {
        "id": node_id,
        "type": "AICG3D_H3FinalHighResUpscalePacked",
        "pos": [int(combine.get("pos", [0, 0])[0]) + 720, int(combine.get("pos", [0, 0])[1])],
        "size": [420, 420],
        "flags": {},
        "order": max_order + 1,
        "mode": 0,
        "inputs": [
            {
                "localized_name": "成片数据",
                "name": "final_sequence",
                "type": FINAL_SEQUENCE_TYPE,
                "link": link_id,
            }
        ],
        "outputs": [
            {"localized_name": "视频", "name": "video", "type": "VIDEO", "links": []},
            {"localized_name": "保存路径", "name": "saved_file", "type": "STRING", "links": []},
            {"localized_name": "高清处理报告", "name": "upscale_report", "type": "STRING", "links": []},
        ],
        "properties": {
            "Node name for S&R": "AICG3D_H3FinalHighResUpscalePacked",
            "cnr_id": "aicg3d-h3-suite",
        },
        "widgets_values": _packed_values(),
        "widgets_values_named": _packed_named(),
        "title": "成片高清二采放大",
    }
    workflow["nodes"].append(node)
    workflow.setdefault("links", []).append(
        [link_id, 60, 3, node_id, 0, FINAL_SEQUENCE_TYPE]
    )
    workflow["last_node_id"] = node_id
    workflow["last_link_id"] = link_id
    _write(path, workflow)
    return True


def main() -> None:
    render_paths = (
        ROOT / "workflows" / "11.AICG3D_多参考-首尾帧-数字人.json",
        WORKFLOW_DIR / "11.AICG3D_多参考-首尾帧-数字人.json",
    )
    packed_paths = (
        ROOT / "workflows" / "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json",
    )
    for path in render_paths:
        print(f"render {path}: {'updated' if update_render_workflow(path) else 'unchanged'}")
    for path in packed_paths:
        print(f"packed {path}: {'updated' if update_packed_workflow(path) else 'unchanged'}")
    short_drama = WORKFLOW_DIR / "13.AICG3D_MiniMax H3 无限长视频短剧工作流.json"
    print(
        f"short-drama {short_drama}: "
        f"{'updated' if add_packed_node_to_short_drama(short_drama) else 'unchanged'}"
    )


if __name__ == "__main__":
    main()
