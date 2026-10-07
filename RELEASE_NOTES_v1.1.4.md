# comfyui-AICG3D v1.1.4

![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![comfyui](https://img.shields.io/badge/ComfyUI-custom%20node-1E90FF)
![version](https://img.shields.io/badge/version-1.1.4-green)

本次更新为短剧工作台的全局设置节点增加外部采样器和外部 Sigma 调度接口，并接入官方 DMAD 四步加速节点。

## 1. 外部采样器与调度器

- `MiniMax H3 Aicg 无限段落顺序生成（全局设置）` 新增两个可选输入：
  - `外部采样器`：`SAMPLER`
  - `外部调度器（Sigmas）`：`SIGMAS`
- 连接外部节点后，实际采样优先使用外部采样器和外部 Sigmas。
- 外部 Sigmas 会覆盖内置调度器、步数和 denoise 截断。
- 不连接外部输入时，继续使用原来的采样器名称、调度器、步数和 denoise，兼容旧工作流。

## 2. 官方 DMAD 四步加速

- 已兼容官方 `Yzmblog/DMAD` 插件：
  - `DMAD Sampler (re-noise)`
  - `DMAD Sigmas`
- 官方推荐设置：
  - DMAD LoRA 强度：`1.0`
  - 步数：`4`
  - Sigmas：`steps=4`，`shift=12`
  - `MiniMaxH3SigmaShift`：`shift_video=12`，`shift_audio=2`
- DMAD 插件来源：https://github.com/Yzmblog/DMAD

## 3. 13 号 1.2 工作流

- 已加入 `ModelSamplingMiniMaxH3`，默认 `shift_video=12`、`shift_audio=2`。
- 已加入 `DMAD Sampler (re-noise)` 和 `DMAD Sigmas`。
- 三个节点已经连接到全局设置节点的外部输入。
- 工作流中的模型说明已补充 DMAD 官方安装来源和参数。

## 4. 兼容性

- 外部采样器接口是可选输入，不连接时不会改变原有采样行为。
- 安装 DMAD 工作流版本前，需要把 `ComfyUI-DMAD` 放入 ComfyUI 的 `custom_nodes` 目录。
- DMAD 是 Apache-2.0 项目，插件代码仍由原仓库维护。

## 5. 同步内容

- `h3easy/aicg3d_sampler.py`
- `h3easy/nodes.py`
- `web/minimax_h3_easy_ui.js`
- `workflows/13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json`
- 插件版本：`1.1.4`

## 升级方法

1. 更新本插件仓库。
2. 安装或更新 https://github.com/Yzmblog/DMAD。
3. 重启 ComfyUI。
4. 浏览器执行 `Ctrl+F5` 强制刷新。
5. 重新打开 13 号 1.2 无限长视频生成工作流。
