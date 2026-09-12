<!--
  GitHub Release 正文（v1.0.0）。发布时把本文件内容整段粘进 Release 描述即可。
  发布前检查清单：
  1. 仓库地址已填 https://github.com/JGRFW/comfyui-AICG3D
  2. 补上截图：在「功能一览」各小节下插入 images/ 目录的图片
  3. 节点注册已核对：h3easy 全套节点 + Aicg 自带节点共 22 个，workflows/ 里用到的类型全部齐了
  4. 确认 skills/ prompt_guides/ prompt_presets/ 三个目录按你的意愿保留或移除
-->

# comfyui-AICG3D v1.0.0 发布

![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![comfyui](https://img.shields.io/badge/ComfyUI-custom%20node-1E90FF)
![version](https://img.shields.io/badge/version-1.0.0-green)

> 把三套 ComfyUI 插件整合成一个 **MiniMax H3 统一创作工作台**：
> 一个加载器面板、一个素材库、一个技能库、一个提示词模板库，
> 加上一套能跑的提示词优化链路。

**非官方项目。** 与 MiniMax、上海稀宇科技有限公司及其关联公司没有任何隶属或背书关系。

---

## 一、这是什么

MiniMax H3 在 ComfyUI 里的原生链路节点多、连线杂、素材要手写 `<Picture 1>` 这种标签。
社区里已经有三套做得很好的插件分别解决了不同的问题，但它们互相不通用，
装在一起会出现三套加载器、三套路子。

comfyui-AICG3D 做的事很简单：**把这三套合并成一套**，统一节点菜单、统一面板、
统一素材与技能入口，并保留全部原有节点 ID —— 旧工作流导进来不需要重新接线。

具体合并内容与逐项改动见 [与上游的差异](#七与上游的差异)。

## 二、代码来源与作者归属（请先读这一段）

这个插件**不是从零写出来的**。它的主体功能来自两位作者的开源项目，
本插件的贡献是"整合 + 界面 + 适配"。具体比例我们说清楚，不含糊：

| 来源 | 作者 | 许可证 | 在本插件中的实际分量 |
|---|---|---|---|
| [ComfyUI-MiniMaxH3-Easy](https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy) | nkxx188 | MIT | **骨架**。H3 主节点、素材加载器、渲染器与整体设计思路来自这里，本插件做了较大改动 |
| [Goohai-MiniMax-H3_Integration](https://github.com/goohai/Goohai-MiniMax-H3_Integration) | goohai（B站 孤海FOTO） | GPL-3.0-or-later | **提示词优化引擎 + 音视频解码**。基本为原样使用：`h3goohai/` 里 5 个文件一字未改，只有 `prompt_optimizer.py`、`nodes.py` 与前端做了少量适配 |
| [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) | MiniMax 官方 | MiniMax H3 Community License | **提示词规范与风格技能**。本插件做的是把 Agent 技能改造成 ComfyUI 节点可直接使用的方案 |
| 中文 AI 创作社区的提示词合集 | 各原始作者 | 未标注 | `prompt_presets/` 的 144 个模板，整理自社区公开流传的文档合集 |

逐文件的"原样复制 / 已修改"清单见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md#逐文件修改清单)，
完整鸣谢见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

**为什么要写这一段**：把别人的代码说成自己的，比用别人的代码严重得多。
这里面最值钱的提示词优化引擎是 goohai 写的，骨架是 nkxx188 写的，
我们只是把它们拼成了一个更好用的整体。

## 三、功能一览

### 1. 统一加载器：一个模型 + 可增减的 LoRA 槽位

`MiniMax H3 Aicg Loader` 的原生控件被换成一整块面板：

- **模型**：只保留一个 H3 主模型下拉，参考模型 REF2VA 自动复用主模型，不再需要单独选。
- **LoRA 槽位**：默认 1 行，用 `− 1 +` 增减（最多 4 行），另有「清空」一键复位。
  每行都是可检索下拉，带缩略图、体积、底模与触发词提示，权重用滑块微调。
- LoRA 直接叠加在 loader 内部，**不必再外挂 `LoraLoaderModelOnly` 节点**。
- 面板顺序固定为 **模型 → 编码与 VAE → LoRA**，原生控件隐藏。

> 兼容性：`fl2va_model / ref2va_model / text_encoder / video_vae / audio_vae`
> 五个 widget 仍按原顺序排在最前，旧工作流里保存的值不会错位。

### 2. 素材库：点一下就 @ 进输入框

- 素材加载器里的缩略图**单击**即把 `@图片1` 之类的引用写进下游主节点的提示词编辑器
  （原本只能拖拽排序）。
- 提示词编辑器右下角新增 **▤ 素材库**：按「可引用素材 / 输入目录」分页浏览，
  单击即插入引用。
- 输入目录里的素材会自动补进素材加载器后再引用，也可以直接「上传并引用」。

### 3. 技能库：把所有创作方法收进一个入口

- 18 个技能包 + H3 场景方案合并成一个技能目录，同名方案自动配对，
  同时携带 `skill_id` 与 `guide_id`。
- 提示词编辑器新增 **◆ 技能库**：全部 / H3 场景方案 / 通用技能三类，
  点选即用 —— H3 方案会直接切换主节点的提示词方案，其余技能把正文写入提示词。
- 修好了因为目录名是中文而扫描不到的技能（手机 Vlog、天宫仙境、超现实关键帧等）。

### 4. 提示词模板库：144 份模板进面板

- 社区提示词合集整理后抽出 **144 个模板、8 个分类**，正文约 90 万字。
- 技能库面板新增 **提示词模板** 页签，配分类胶囊筛选，卡片显示字数与来源。
- 点选即写回节点，或直接粘贴进提示词编辑器。

分类：H3 专题 21 · 视频生成与运镜 7 · 分镜与剧本 16 · 人像写真 15 ·
古风仙侠东方 18 · 画风与插画 15 · 生图模板与反推 37 · 提示词工程 15

### 5. 提示词优化：本地模型或云端 API，二选一

一键把一句话扩写成 H3 可用的完整提示词。

- **本地模式**：加载 GGUF 视觉模型在本机推理，不外发任何内容。
- **云端模式**：支持 OpenAI / Google Gemini / OpenRouter / 阿里云 DashScope /
  硅基流动 SiliconFlow / RunningHub，密钥自备。
- **只发送真正引用到的素材**：提示词里没有 `<Picture N>` 之类的引用时，
  一律不附带任何附件，附件计数同步归零；写了引用时，只把被引用的素材送出去。

### 6. 采样与渲染：把链路收短

- **AICG-采样器（高级）**：把 `RandomNoise` / `BasicScheduler` / `KSamplerSelect` /
  `BasicGuider` / `SamplerCustomAdvanced` 五个节点合成一个，只留一个 LATENT 输出，
  可直接接解码节点。执行逻辑与原生 `SamplerCustomAdvanced` 一致。
- **AICG-渲染器（高级）**：一条龙出片，单条输出线。

### 7. 界面

所有自定义面板共用一套深色玻璃主题，蓝紫渐变强调色，12px 信息密度；
三个来源的节点按分组染不同标题色，画布上一眼可辨。
备注节点（`Note` / `Markdown Note`）默认改用系统深灰配色，不再是前端硬编码的黄色
（可在 `设置 → AICG3D` 里关掉）。

## 四、安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/JGRFW/comfyui-AICG3D.git
```

重启 ComfyUI。

**前置条件**

- 需要包含 MiniMax H3 官方节点的较新版本 ComfyUI。
- **模型权重不随本插件分发**，请自行准备 H3 主模型、文本编码器、VAE。
- 使用提示词优化的本地模式需要装 `llama-cpp-python`（见上游
  [llama-cpp-python](https://github.com/JamePeng/llama-cpp-python)）。

## 五、快速上手

1. 添加 **MiniMax H3 Aicg Loader**，在面板里选模型（需要 LoRA 就点 `+`）。
2. 添加 **MiniMax H3 Aicg资源库**，把图片 / 视频 / 音频拖进去。
3. 添加 **MiniMax H3 Aicg**，在提示词编辑器里：
   - 点缩略图或 ▤ 素材库 → 插入 `@图片1`；
   - 点 ◆ 技能库 → 挑一个技能或 H3 场景方案；
   - 需要扩写就点提示词优化。
4. 接上采样与解码，运行。

## 六、示例工作流

`workflows/` 随仓库提供 11 个示例：

| 文件 | 用途 |
|---|---|
| `1.MiniMax_H3_Easy.json` | 基础链路（文生 / 图生 / 首尾帧 / 参考生视频 / 数字人） |
| `2.MiniMax_H3_Easy_Pass2.json` | 二采 |
| `3.MiniMax_H3_Easy_Selected_Video_Refine.json` | 选定视频再精修 |
| `4~7.*Context_Segments*.json` | 分段长视频：上下文传递 / Latent 二采 / 像素二采 / 控制 |
| `8.AICG3D_Smoke_Test.json` | 冒烟测试 |
| `9.AICG3D_合并采样器_测试.json` | 合并采样器链路 |
| `10.AICG3D_渲染器_测试.json` | 渲染器（高级） |
| `11.AICG3D_测试样板.json` | 综合样板 |

> 部分示例依赖第三方节点：KJNodes、VideoHelperSuite、pysssss `ShowText`、
> Memory Cleanup、Easy-Use，以及提供 `MiniMaxH3AVDecodeT8` 的 T8 解码插件。
> 缺哪个装哪个，具体以工作流里标红的节点为准。

## 七、与上游的差异

| 项 | 上游 | 本插件 |
|---|---|---|
| 节点归属 | 三套插件各自一个菜单 | 统一收敛到 `AICG3D` 命名空间 |
| 节点显示名 | `MiniMax H3 Easy …` | `MiniMax H3 Aicg …`（节点 ID 不变） |
| 加载器 | 原生 combo 控件 | 自绘面板 + 多 LoRA 槽位 |
| 素材引用 | 拖拽排序 | 单击 @ 进提示词 + 素材库面板 |
| 技能 | 分散在 `skills/` 与 `prompt_guides/` | 合并成一个技能库 + 面板 |
| 提示词模板 | 无 | 144 个模板 + 分类面板 |
| 采样 | 五个节点连线 | AICG-采样器（高级）一个节点 |
| 提示词优化附件 | 全部素材一起发送 | 只发送提示词真正引用到的素材 |

## 八、开源许可

自有代码按 **GPL-3.0-or-later** 发布（因为整合了 GPL-3.0-or-later 组件），
全文见 [LICENSE](LICENSE)。

| 组件 | 许可证 |
|---|---|
| `h3easy/`、`web/minimax_h3_easy_ui.js` | MIT（nkxx188） |
| `h3goohai/`、`web/minimax_h3_integration.js`、`locales/` | GPL-3.0-or-later（goohai） |
| `skills/`、`prompt_guides/` 中的 MiniMax 官方提示词内容 | MiniMax H3 Community License |
| `prompt_presets/` | 未标注，版权归各原始作者 |

许可证原文在 [third_party/](third_party/)，逐项声明与修改清单在
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

使用 MiniMax 官方提示词内容时请注意其许可的**地域限制**（不含欧盟、英国、韩国、美国）、
商业规模条款与 Acceptable Use Policy。**不接受这些限制**时：

```bash
git rm -r skills prompt_guides
```

不需要社区提示词模板时：

```bash
git rm -r prompt_presets
```

两个目录删掉后插件仍正常运行，对应的库会显示为空。

## 九、隐私与联网

| 场景 | 是否会外发数据 |
|---|---|
| 不使用提示词优化 | **不会**，插件不联网 |
| 提示词优化 · 本地 GGUF 模式 | **不会** |
| 提示词优化 · 云端模式 | 会把提示词与所选附件素材发送到你配置的服务商 |

云端模式下，密钥、调用费用与数据处理由你自行负责，并适用对应服务商的条款与隐私政策。

## 十、鸣谢

完整版见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

| 项目 | 作者 | 贡献 |
|---|---|---|
| ComfyUI-MiniMaxH3-Easy | **nkxx188** | 整个骨架：主节点、素材加载器、渲染器，以及把几十个节点收敛成一个主节点的设计 |
| Goohai-MiniMax-H3_Integration | **goohai**（B站 [孤海FOTO](https://space.bilibili.com/1194488958)） | 提示词优化引擎（云端 API + 本地 GGUF 双引擎）与音视频潜空间解码 |
| MiniMax-AI/MiniMax-H3 | **MiniMax** | 公开了 H3 五种生成模式的提示词规范与官方风格技能 |
| comfyUI-llama-TE | **tl2012tl** | 本地推理与多轮对话的开源工作（本版未包含其代码，但参考了设计） |

还要谢谢所有在社群里无偿分享提示词、教程与排错经验的人 ——
这个插件里很多"少走弯路"的部分，是别人已经踩过一遍并且愿意讲出来。

## 十一、免责声明

1. **非官方**。本插件为第三方非官方项目，与 MiniMax、上海稀宇科技有限公司及其关联公司
   无任何隶属、合作、赞助或背书关系，未获其审核或认可。
2. **商标**。`MiniMax`、`MiniMax H3`、`ComfyUI`、`Qwen`、`Gemma`、`RunningHub`
   等名称与标识归各自权利人所有，本插件仅在描述兼容性所必需的范围内使用。
3. **按现状提供，不提供任何担保**。因使用或无法使用本插件造成的任何直接、间接、
   附带或后果性损失（含数据丢失、设备损坏、业务中断、收益损失），
   作者与贡献者不承担责任。
4. **合规责任在使用者**。生成内容的合法性、真实性，以及是否侵犯他人肖像权、名誉权、
   著作权、商标权，由使用者自行判断并承担全部责任。
5. **禁止用途**。请勿用于生成违法、侵权、色情、暴力或虚假信息内容，
   请勿未经许可使用他人肖像与声音。
6. **第三方 API**。云端模式会外发数据，密钥与费用自负，详见第九节。
7. **模型与素材不在本仓库**。模型权重需自行获取并遵守其各自许可证；
   你上传或引用的素材，由你保证其合法来源与授权。
8. **第三方提示词内容**。`prompt_presets/` 等内容的版权归各原始作者，
   本仓库不作权利主张；权利人要求移除时我们会立即处理。
9. **不保证兼容与持续更新**。ComfyUI 版本迭代较快，不承诺在任意版本、
   任意硬件下都能工作，也不承诺技术支持。
10. **商业使用**。GPL-3.0-or-later 允许商业使用，但要求以同样许可证开放衍生作品源码。

完整免责声明见 [RELEASE.md](RELEASE.md#六免责声明)。

## 十二、反馈

问题、建议、权利人移除请求都欢迎提 issue。
接受第三方内容进入本仓库这件事，我们持开放态度 —— 说清诉求即可。

---

## 附：v1.0.0 更新日志

- 合并三套插件为统一节点菜单，节点 ID 全部保持原样
- 加载器改自绘面板，支持 1–4 个 LoRA 槽位与检索式下拉
- 素材库：单击 @ 引用、输入目录直传
- 技能库：18 个技能包 + H3 场景方案合并，中文目录名可识别
- 提示词模板库：144 个模板 / 8 个分类
- 提示词优化：只发送被引用的素材；本地 GGUF 参考图降采样，不再撑爆上下文
- 新增 AICG-采样器（高级）、AICG-渲染器（高级）
- 统一深色主题；备注节点改用系统配色
- 适配 comfyui-frontend 1.51 / ComfyUI 0.35 的 V3 节点接口

**完整更新说明与逐条修复记录见 [README.md](README.md)。**
