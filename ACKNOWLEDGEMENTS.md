# 鸣谢

comfyui-AICG3D 不是一个从零开始的项目。它站在三个优秀的 ComfyUI 插件肩上，
又吸收了 MiniMax 官方的提示词体系和中文创作社区大量无偿分享的经验。
没有这些人和这些作品，就没有这个插件。这里逐一说明各自的贡献。

> **鸣谢 ≠ 授权**。下面每一位作者的作品仍然适用他们自己的许可证，
> 具体条款与必须随附的声明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)，
> 许可证原文见 [`third_party/`](third_party/)。

---

## 一、构成这个插件的三个基础插件

### 1. ComfyUI-MiniMaxH3-Easy —— 作者 nkxx188（MIT License）

本插件的骨架。H3 主节点、素材加载器、渲染器，以及"一个入口覆盖文生 / 图生 /
首尾帧 / 参考生视频 / 数字人"的整体设计思路，都来自这个项目。

- 仓库：https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy
- 贡献文件：`h3easy/`、`web/minimax_h3_easy_ui.js`、`workflows/1.*` ~ `workflows/7.*`
- 使用方式：**大幅改动**。本插件把它的节点并入统一注册表、把显示名里的 `Easy` 换成
  `Aicg`、重写了加载器与素材库/技能库面板，还改了几处采样接口适配新版 ComfyUI。
  骨架和设计是它的，外层是本插件新写的。
- 特别感谢：他把原本几十个节点的连线收敛成一个主节点，还做了 `@` 直接引用素材、
  分段长视频与分段二采这些真正省时间的设计。

### 2. Goohai-MiniMax-H3_Integration —— 作者 goohai（GPL-3.0-or-later）

本插件的提示词优化引擎与音视频潜空间解码来自这个项目。
没有它的 `prompt_optimizer`，就没有"一键把一句话扩写成 H3 可用提示词"这个能力。

- 仓库：https://github.com/goohai/Goohai-MiniMax-H3_Integration
- 作者 B 站：孤海FOTO —— https://space.bilibili.com/1194488958
- 另一插件：https://github.com/goohai/Goohaitools-comfyui
- 贡献文件：`h3goohai/`、`web/minimax_h3_integration.js`、`web/audio/done.mp3`、`locales/`
- 使用方式：**基本原样使用**，这点要说清楚，不能含糊 —— `h3goohai/` 里的
  `audio_ops.py`、`conditioning.py`、`core.py`、`prompt_tags.py`、`sampling.py`
  五个文件一字未改，`done.mp3` 也逐字节相同；只有 `prompt_optimizer.py`（本地 GGUF
  参考图降采样与上下文上限等适配）、`nodes.py`（节点分类改名）、前端脚本和语言文件
  做过少量修改。
  换句话说，这个插件的提示词优化能力**是他写的代码在实际运行**，
  不是"参考了他的思路后重写"。
- 特别感谢：他做了云端 API 与本地 GGUF 双引擎的完整适配，还写了大量中文提示词模板。
  这一套是"会用"和"用好"之间的差距所在。这个功能本插件没有能力独立复现，
  也不打算假装是自己做的。

### 3. comfyUI-llama-TE —— 作者 tl2012tl（本版未包含其代码）

本项目在开发过程中参考过它的 Qwen / Gemma4 本地推理与多轮对话设计，
但**最终没有把它的代码随本插件分发**——因为该仓库当前没有声明许可证。
这不是对它质量的评价，纯粹是授权现状所限。

- 仓库：https://github.com/tl2012tl/comfyUI-llama-TE
- 如果你需要那套本地方案，请直接安装上游插件，两者可以共存。

---

## 二、提示词与技能内容

### 4. MiniMax 官方 —— MiniMax-AI/MiniMax-H3

`skills/` 与 `prompt_guides/` 里的 H3 提示词编写规范、五种生成模式（T2VA / I2VA /
FL2VA / L2VA / Ref2VA）的结构定义，以及官方风格技能，都来自 MiniMax 官方开源仓库。
本插件做的是"把 Agent 技能改造成 ComfyUI 节点能直接用的方案"，不是重新发明这套规则。

- 仓库：https://github.com/MiniMax-AI/MiniMax-H3
- 模型主页：https://huggingface.co/MiniMaxAI/MiniMax-H3
- 许可：MiniMax H3 Community License Agreement
- 特别感谢：官方把提示词规范公开写出来并开源，还配了完整示例，这在这个行业里并不常见。

### 5. 中文 AI 创作社区的提示词合集作者们

`prompt_presets/` 里的 144 个提示词模板、以及部分场景技能（高密度打斗、天宫仙境、
手机 Vlog、光感小清新、超现实底图、女团 MV 等），整理自中文 AI 创作社区公开流传的
提示词文档合集。这些文档在群里、在 B 站教程里、在共享网盘里被无数人反复转发，
很多已经很难追溯到最初作者；但每一个模板背后都有人在无偿试错、总结、分享。

- 每个条目的原始出处记录在 `prompt_presets/<分类>/<id>/meta.yaml` 的 `source:` 字段
- 版权归各原始作者所有，本仓库不作任何权利主张
- 如果你是其中任何内容的作者，或希望某条目移除，请提 issue 说明条目 ID，
  我们会在确认后立即删除，不需要额外的理由说明

---

## 三、所依赖的生态

- **ComfyUI** 与 **Comfy Org** —— 没有这个平台，这些节点无处安放
  https://github.com/comfyanonymous/ComfyUI
- **ComfyUI-Manager** —— 插件分发与依赖管理
- **llama.cpp / llama-cpp-python 生态** —— 本地模型的推理底座
- **Qwen（阿里）/ Qwen3-VL** 与 **Gemma（Google）** —— 提示词优化可以挂载的模型
- **RunningHub**、**OpenAI**、**Google Gemini**、**OpenRouter**、**阿里云 DashScope**、
  **硅基流动 SiliconFlow** —— 提示词优化可以在线调用的服务

---

## 四、还要谢谢

- 所有在社群里回答"这个报错怎么解"的人。本插件的很多修复，
  起因都是别人已经踩过一遍并且愿意讲出来。
- 所有测试、反馈、提意见的朋友。你们比代码本身更决定这个东西好不好用。

---

## 如果你是被引用的作者之一

如果上面任何一条描述与事实不符，或者你希望调整署名方式、补充链接、
限制使用范围，甚至要求移除相关内容 —— 请直接提 issue 或联系维护者，
我们会按你的意思改，默认优先采用你的要求。
