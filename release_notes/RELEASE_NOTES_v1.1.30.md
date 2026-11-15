# comfyui-AICG3D v1.1.30

![version](https://img.shields.io/badge/version-1.1.30-green)

本版本更新了工作流发布目录，并修复最终高清合成阶段的内存峰值问题。

## 最终合成与高清放大

- 最终合成节点开始前卸载前端模型并清空模型缓存，降低长视频成片阶段的资源占用。
- 最终成片解码后、成片高清处理开始前再次回收模型和缓存，避免前后阶段同时占用显存与内存。
- RelayVSR 曝光锁定改为逐帧原地处理，不再为整段视频一次性创建约 16.4 GiB 的 CPU 临时张量。
- 帧数相同时跳过无用复制，减少高分辨率长视频的额外内存分配。

## 工作流目录

`workflows/` 已替换为当前维护的 7 个工作流：

- `10.AICG3D-SKILLS 多参考提示词推理工作流.json`
- `11.AICG3D_多参考-首尾帧-数字人.json`
- `12.AICG3D_二彩高清放大.json`
- `13.AICG3D_MiniMax H3 无限长视频短剧工作流.json`
- `18.AICG3D-CSR_人物场景动作迁移.json`
- `20.AICG3D-换姿势，换服装，换人脸.json`
- `22.AICG3D-VOSR2-最强图片视频超分极速流.json`

旧版工作流文件已从仓库目录移除。Registry 发布 Action 会精确校验这 7 个文件，缺失或混入旧文件都会导致发布验证失败。

## 验证

- RelayVSR 手动测试通过。
- 最终高清放大测试通过。
- 最终合成节点测试通过。
- `workflows/` 中 7 个 JSON 文件全部通过解析校验。

## 版本

- Registry 版本：`1.1.30`
- 仓库：https://github.com/JGRFW/comfyui-AICG3D
- 版本说明：https://github.com/JGRFW/comfyui-AICG3D/blob/main/release_notes/RELEASE_NOTES_v1.1.30.md
