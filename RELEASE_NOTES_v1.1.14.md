# comfyui-AICG3D v1.1.14

本次更新修复 Comfy Registry 安全检查标记，使插件能够重新进入公开自定义节点管理器的可搜索版本列表。

## 更新内容

- 修复 PyTorch checkpoint 的不安全反序列化扫描问题。
- 非 SafeTensors latent 放大模型改用 `torch.load(..., weights_only=True)` 安全加载。
- 保留 SafeTensors 优先加载路径。
- 保留对标准 `model` 状态字典和 `upscaler.` 前缀权重的兼容。
- 版本号提升至 `1.1.14`。
- 内部 Python 包统一改为 `aicg3d_h3easy` / `aicg3d_h3goohai`，避免与同源插件的通用包名互相抢占。
- 所有新增 HTTP 路由和前端扩展名收进 AICG3D 唯一命名空间，避免路由覆盖和扩展重名。
- 分段提示词解析改用正式 ID `AICG3D_H3PromptSegmentSplit`；仅在未检测到旧 PromptSplit 插件时注册旧 ID 兼容别名。
- 提示词优化设置接口不再把已保存的 API Key 返回浏览器；留空保存会保留旧密钥，并支持显式清除。
- 清理调试脚本、旧版前端备份和危险批量导入脚本，补齐 `psutil` / `requests` / `aiohttp` 基础依赖声明。

## 说明

Comfy Registry 的旧版本因 `policy-v0.6: insecure-deserialization` 被标记，不会出现在其他电脑的公开搜索结果中。`1.1.14` 发布后需要通过 Registry 自动安全检查，状态变为 `NodeVersionStatusActive` 后即可公开搜索和安装。
