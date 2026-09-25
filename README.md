# ComfyUI-AICG3D-Integrated 🚀
### 极致稳定的 MiniMax H3 AI 视频创作全链路解决方案

ComfyUI-AICG3D-Integrated 是一个专为专业 AI 视频创作者打造的深度整合插件包。它将 MiniMax H3 的核心生成能力、智能分段解析与高阶渲染策略集成于一体，旨在为用户提供一个**零冲突、工业级、可预测**的视频创作环境。

## 🌟 核心价值 (Core Value)

### 🛡️ 工业级稳定性：零冲突命名空间
针对 ComfyUI 生态中常见的节点同名冲突（Node Collision）问题，本插件采用了 **Forced Unique Namespace (强制唯一命名空间)** 架构。
- **唯一标识**：所有核心节点均采用 AICG3D_H3_ 专属前缀。
- **独立运行**：无论你的环境中安装了多少个 MiniMax 相关分支，AICG3D 均能独立运行，彻底杜绝节点被覆盖、工作流失效或界面崩溃的情况。

### ⚙️ 全链路功能集成 (Integrated Pipeline)
无需安装碎片化的插件，一个包即可覆盖从创意到成片的完整流程：

- **智能剧本分段 (PromptSplit)**：支持将长剧本/提示词自动拆分为逻辑段落 -> 一键映射至视频时间轴 -> 自动优化随机种子。
- **高精度渲染采样 (Advanced Sampler)**：集成高度优化的采样策略，确保视频在动态一致性与视觉质量之间达到最佳平衡。
- **Latent 深度放大 (HD Upscaler)**：内置专为 H3 设计的潜空间放大算法，在提升分辨率的同时，有效保留细节并减少伪影。
- **SelfLift 策略增强**：支持高级的自提升采样方案，极大增强画面细节的丰富度。

## 🛠️ 安装与部署

1.  **快速安装**：将 ComfyUI-AICG3D-Integrated 文件夹复制到 custom_nodes/ 目录下。
2.  **启动服务**：重启 ComfyUI。
3.  **定位节点**：在右键菜单中找到 **AICG3D** 分类即可开始创作。

> **💡 迁移指南**：由于采用了强制前缀，若您迁移旧版工作流，请将原有的 MiniMaxH3Easy 节点手动替换为对应的 AICG3D_H3_ 节点。

## 🤝 核心贡献者与致谢 (Core Contributors & Acknowledgements)

本项目是通过整合社区顶顶成果并进行工程化重构而成的，其稳定性与功能的实现离不开以下核心作者的贡献：

- **主架构师与整合者 (Integration & Maintenance)**: 
  - **AICG3D** - 负责整体架构设计、强制命名空间重构、稳定性优化以及插件的日常维护。
- **核心模块贡献者 (Core Engine Developers)**: 
    - **@goohai** - 提供了 Goohai-MiniMax-H3_Integration 的核心实现，包括强大的提示词优化能力与集成框架。
    - **@nkxx188** - 提供了 ComfyUI-MiniMaxH3-Easy 的核心节点实现，包括高效的采样策略与渲染流程。
- **社区支持**: 感谢所有在 MiniMax H3 生态中提供反馈、测试并贡献灵感的 ComfyUI 创作者。

## 📜 开源协议

本项目遵循 GNU GPL v3.0 协议开源。
