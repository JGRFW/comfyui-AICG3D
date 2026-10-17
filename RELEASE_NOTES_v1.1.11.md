# comfyui-AICG3D v1.1.11

本次更新将 AICG3D 短剧工作台接入 ComfyUI 官方节点注册表（Comfy Registry），让用户可以直接在 ComfyUI 官方节点管理器中搜索和安装。

## 更新内容

- 补齐 Comfy Registry 所需的项目名称、版本、Publisher、显示名称、仓库地址和问题反馈地址。
- 增加用于官方管理器卡片展示的 AICG3D 图标。
- 增加中文与英文检索关键词，覆盖 `AICG3D`、`短剧工作台`、`MiniMax H3`、`无限长视频` 和 `infinite video`。
- 增加 GitHub Actions 自动发布流程。
- 版本号提升至 `1.1.11`。

## 发布后如何搜索

在 ComfyUI 官方节点管理器的搜索框输入以下任意关键词：

- `AICG3D`
- `短剧工作台`
- `MiniMax H3`
- `aicg3d-h3-suite`

## 首次发布配置

1. 在 Comfy Registry 创建 Publisher：`aicg3d`。
2. 为 Publisher 创建 Registry API Key。
3. 在 GitHub 仓库的 Actions Secrets 中添加 `REGISTRY_ACCESS_TOKEN`。
4. 运行 `Publish to Comfy Registry` 工作流。

发布成功后可在此查看：

https://registry.comfy.org/nodes/aicg3d-h3-suite
