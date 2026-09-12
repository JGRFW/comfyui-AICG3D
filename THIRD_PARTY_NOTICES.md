# 第三方组件与许可证声明

本插件 **comfyui-AICG3D** 的**自有新增代码**（`aicg3d/`、`web/aicg3d-*.js`、
`web/aicg3d-theme.css`、`h3easy/aicg3d_sampler.py` 等标注为「本模块为新增代码」的部分）
版权归 **AICG3D** 所有，按 **GPL-3.0-or-later** 发布，全文见仓库根目录 `LICENSE`。

本插件同时包含下列第三方组件。**各第三方组件仍适用其自身的许可证，不会因为被合并进
本插件而改变。** 全部许可证原件放在 `third_party/`。

---

## 1. ComfyUI-MiniMaxH3-Easy — MIT License

| 项 | 内容 |
|---|---|
| 原始作者 | nkxx188 |
| 原始仓库 | https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy |
| 涉及文件 | `h3easy/`、`web/minimax_h3_easy_ui.js`、`workflows/1.*` ~ `workflows/7.*` |
| 许可证 | MIT，全文见 `third_party/LICENSE-ComfyUI-MiniMaxH3-Easy-MIT.txt` |
| 修改情况 | **已修改**：合并为 AICG3D 插件、重写加载器/素材库/技能库前端面板、新增 `_optimizer_attached_resources()` 与无引用输出规则、`aicg3d_sampler.py` 适配 ComfyUI 0.35 V3 节点接口 |

MIT 许可证要求：在软件的所有副本或实质性部分中保留上述版权声明与许可声明。

---

## 2. Goohai-MiniMax-H3_Integration — GPL-3.0-or-later

| 项 | 内容 |
|---|---|
| 原始作者 | goohai（其 LICENSE 署名为 "MiniMax H3 Audio T8 contributors"） |
| 原始仓库 | https://github.com/goohai/Goohai-MiniMax-H3_Integration |
| 涉及文件 | `h3goohai/`、`web/minimax_h3_integration.js`、`web/audio/done.mp3`、`locales/` |
| 许可证 | GPL-3.0-or-later，全文见 `third_party/GPL-3.0.txt`；原始声明见 `third_party/LICENSE-Goohai-MiniMax-H3_Integration-GPL-3.0-or-later.txt` |
| 修改情况 | 见下方逐文件清单。大部分文件为**原样复制**，只有 3 个文件有实质改动 |

因为本插件包含 GPL-3.0-or-later 代码，**插件整体按 GPL-3.0-or-later 发布**，源码随仓库提供。

### 逐文件修改清单

依据 GPL-3.0 第 5(a) 条，修改过的文件在此列明改动内容与日期（2026-09-12）。
其余文件为原样复制，未作修改，因此不作"已修改"标注。

| 文件 | 状态 | 改动内容 |
|---|---|---|
| `h3goohai/audio_ops.py` | 原样复制 | — |
| `h3goohai/conditioning.py` | 原样复制 | — |
| `h3goohai/core.py` | 原样复制 | — |
| `h3goohai/prompt_tags.py` | 原样复制 | — |
| `h3goohai/sampling.py` | 原样复制 | — |
| `h3goohai/nodes.py` | 已修改 2026-09-12 | 节点菜单分类由 `Goohai/MiniMax H3 Integration` 改为 `AICG3D/H3 集成` |
| `h3goohai/prompt_optimizer.py` | 已修改 2026-09-12 | 本地 GGUF 参考图降采样与上下文上限、模型目录解析层级、日志前缀、RunningHub App id 改为可用环境变量覆盖 |
| `web/minimax_h3_integration.js` | 已修改 2026-09-12 | 素材路径改为 `./audio/`，接入 AICG3D 公共层与主题 |
| `web/audio/done.mp3` | 原样复制 | 与上游文件逐字节相同 |
| `locales/en/main.json`、`locales/zh/main.json` | 已修改 2026-09-12 | 键值改写为 AICG3D 名称 |
| `locales/en/nodeDefs.json`、`locales/zh/nodeDefs.json` | 已修改 2026-09-12 | 原有 4 个键的值改写为 AICG3D 名称，并新增 `AICG3D_SkillLoader`、`AICG3D_PromptPreset` 两个键 |

### 本插件对它的依赖方式

`h3easy/nodes.py`（MIT 组件）通过 4 处调用使用本模块，这是两者的结合点：

- `h3easy/nodes.py` 中 3 处 `from ..h3goohai import prompt_optimizer`，
  调用 `image_file_data_url` / `generate_local_prompt` / `scan_local_models` /
  `missing_local_dependencies` / `gguf_dependency_status`；
- `h3easy/nodes.py` 中 1 处 `from ..h3goohai.audio_ops import decode_av_latent`。

因为这 4 处调用把 MIT 组件与 GPL-3.0-or-later 组件组成了一个作品，本插件整体按
GPL-3.0-or-later 发布。

---

## 3. MiniMax H3 官方提示词内容 — MiniMax H3 Community License Agreement

| 项 | 内容 |
|---|---|
| 原始出处 | https://github.com/MiniMax-AI/MiniMax-H3 的 `skills/` 目录 |
| 涉及目录 | `skills/` 中的官方风格技能与 `h3-prompt-writing`，以及由它们改写而成的 `prompt_guides/` 方案 |
| 许可证 | MiniMax H3 Community License Agreement（2026 年 8 月 2 日版），全文见 `third_party/LICENSE-MiniMax-H3-Community.txt` |
| 修改情况 | **已修改**：按 ComfyUI 节点场景改造——去除 Agent 运行时操作（工具分发、画布操作、阶段确认等待、外部生成、成片组装与交付）、拆分为 `guide.md` + `references/`、补充中文 `meta.yaml`。改造规则见 `prompt_guides/ADAPTATION_NOTES.md` |

### 该许可要求的声明原文

依据 MiniMax H3 Community License Agreement 第 III.4 条，分发时必须随附以下声明：

> MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.

### 你需要知道的使用限制

以下是该许可的要点**摘要**，仅供参考，以 `third_party/LICENSE-MiniMax-H3-Community.txt` 英文原文为准：

- **地域限制**：许可的「适用地域」为全球**但不含**欧盟、英国、韩国、美国。在上述被排除地域使用或分发不在授权范围内。
- **商业条款**：商业产品/服务年收入超过 2000 万美元时，需先向 api@minimax.io 取得书面授权。
- **用途限制**：须遵守其 Acceptable Use Policy（许可 Exhibit A），且不得用 MiniMax H3 的产出改进其它 AI 模型。
- **商标**：该许可不授予商标许可；`MiniMax` / `MiniMax H3` 仅可在「描述与分发 MiniMax H3 所合理必需」的范围内使用。

### 与 GPL-3.0 的关系（重要）

该许可要求分发者「让每个接收方接受至少同样严格的限制条款」，并带有地域与用途限制；
而 GPL-3.0 第 7 条禁止追加额外限制。两者不能同时适用于同一份作品。因此本仓库把
`skills/` 与 `prompt_guides/` 作为**独立分区**处理：它们不是本插件 GPL 作品的组成部分，
而是各自按 MiniMax 许可分发的素材。

**不能接受上述限制，或需要在被排除地域分发时**，请删除这两套内容：

```bash
git rm -r skills prompt_guides
```

删除后插件仍可正常运行，技能库会显示为空；`prompt_guides/` 缺失时 H3 主节点会自动
退回不带场景方案的普通指南。

---

## 4. 提示词模板库 `prompt_presets/`

| 项 | 内容 |
|---|---|
| 来源 | 中文 AI 创作社区公开流传的提示词文档合集，经整理抽取为 144 个模板 |
| 原始出处 | 记录在各条目 `prompt_presets/<分类>/<id>/meta.yaml` 的 `source:` 字段 |
| 许可证 | **未标注**，版权归各原始作者所有 |

本目录是技术性的收集、去重与检索化整理，未从任何权利人处取得明示授权。本仓库对这部分
内容不作任何权利主张。

**如果你是其中任何内容的权利人并希望移除**，请在本仓库提 issue 说明条目 ID，我们会在
确认后立即删除对应条目。不接受第三方内容进入本仓库时，可直接删除：

```bash
git rm -r prompt_presets
```

删除后插件仍可正常运行，「提示词模板」页签会显示为空。

---

## 5. 不随本插件分发的第三方内容

- **模型权重**（MiniMax H3 主模型、文本编码器、VAE、Qwen3-VL 等）不随本插件分发，需由用户
  自行获取并遵守其各自许可证。MiniMax H3 模型本身的许可见
  https://huggingface.co/MiniMaxAI/MiniMax-H3 。
- **llama.cpp / llama-cpp-python** 由用户运行环境自行安装，不随本插件分发。
- **LoRA** 由用户自行放置，不随本插件分发。

---

## 6. 运行时会调用的第三方服务

提示词优化功能可以调用下列第三方 API，需要用户**自备密钥**。启用后，你的提示词以及
所选附件素材会被发送到对应服务：

| 服务 | 域名 |
|---|---|
| OpenAI | api.openai.com |
| Google Gemini | generativelanguage.googleapis.com |
| OpenRouter | openrouter.ai |
| 阿里云 DashScope | dashscope.aliyuncs.com |
| 硅基流动 SiliconFlow | api.siliconflow.cn |
| RunningHub | www.runninghub.cn |

不配置密钥、改用本地 GGUF 模型时，不会向上述服务发送任何内容。

---

## 7. 免责声明

- 本插件是**非官方**第三方项目，与 MiniMax、上海稀宇科技有限公司及其关联公司**无任何
  隶属、合作或背书关系**。
- `MiniMax`、`MiniMax H3` 等名称与标识归其权利人所有，本插件仅在描述兼容性所需的范围内
  使用这些名称。
- 本插件按 GPL-3.0-or-later 提供，**不附带任何担保**。
