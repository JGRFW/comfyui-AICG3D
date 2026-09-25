# ComfyUI-AICG3D-Integrated

这是一个深度整合的 ComfyUI 插件包，旨在提供一套完整且**绝无冲突**的 MiniMax H3 创作工作流。

## 🚀 核心升级：新方案 (Forced Unique Namespace)

针对用户反馈的「节点同名导致冲突/失效」问题，本版本舍弃了不稳定的智能检测机制，采用了**强制唯一命名空间**方案：

- **绝对唯一 ID**：所有核心节点（包括 Loader, Sampler, Segment 等）在注册时被强制加上 `AICG3D_H3_` 前缀。
- **零冲突运行**：无论你是否安装了 `ComfyUI-MiniMaxH3-Easy` 或其他社区分支，本插件将独立运行，互不干扰，彻底杜绝「节点被顶掉」或「界面失效」的情况。
- **统一入口**：整合了 `PromptSplit` 分段解析功能，无需安装多个碎片插件。

## 📦 功能组件

1. **AICG3D 核心节点**：包含高度优化的采样器、Latent 放大及 SelfLift 策略。
2. **AICG3D 技能/模板加载器**：统一调用 `skills/` 和 `prompt_presets/` 库，实现创作规范化。
3. **AICG3D 分段提示词解析**：支持剧本自动拆分 $\rightarrow$ 一键填入视频段落 $\rightarrow$ 自动种子随机化。

## 🛠 安装与使用

1. 将 `ComfyUI-AICG3D-Integrated` 文件夹放入 ComfyUI 的 `custom_nodes/` 目录下。
2. 重启 ComfyUI。
3. 在节点菜单中找到 **AICG3D** 分类。
4. **注意**：由于采用了强制前缀，之前保存的旧工作流（使用原版 MiniMaxH3Easy 节点）需要手动替换为 `AICG3D_H3_` 系列节点。

---
© 2026 AICG3D - 打造最稳定的 AI 视频创作链路
