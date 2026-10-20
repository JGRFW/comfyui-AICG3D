# comfyui-AICG3D v1.1.14

本次更新修复 Comfy Registry 安全检查标记，使插件能够重新进入公开自定义节点管理器的可搜索版本列表。

## 更新内容

- 修复 PyTorch checkpoint 的不安全反序列化扫描问题。
- 非 SafeTensors latent 放大模型改用 `torch.load(..., weights_only=True)` 安全加载。
- 保留 SafeTensors 优先加载路径。
- 保留对标准 `model` 状态字典和 `upscaler.` 前缀权重的兼容。
- 版本号提升至 `1.1.14`。

## 说明

Comfy Registry 的旧版本因 `policy-v0.6: insecure-deserialization` 被标记，不会出现在其他电脑的公开搜索结果中。`1.1.14` 发布后需要通过 Registry 自动安全检查，状态变为 `NodeVersionStatusActive` 后即可公开搜索和安装。
