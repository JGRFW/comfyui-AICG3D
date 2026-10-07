# comfyui-AICG3D v1.1.5

![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![comfyui](https://img.shields.io/badge/ComfyUI-custom%20node-1E90FF)
![version](https://img.shields.io/badge/version-1.1.5-green)

本次更新把外部采样器和外部 Sigmas 接入三个渲染器，并修复经典画布模式下提示词优化设置无法打开的问题，同时同步 11、12、13 号工作流。

## 1. 三个渲染器支持外部采样

以下节点新增可选输入：

- `AICG-渲染器（高级·加速）`
- `AICG-渲染器（一采）`
- `AICG-渲染器（二采放大）`

新增输入：

- `外部采样器`：`SAMPLER`
- `外部调度器（Sigmas）`：`SIGMAS`

连接外部输入后，实际采样优先使用外部采样器和 Sigmas。未连接时，继续使用原来的采样器名称、调度器、步数和 denoise。

## 2. 二采完整支持

- 二采放大节点的整幅采样支持外部采样器和 Sigmas。
- 二采分块采样同样支持外部采样器和 Sigmas。
- 外部 Sigmas 的步数会同步到进度计算。

## 3. DMAD 四步加速

可连接：

- `DMAD Sampler (re-noise)` -> `外部采样器`
- `DMAD Sigmas` -> `外部调度器（Sigmas）`

官方推荐参数：

- DMAD LoRA 强度：`1.0`
- 步数：`4`
- Sigmas：`steps=4`，`shift=12`
- `MiniMaxH3SigmaShift`：`shift_video=12`，`shift_audio=2`

DMAD 插件来源：https://github.com/Yzmblog/DMAD

## 4. 提示词优化设置修复

- Nodes 2.0 开启时保持原来的入口行为。
- Nodes 2.0 关闭时，经典画布把入口显示为真正的“打开提示词优化设置”按钮。
- 点击后可以正常打开设置面板并选择本地视觉模型。
- 保存工作流时仍保留原布尔值位置，不会造成控件错位。

## 5. 工作流同步

- `workflows/11.AICG3D_多参考-数字人.json`
- `workflows/12.AICG3D_二彩高清放大.json`
- `workflows/13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json`
- `workflows/13.AICG3D_无限分段 生视频.json`

## 6. 同步内容

- `h3easy/nodes.py`
- `h3easy/aicg3d_sampler.py`
- `web/minimax_h3_easy_ui.js`
- 插件版本：`1.1.5`

## 升级方法

1. 更新本插件仓库。
2. 如使用 DMAD 工作流，安装或更新 https://github.com/Yzmblog/DMAD。
3. 重启 ComfyUI。
4. 浏览器执行 `Ctrl+F5`。
5. 重新打开对应的 11、12、13 号工作流。
