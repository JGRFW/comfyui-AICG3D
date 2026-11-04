# comfyui-AICG3D v1.1.25

![version](https://img.shields.io/badge/version-1.1.25-green)

## 本次更新

### 二采无限修复引擎

- `AICG-渲染器（二采放大）`新增 `SeedVR2 视频修复`、`RTX VSR 超分`、`VOSR2 单帧修复` 三种独立修复方式。
- 选择修复引擎后，节点会解码上一颗二采传来的视频 latent，修复真实画面，再编码回 H3 latent 交给下一颗二采节点。
- `1.0x` 修复可以连续串联，后一颗处理前一颗的结果，不再只是重复执行 H3 二采。
- 修复引擎启用时自动跳过当前 H3 二采采样，减少重复计算和画面结构漂移。
- SeedVR2 支持时序批次、重叠融合、颜色校准、VAE 分块与 BlockSwap；RTX VSR 与 VOSR2 作为可选加速兼容方案。
- 缺少外部修复插件或模型时，会在选择对应引擎后给出明确提示；保持“关闭”时不增加任何外部依赖。

### 二采音频与原画面保护

- 二采采样使用独立视频噪声遮罩，音频 latent 不再参与二次修复。
- 采样器会完整转发 packed AV denoise mask。
- 二采完成后强制恢复一采原始音轨，避免音色、速度和时长发生变化。
- 新增二采音频保护、连续修复链、目标分辨率与修复适配器回归测试。

### 角色音色库界面修复

- 修复旧工作流保存小尺寸后，音色库面板只显示窄栏、内容被裁切的问题。
- 节点加载恢复旧尺寸后，会重新应用最小尺寸并同步 DOM widget 布局。
- 同时兼容经典节点模式与 Nodes 2.0；放大或缩小节点时，面板会跟随实际宽度。
- 增加响应式角色行、输入框和按钮布局，窄宽度下不再横向溢出。
- 新增经典模式与 Nodes 2.0 的自动布局检查。

### 节点注册与工作流

- 收敛 H3、PromptSplit 和 Spark-TTS 的命名空间兼容注册，避免与同名开源插件互相抢占节点 ID。
- 更新 11 号数字人、12 号二采修复和 13 号无限分段工作流。
- 更新二采无限修复说明与发布审计脚本。

## 可选修复模型

SeedVR2：

```text
ComfyUI/models/SEEDVR2/seedvr2_ema_3b_fp8_e4m3fn.safetensors
ComfyUI/models/SEEDVR2/ema_vae_fp16.safetensors
```

VOSR2：

```text
ComfyUI/models/vosr2/VOSR2/
```

RTX VSR 需要安装 `comfyui_nvidia_rtx_nodes`，并使用支持 NVVFX 的 NVIDIA RTX 显卡。以上修复引擎均为可选功能，不安装时仍可正常使用原有 H3 二采。

## 版本

- Registry 版本：`1.1.25`
- 仓库：https://github.com/JGRFW/comfyui-AICG3D
- 工作流下载：https://github.com/JGRFW/comfyui-AICG3D/tree/main/workflows
