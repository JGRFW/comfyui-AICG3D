<img width="1591" height="585" alt="image" src="https://github.com/user-attachments/assets/a0073ab0-ed68-43b6-a866-ce80f8601e16" />

# comfyui-AICG3D

基于 MiniMax H3 Easy 优化合并的 ComfyUI 插件，加入统一的素材、技能与加载器界面。

本插件是**非官方**第三方项目，与 MiniMax / 上海稀宇科技有限公司无任何隶属、合作或背书关系。

| 来源 | 许可证 | 合并内容 |
|---|---|---|
| `ComfyUI-MiniMaxH3-Easy`（nkxx188） | MIT | H3 主节点、素材加载器、渲染器 |
| `Goohai-MiniMax-H3_Integration`（goohai） | GPL-3.0-or-later | 提示词优化引擎、AV 潜空间解码 |
| 本项目新增 | GPL-3.0-or-later | 统一加载器 / 素材库 / 技能库面板、AICG-采样器、提示词模板库 |
| `comfyUI-llama-TE`（tl2012tl） | 上游**未附许可证** | **未合并**：早期版本曾合并它的本地 LLM 节点，因上游无授权已整体移除，本仓库不含其代码 |

第三方许可证原文在 `third_party/`，逐项声明见 `THIRD_PARTY_NOTICES.md`。

`comfyUI-llama-TE` 已移除的说明见下方「鸣谢」、`ACKNOWLEDGEMENTS.md` 第 3 节与
`THIRD_PARTY_NOTICES.md` 第 6 节；提示词优化的本地模型能力由插件自带的 GGUF 引擎提供，不受影响。

节点 ID 全部保持原样（显示名里的 `Easy` 换成 `Aicg`），旧工作流导入后不需要重新接线。

## 这次改了什么

### 1. 加载器：一个模型 + 可增减的 LoRA 槽位

`MiniMax H3 Aicg Loader` 的原生控件被换成一整块 AICG3D 面板：

- **模型**：只保留一个下拉（H3 主模型）；参考模型 REF2VA 已从面板移除，参考生视频自动复用主模型。
- **LoRA 槽位**：默认 1 行，用 `− 1 +` 增减（最多 9 行），另有「清空」一键复位；
  每行都是可检索下拉，带缩略图、体积、底模与触发词提示，权重用滑块微调。
- LoRA 直接叠加在 loader 内部，不必再外挂 `LoraLoaderModelOnly` 节点。
面板顺序为 **模型 → 编码与 VAE → LoRA**，原生控件固定隐藏，不再提供切回入口。

`fl2va_model / ref2va_model / text_encoder / video_vae / audio_vae` 五个 widget 仍然排在最前（其中 `ref2va_model` 仅隐藏、不再出现在面板上），
所以旧工作流里保存的 5 个值依旧按位对应。

### 2. 素材：点一下就 @ 进输入框

- **素材加载器**里的缩略图支持单击：直接把 `@图片1` 之类的引用写进下游主节点的提示词编辑器（原本只能拖拽排序）。
- 提示词编辑器右下角新增 **▤ 素材库**：按「可引用素材 / 输入目录」分页浏览，单击即插入引用；
  输入目录里的素材会自动补进素材加载器后再引用，也可以直接「上传并引用」。

### 3. 技能：统一的 Skill 调用入口

- `skills/`（原 llama-AI 技能包）与 `prompt_guides/`（原 H3 场景方案）合并成一个技能目录，
  同名方案自动配对，同时携带 `skill_id` 与 `guide_id`。
- 新增节点 **AICG3D 技能加载器**：输出「技能正文 + 任务描述」拼好的提示词，可直接接到 H3 主节点或多轮对话。
- 提示词编辑器新增 **◆ 技能库**：全部 / H3 场景方案 / 通用技能三类，点选即用。
  带有 H3 方案的技能会直接切换主节点的提示词方案，其余技能把正文写入提示词。
- 原来因为目录名是中文而扫描不到的几个技能（手机 Vlog、天宫仙境、超现实关键帧等）现在都能识别。

### 4. 采样：AICG-采样器（高级）

新增节点 **AICG-采样器（高级）**（`MiniMaxH3EasySamplerAdvanced`）：
把原生链路里散开的 `RandomNoise` / `BasicScheduler` / `KSamplerSelect` /
`BasicGuider` / `SamplerCustomAdvanced` 五个节点合成一个，
只留一个 LATENT 输出，可直接接到 `MiniMaxH3AVDecodeT8` 的 `av_latent`。
执行逻辑与原生 `SamplerCustomAdvanced` 一致，参考
`workflows/9.AICG3D_合并采样器_测试.json`。

### 5. 提示词模板库：144 份模板进技能库

把本地收集的提示词合集（494 个文件）整套整理进插件：

- 去重后从 199 份文档里抽出 **144 个提示词模板**，落在 `prompt_presets/`，正文约 90 万字。
- 分成 8 类：H3 专题 21、视频生成与运镜 7、分镜与剧本 16、人像写真 15、
  古风仙侠东方 18、画风与插画 15、生图模板与反推 37、提示词工程 15。
- 每个模板一个目录：`prompt_presets/<分类>/<id>/SKILL.cn.md` + `meta.yaml`，
  根目录 `manifest.json` 记录分类、字数与来源路径。
- 技能库面板新增 **提示词模板** 页签，配分类胶囊筛选，卡片显示字数与来源；
  点选即写回节点或直接粘贴进提示词编辑器。
- 新增节点 **AICG3D 提示词模板**（`AICG3D_PromptPreset`）：输出「模板正文 + 任务描述」，
  可直接接 H3 主节点或多轮对话。
- 顺带补了 4 个新技能包（高密度打斗、生图导演、天宫仙境、K-pop 女团 MV）与 5 个技能的中文显示名，
  技能包总数 18。
- 修掉技能库目录缓存失效：目录签名现在递归采集子目录 mtime，改 `meta.yaml` 立即生效。

### 6. 视觉

所有自定义面板共用 `web/aicg3d-theme.css`：深色玻璃面板、蓝紫渐变强调色、
紧凑的 12px 信息密度；三个来源的节点也按分组染了不同的标题色，画布上一眼可辨。

备注节点（`Note` / `Markdown Note`）默认使用系统深灰配色，
不再是 ComfyUI 前端硬编码的黄色；
工作流里已保存的颜色不受影响。开关：
`设置 → AICG3D → 备注节点使用系统默认配色（不再用黄色）`。

### 7. 新节点为什么不是系统默认颜色？(已修)

现象：新建工作流、新增任何节点（`VAEDecode`、`KSampler`……），节点都带着红 / 黄 / 棕的
色板色，重启 ComfyUI 也还在。

根因不在本插件，而在 **tinyterraNodes（ttN）**：
它的右键菜单项「🌏 Default Node BG Color」会把选中的色板写进
`localStorage['Comfy.Settings.ttN.defaultBGColor']`，然后通过 `nodeCreated` /
`loadedGraphNode` 给**每一个**节点上色（`node.color` / `node.bgcolor`），
同时留下标记 `properties.ttNbgOverride`。这跟本插件无关，任何节点都会被染。

本插件的处理（`web/aicg3d-nodes.js`）：

1. 启动时清掉 `Comfy.Settings.ttN.defaultBGColor`，ttN 之后不再给新节点上色；
2. 把已经被 ttN 染色的节点还原成系统配色 —— 只处理「有 `ttNbgOverride` 标记
   且当前颜色等于该标记颜色」的节点，手动配色、工作流自带配色、其它插件的
   节点配色都不动；
3. 改动节点颜色后重新保存工作流即写回干净配色。

开关：`设置 → AICG3D → 新节点保持系统默认配色（自动清理 ttN 全局默认色）`，默认开启。
关掉后一切交给 ttN，和以前一样。

想彻底手动来一遍：画布右键 → `🌏 默认节点背景颜色` → 选 `No Color`，
作用等同第 1 步，并会顺带还原当前画布上的节点。

### 8. 本地 LLM 节点（`llama TE`）没有包含在本仓库

早期版本曾合并 `comfyUI-llama-TE` 的 Qwen / Gemma4 本地文本编码节点
（节点 ID `QwenTE_*` / `Gemma4TE_*`）。该上游仓库**没有提供任何许可证文件**，
法律上属于默认「保留所有权利」，未经授权不能再分发，因此已从本仓库移除。

提示词优化的本地模型能力**不受影响**：`h3goohai/prompt_optimizer.py` 自带 GGUF
本地引擎（配置里 `mode` 选 `local`，再选 `local_model` / `local_mmproj`），
不需要那套节点。

如果你本来就在用 `comfyUI-llama-TE`，单独安装它即可，两套节点互不冲突。

### 9. 本地模型提示词优化：参考图不再撑爆上下文

**症状**：本地模型做提示词优化时报
`提示词优化失败 Qwen35ChatHandler(mtmd_helper_eval_chunk_single): Media evaluation failed with error code 1.`

**原因**：本地 GGUF 视觉模型把每张参考图当成一整个多模态批次送进 KV cache。
原图直传时（例如 1440×1440 的截图）单张就要约 2000 个视觉 token，几张叠加后
llama.cpp 找不到足够的连续显存槽位，日志里会看到
`decode: failed to find a memory slot for batch of size N`，随后就是上面那句报错。

**修复**（两层）：

1. `h3goohai/prompt_optimizer.py`：进入本地引擎的参考图统一压到长边 512（约 256 token/张），
   单次最多 12 张；上下文窗口从 16384 提到 32768，显存不够时自动回退 16384。
2. `h3easy/nodes.py`：H3 Aicg 节点的本地优化不再原图直传，先缩放再编码（1440px 图从 1MB 降到 2KB）。

即使媒体评估仍然失败（参考集特别重时），也会自动重新加载模型并**改用纯文本重试**，
返回优化结果而不是直接报错。云端 API 模式不受影响，仍按原图发送。

### 10. Nodes 2.0（Vue 节点）不再出现可点击的空白区域

**现象**：开启 `Nodes 2.0` 后，加载器 / 媒体加载器 / H3 Aicg 主节点底部多出一大块空白，
右键那块空白还会弹出 VAE / LoRA 选择菜单。

**原因**：插件原先靠 `widget.hidden = true` 隐藏原生控件，这只对旧 Canvas 渲染器有效。
Vue 渲染器（`computeProcessedWidgets()` → `isWidgetVisible()`）只看 `widget.options.hidden` /
`widget.options.canvasOnly`，而且读的是 **widgetValueStore 注册时的快照**，
事后只改 `widget.options.hidden` 不会生效；被隐藏的控件仍占着一行高度，
空的 DOM 行又被 Vue 当成可交互区域，于是右键就弹出了模型菜单。

**修复**（`web/aicg3d-core.js` 提供三个共用函数，四个前端脚本统一接入）：

1. `markWidgetHidden(widget)`：同时写 `options.hidden` / `options.canvasOnly` /
   `_state.options.hidden`，并压掉 `computeSize`，让控件在两种渲染器下都不占位。
2. `autoHideWidgets(nodeType, names)`：包装 `prototype.addWidget`，
   **在控件注册阶段**就把它标成隐藏 —— Nodes 2.0 只认注册时的快照，这一步是关键。
3. `refreshVueWidgets(node)`：对已经建好的节点，用 `pop()`+`push()` 最后一项
   `node.widgets` 触发前端重新映射（直接重新赋值数组无效）。

**验证**（Playwright 真机跑 `Nodes 2.0`，逐个量节点 DOM 行高）：

| 工作流 | 节点数 | 空白行 |
|---|---|---|
| `workflows/1.MiniMax_H3_Easy.json` | 16 | 0 |
| `workflows/8.AICG3D_Smoke_Test.json` | 13 | 0（`合并为视频(VHS)` 的 340px 预览区属第三方插件） |

在节点底部残留的 22~27px 上右键，弹出的是原生节点菜单（Pin / Clone / 颜色…），
不再出现 `comfyui-easyuse-contextmenu-model`。旧 Canvas 渲染器回归正常。
### 11. 一条龙出片：AICG-渲染器（高级）+ 单条输出线

**主节点输出与上游保持一致**：`MiniMax H3 Aicg`（以及 `Context Segments` /
`Selected Video Context`）有 **2 个输出点** —— 第 1 个 `model`、第 2 个 `h3_context`，
和上游 `ComfyUI-MiniMaxH3-Easy` 完全相同。

上游那批二采工作流（`2.`~`7.`）都是从这个 `model` 输出取模型去接
`ModelAttentionBackend` / `BasicScheduler` / `LoraLoaderModelOnly`。
早先把这个输出删掉后，老工作流读到的第 1 个输出变成了 `h3_context`，
校验报 `received_type(MINIMAX_H3_CONTEXT) mismatch input_type(MODEL)` 和
`tuple index out of range`，整条二采链路直接跑不起来；现已恢复。

- `MiniMaxH3Context` 新增 `model` 字段，三处构造点都会回填。
- `MiniMax H3 Aicg Output` 末尾新增 `model` 输出：需要走原生链路
  （BasicGuider / SamplerCustomAdvanced / VAEDecode …）时，从它取 model 也可以，
  原来的 6 个输出位置不变，老工作流不必重连。
- `Segment Sample` / `Sample Setup` / `Segment Refine` / `Selected Video Refine`
  的 `model` 输入改成**可选**：接了就优先用它，没接就自动用 `h3_context.model`。

**新节点 `AICG-渲染器（高级）`**（`MiniMaxH3EasyRenderAdvanced`）把原先散在画布上的四步
合并成一个节点：

```text
AICG-采样器（高级）  ->  采样
VAEDecode           ->  视频帧
VAEDecodeAudio      ->  音频
CreateVideo         ->  合成 VIDEO
```

输入只有上游的 `h3_context`，控件是 `Seed / 采样器 / 调度器 / 步数 / 降噪`，
输出只有一条 `VIDEO`，直接接 `SaveVideo`。数字人 / 锁定参考音频时自动用驱动音轨。

**素材统一在「媒体包」里点选**：素材选择不再依赖主节点的模式，
`图生或首尾帧` 模式下也能点素材卡片插入 `@` 引用，`@` 自动补全同样可用。
判定集中在 `canUseMediaMentions()`（新增 `isImageMode`，并用 `isTarget` 限定了节点范围）。

**提示词优化完成提示音**：主节点编辑器里的 `✦` 优化成功后播放 `web/audio/done.mp3`。
同时修正了 `minimax_h3_integration.js` 里写成 `../audio/done.mp3` 的路径
（应为 `./audio/done.mp3`），否则浏览器会 404 而静默失败。

### 12. 提示词优化只发送提示词真正引用到的素材

**症状**：媒体包里放 7 张图，提示词只写了 `<Picture 4>` 与 `<Picture 1>`，
优化结果却把 `<Picture 1>` ~ `<Picture 7>` 全部写进 `subject_definitions` /
`retention_analysis`。

**原因**：`promptOptimizerResources()` 会把媒体加载器里的**全部**素材编进请求，
`media_counts`、资源标签和本地引擎的 `_user_parts()` 都按全量下发，
而系统提示词要求"每个 label 都要定义"，模型于是把没用到的素材也写了进去。

**修复**：新增 `referencedMediaTags()` / `filterOptimizerResources()`，
在下发前按提示词里实际出现的 `<Picture N>` / `<Video N>` / `<Audio N>` 过滤：

- 命中：只把引用到的素材（及其原始序号）发出去，`media_counts` 同步收敛。
  序号按资源自带的 tag 保留，不会重新编号，所以 `<Picture 4>` 仍是第 4 张图。
- 提示词完全没有引用：保持原行为，全部下发（不影响纯文字场景描述）。
- 引用的标签一个都匹配不上（例如写错序号）：同样回退为全部下发，避免优化器空手作战。

上下文分段的「逐段优化」也会按每段自己的提示词再过滤一次。

### 13. 参考生视频只把提示词里引用到的素材送给模型

**症状**：媒体包里放 12 张图，提示词只写 `<Picture 5>` 与 `<Picture 11>`，
运行时却报 `ValueError: Reference mode media limits are 9 images, 3 videos and 3 audio clips`。

**原因**：`MiniMaxH3EasyMediaLoader` 是不限量的素材库（`MEDIA_LOADER_GROUPS`
里数量上限为 `None`），而一次 H3 参考调用真正的上限是 9 图 / 3 视频 / 3 音频。
之前下游节点直接拿整个媒体包去校验，所以只要库里超过 9 张图就会在采样前直接失败。

**修复**：新增 `bind_reference_media()`，与分段模式早已使用的 `bind_segment_media()` 同策略：

- 提示词里出现了 `<Picture N>` / `<Video N>` / `<Audio N>`（含 `@` 提及展开的）：
  只送被引用的那几个素材，并按引用顺序重新编号为 `<Picture 1>`、`<Picture 2>`……
  提示词文本同步重写，所以模型看到的编号与实际下发的素材始终一致。
- 提示词完全没有引用：保持原行为，全量下发。
- 引用的编号一个都对不上（例如只写了 `<Picture 99>`）：回退为全量下发，避免空参考。
- 数字人模式：只收窄参考画面，驱动用的音频不受影响。

真的超预算时，报错也会说清楚实际收到多少：
`Reference mode media limits are 9 images, 3 videos and 3 audio clips, but received 12 images, 0 videos and 0 audio clips.`。

### 14. 本地视觉引擎也遵守「读取已连接媒体」

**症状**：优化方式选「本地视觉模型」时，即使关掉「读取已连接媒体」，
优化结果里仍然会出现媒体包中**全部**素材的引用与描述。

**原因**：API 引擎的素材随 `media_parts` 下发，会被 `read_media` 拦下；
本地引擎走 `_optimizer_local_generate()`，在函数内部直接把 `resources` 编码成附件，
`read_media=False` 只让 `attached_media_count` 变成 0，附件却照样发出，
模型一边被告知"没有附件"，一边看到了所有素材。

**修复**：本地引擎同样先过开关（`attached_resources`）。
关掉时模型看不到任何素材，`attached_media_count` 与实际附件保持一致。

### 15. 提示词没有引用素材时，优化结果不会新增素材引用

**症状**：纯文字提示词（没有任何 `@` 引用）在「参考生视频」模式下优化后，
结果里凭空多出 `图1`/`图2`…… 的 `subject_definitions`，等于把所有上传素材都变成了引用。

**原因**：运行时的素材绑定（`bind_reference_media()`）按优化后提示词里的引用标签执行，
模型新增的标签会真的改变送进 H3 的素材。而全引用模式的指南本身要求输出
`subject_definitions`，小模型看不到素材也会硬造标签，只加一句"不要新增引用"的
提示词约束挡不住。

**修复**：改成代码强制，不再依赖模型自觉：

- 提示词里没有 `<Picture N>` / `<Video N>` / `<Audio N>` 时一律不附带附件
  （`_optimizer_attached_resources()`），`media_counts` 同步归零；
- 同时不再注入「全引用指南」，改用普通视频提示词指南
  （`_prompt_guide_bundle(..., reference_mode=False)`），并附上
  「NO-REFERENCE OUTPUT RULE」：不得出现引用标签、`subject_definitions`、`retention_analysis`；
- 提示词里写了引用（例如只引用 `图1`/`图2`/`图3`）时行为不变：只把被引用的素材送出去。

### 16. 装了 ComfyUI-MiniMaxH3-Easy 之后，加载器节点变成空白

**症状**：`MiniMax H3 Aicg 加载器` 只剩标题和 `h3_bundle` 输出点，模型、编码器、VAE 全都不见了。

**原因**：两个插件的 Python 节点类都叫 `MiniMaxH3EasyLoader`，ComfyUI 只会保留其中一个。
上游那套只有 5 个控件（没有 LoRA 槽位），而界面脚本已经按本插件的实现把原生控件隐藏了 ——
"面板建不出来"叠加"原生控件已被隐藏"，结果就是一个空白节点。

**修复**：

- 面板只把 4 个核心控件当硬要求；一旦缺控件就**不再隐藏任何原生控件**，直接退回原生下拉；
- 面板初始化或挂载失败时，已被隐藏的原生控件会**自动还原**（`markWidgetVisible`）；
- 面板被其他脚本整表重排 `node.widgets` 摘掉后会自动装回；
- 启动时扫描 `custom_nodes`，发现同类节点包会在控制台打一段中英文提示。

**建议**：两个插件二选一，把不用的那个目录改名成 `xxx.disabled`，再重启 ComfyUI。

### 17. 与上游 ComfyUI-MiniMaxH3-Easy 的节点重名问题（本版重点）

**症状**：装了上游插件之后，本插件节点的左上角标签变成 `MiniMaxH3-Easy`，
加载器面板里的 LoRA 槽位也不见了。

**原因**：两个插件注册的是同一批 Python 节点类名（`MiniMaxH3EasyLoader`、`MiniMaxH3Easy`……），
ComfyUI 只会保留其中一份 —— 谁被顶掉，谁的节点就归到对方插件包名下，自己的字段也会丢。
前端扩展名也一样：两边都叫 `MiniMaxH3Easy`，会互相覆盖。

**修复**：本插件注册的节点 ID 统一加 `AICG3D_H3` 前缀（`MiniMaxH3EasyLoader` → `AICG3D_H3Loader`），
前端扩展改名 `AICG3D.H3EasyUI`，所有按类名匹配节点的代码一次性做换算。

节点 ID 怎么选，启动时自动判断：

| 环境 | 实际注册的节点 ID |
|---|---|
| 没装同名插件（绝大多数用户） | 沿用 `MiniMaxH3Easy*`，以前保存的工作流直接能开 |
| 装了同名插件 | 只用带前缀的 `AICG3D_H3*`，两边各归各的，不再互相顶掉 |

控制台会打印结论。注意第二行那种情况下，旧工作流里写死的 `MiniMaxH3Easy*`
会连接到上游插件上 —— 想继续用本插件的加载器面板和 LoRA 槽位，把上游插件改名成
`xxx.disabled` 再重启即可（本插件已经内置了上游那套节点）。

### 18. 同步上游新功能

`h3easy/nodes.py`、`web/minimax_h3_easy_ui.js` 以旧版上游为基线，
把本插件的改动重新落到新版上游上，带进来这些东西：

- **SelfLift 采样策略**（`sampling_strategies.py`）：低分辨率起手、逐步升到目标分辨率，
  用 `MiniMax H3 Aicg SelfLift` 生成采样方案，接到采样节点的 `sampling_plan` 输入；
- 上下文连续模式新增 **Soft AV Prefix / Hard AV Prefix**，加上原有的 Motion Context、RGB Guide；
- 提示词优化支持**按语言选指南**（中文/英文各一套），并新增 `文戏 / 动作 / 广告` 三个中文方案；
- 提示词优化新增**分段时长**输入：多段时每段各自计时，而不是共用总时长；
- 主节点的 `positive / latent / video_vae / audio_vae / fps` 之外，
  本插件继续保留 `driving_audio` 与 `model` 两条输出；
- 新增上游工作流放在 `workflows/upstream/`（含 SelfLift、Sigma Latent 放大、ClipProj 4B 等实验流程），
  本插件原有工作流不变。

### 19. LoRA 槽位保存后重启要重选（已修）

**症状**：加载器面板里配好 LoRA、权重 0.80，保存工作流；重启 ComfyUI 再打开，
那一行变灰（看起来没启用）、权重显示回 1.00，只能重新选一遍。

**原因**：存档其实是好的（`widgets_values` 里权重就是 0.80）。问题在面板：
ComfyUI 打开工作流是**先建面板、后写存档值**，而面板的同步函数只同步了下拉框里的名字，
没重算「是否启用」和权重，于是那一行一直停在默认状态。CSS 里未启用的行会被压到 45% 透明度，
看着就跟没加载一样。

**修复**：每次同步都按控件当前值重算启用状态与权重；载入工作流后再补同步几次，
并按存档把 LoRA 槽位补回来（只补后端 LoRA 列表里确实存在的权重）。

### 20. 提示词方案：增删只看一个文件夹

「提示词优化设置 → 提示词方案」的列表现在由 `prompt_guides/` 目录扫描得出，
**一个子目录 = 一个方案**，不用改代码、不用重启 ComfyUI：

```text
prompt_guides/
    我的方案/
        guide-zh.md      中文正文（可选）
        guide.md         英文正文（可选，只有一份时中英共用）
        meta.json        可选：{"id": "...", "name_zh": "...", "languages": ["zh", "en"]}
        references/      可选：参考文件（.md / .txt），会一起喂给模型
```

- 删掉目录，方案就从下拉和节点参数里消失；改目录名即时生效（缓存按目录 mtime 失效）。
- `manifest.json` 仍然优先，用来锁住随插件发布的方案 id、显示名与语言，
  所以旧工作流里已经选好的方案不会因为目录改名错位；自建方案不需要动它。
- `h3_general/` 是常驻的通用规则，不会出现在可选方案里。
- 顺带修掉一个老问题：节点控件里存的是**显示名**（例如「动作」），后端原来只认 id，
  等于节点上选的方案会被静默回落成「通用」。现在 id、目录名、显示名三种写法都认。

具体说明见 `prompt_guides/README.md`。

### 21. 渲染器：采样预览图可以关掉

`AICG-渲染器（高级）` 每一步发一张预览图走 ComfyUI 原生预览通道，节点正文里会占一块。
现在默认**不发预览图**，只留底部的百分比进度条（含已用时间与剩余估计），
顺带省掉每步解码 + JPEG 的开销。想恢复预览，把 `h3easy/render_progress.py` 的
`SAMPLE_PREVIEW_ENABLED` 改成 `True` 即可，整套预览通道都还在。

`AICG-渲染器（一采）` 与 `AICG-渲染器（二采放大）` 面板上各有一个「采样预览」开关（默认关）：
开着时各自那段采样的每一步都把中间结果推给同一条原生预览通道，实时采样画面直接显示在这个
节点正文里（右侧图片流面板同样能看到），开了「二采分块采样」时逐块的画面也会推；
关着就和高级渲染器一样只留进度条。
`SAMPLE_PREVIEW_ENABLED` 仍然是模块级总开关，改成 `True` 会把所有渲染节点强制打开。
预览频率由旁边的「预览间隔」控制（默认 1 = 每步一张）：调大就是隔几步推一张，省掉预览解码
与前端刷新的开销、采样更快，整段采样的最后一步始终会推一张。

### 22. 渲染器：跑完自动清理显存与内存

`AICG-渲染器（高级）` 新增参数「运行后清理」，跑完这个节点就收尾（成功和报错都会执行）：

| 选项 | 行为 |
|---|---|
| **卸载模型**（默认） | 把模型一并卸出显存，并回收显存缓存与内存，占用最低；下次运行要重新加载 |
| 释放缓存 | 只把 PyTorch 缓存的显存块还给驱动、回收内存，模型留在显存里，下次跑得快 |
| 不处理 | 保持 ComfyUI 默认行为 |

控制台会打一行前后对比，方便确认效果：

```text
[MiniMax H3 Aicg] 渲染结束已清理（卸载模型）：内存 25.1G，显存 17.3G(保留 18.0G) -> 内存 18.4G，显存 0.2G(保留 0.4G)
```

长视频渲染一跑就是几分钟，跑完显卡还占着的情况很常见，所以默认选了「卸载模型」；
要连着跑多个种子的话切成「释放缓存」更划算。

### 23. 加载器：VAE 槽位默认值改成 H3 专用 VAE（已修）

**症状**：新加的 `MiniMax H3 Aicg 加载器` 直接跑就报
`MiniMax H3 Loader video VAE slot must contain a video VAE (latent_dim=3 ...), but 'ae.safetensors' is not a video VAE`。

**原因**：两个 VAE 槽位的下拉框列的是 `models/vae` 里的**全部**文件（社区改名、挪目录都能选中），
但一直没给默认值 —— ComfyUI 就选列表第一项，按文件名排序常常落到音频 VAE 或 `ae.safetensors`
这类普通图像 VAE 上，直到加载时才被角色校验拦下。

**修复**：

- 列表仍然原样列出 vae 文件夹的全部文件，但按角色把 H3 视频 / 音频 VAE 排到**最前**
  （`_vae_choices(role, fallback)`），新节点默认就是 `minimax_h3_video_vae_fp16.safetensors`
  和 `minimax_h3_audio_vae_fp32.safetensors`；
- 两个槽位补上 `default` 与提示文案（视频 VAE `latent_dim=3`，音频 VAE `latent_dim=2`）；
- 报错信息里直接点名该选哪个文件。

已经存了错误 VAE 的旧工作流不会自动改，把两个槽位手动换回
`minimax_h3_video_vae_*` 与 `minimax_h3_audio_vae_fp32.safetensors` 即可。

### 24. 二采放大拆成两个节点：AICG-渲染器（一采）+ AICG-渲染器（二采放大）

二采放大原先收成一个节点，只能整条链路一起跑。现在拆成两个各自独立的节点，
画布上仍然是一条线，用不用二采自己挑：

```text
主节点 ──h3_context──> AICG-渲染器（一采）──成片视频──> SaveVideo
                             │
                             └──一采数据──> AICG-渲染器（二采放大）──成片视频──> SaveVideo
```

| 节点 | 干什么 | 输入 / 输出 |
|---|---|---|
| `AICG-渲染器（一采）`（`MiniMaxH3EasyRenderPass1`） | 采样 -> 解码 + 合成，只跑一采 | 进：`h3_context`；出：`成片视频`、`一采数据` |
| `AICG-渲染器（二采放大）`（`MiniMaxH3EasyRenderPass2`） | 拆 AV latent -> Latent 3D 放大 -> 拼回 AV latent -> 二采条件 -> 二采 -> 解码 + 合成 | 进：`一采数据`；出：`成片视频`、`一采成片` |

只想要一采：一采节点接上 `SaveVideo` 就行，二采放大节点整条删掉。
想接着放大精修：把一采的 `一采数据` 接到二采放大节点的 `一采数据` 输入，
一条线串下去，画布上不再摊开十来步。

**AICG-渲染器（一采）**

| 参数 | 说明 |
|---|---|
| 种子 / 采样器 / 调度器 / 步数 / 降噪 | 与 `AICG-渲染器（高级）` 同一套采样 |
| 采样预览 | 开：一采每一步都推一张中间结果到 ComfyUI 原生预览通道，实时采样画面显示在节点上；关：只留底部进度条。默认关 |
| 预览间隔 | 每隔多少步推一张预览图（默认 1 = 每步都推）。调大省开销、采样更快；最后一步始终会推，不会看不到成图。只在「采样预览」开着时显示 |
| 运行后清理 | 同 `AICG-渲染器（高级）`。一采跑完就卸模型的话，二采放大还得重新载一次；两个节点连着跑时建议一采选「释放缓存」、二采放大保持「卸载模型」 |

**AICG-渲染器（二采放大）**

| 参数 | 说明 |
|---|---|
| 二采种子 / 二采降噪 | 降噪 0.4~0.6 最稳，越大重画越多（放大出来的细节也越容易被改掉） |
| 二采分块采样 / Tile 宽度·高度·重叠区·接缝渐变 | 开：二采按空间切块逐块采样再拼回，显存只跟单块有关（长片 / 放大后不容易爆显存）；关：整幅一次跑完。默认关，关着时后面四个 Tile 参数自动收起 |
| 采样预览 / 预览间隔 | 同上一张表，作用在二采这一段 |
| Latent 放大器 / 放大倍数 | 倍数 1.0 = 不放大，只按原分辨率跑一遍二采 |
| 放大设备 / 放大精度 / 时间分块放大 | 16G 显存建议 cuda + fp16 + 开分块 |
| 附带一采成片 | 开：额外解码一采 latent，从 `一采成片` 输出一份对照成片（更慢更占显存） |
| 运行后清理 | 同 `AICG-渲染器（高级）` |

二采那一段的采样器 / 调度器 / 步数沿用一采那套（面板上仍然列着，方便单独调），
只有 seed 与降噪是分开的。

几点实现上的取舍：

- 两个节点之间传的是一条自定义类型 `AICG3D_H3_PASS1` 的线，里面装
  `{"latent": 一采 AV latent, "context": H3 上下文}`；上下文（VAE、关键帧、驱动音轨）不塞进
  LATENT 字典，避免下游 `latent.copy()` 把上下文一起搅进去。
- 音频那一路不放大，原样拼回 AV latent 再进二采，二采把音画一起精修。
- 二采分块（`tiled_sampling`）直接复用「分段二采」里已经跑熟的 `tiled_low_vram`：整幅先出一张
  噪声再按坐标切给每一块（块间噪声连续）、接缝按 overlap 淡入淡出、每块跑完跟已拼好的邻块
  对齐一次通道基线；音频不参与分块重采样，原样带过。默认 512 / 512 / 128 / 32 像素，
  都必须是 32 的倍数，重叠要小于分块宽高、接缝渐变不能大于重叠。显存吃紧时把它打开，
  代价是比整幅慢一点。
- 采样预览（`sample_preview`）走的是 ComfyUI 原生预览通道，图在运行时推给前端，跑完不留结果，
  也不会变成节点输出 —— 想留画面请用 `附带一采成片` 或外接解码节点。预览解码用 H3 latent
  自带的 RGB 因子 / `taeh3` 预览解码器，只解第一帧，开销很小。
- 放大前先把 H3 主干请出显存（`unload_model_and_clones`）再加载放大器，二采时 ComfyUI
  会自动把主干载回来，避免两个大模型同时占显存。
- 进度条按阶段推进：一采节点是 采样 90% -> 解码合成 10%；二采放大节点是
  放大 12% -> 二采 78% -> 解码合成 10%，文字跟着阶段变
  （`render_progress.py` 新增 `begin_stage` / `update_stage`，旧的两个接口行为不变）。
- 分母是 `second_pass_denoise`：采样器原来的 `denoise` 没参与 sigma 计算（等于永远按 1.0 跑），
  二采必须靠它，所以顺带修了 —— 现在与原生 `BasicScheduler` 的 denoise 行为逐项对齐
  （simple / normal / karras 三套调度器、多组步数都核对过）。

配套工作流 `14.AICG3D_渲染器_一采二采_拆分.json`：一份里同时演示「只用一采」与
「一采 + 二采放大」两条接法。`13.AICG3D_渲染器_二采_单节点.json` 是老的单节点版，
控件表已经对不上，请删掉重拖；12 号那份拆开版的保留着，想单独调某一步、或者想看中间 latent 时用。

### 25. 无限段落顺序生成：段落自由增减 + 自动拼接

把「顺序生成长视频」做成一套可以拆着用的独立节点，画布上一条线连到底：

`MiniMax H3 Aicg 加载器` → **`MiniMax H3 Aicg 无限段落顺序生成（全局设置）`** → **`MiniMax H3 Aicg 视频段落`**（想加几段加几段）→ **`MiniMax H3 Aicg 最终合成视频`** → `SaveVideo`

- **全局设置**（一个节点管全部段落）：`sequence_config` 只在**第 1 段**接一次，后面的段落顺着
  `previous_segment` 自动继承（想给某段换配置，单独把线接到那一段即可），里面是全局的
  分辨率、宽高比、帧率（H3 原生 24fps 锁定）、参考图尺寸、采样器 / 调度器 / 步数 / 降噪；
  分辨率只有预设档，宽高由「分辨率 + 宽高比」算出来、在节点上只读显示（如 `1920x1080`），不用手填。
  其中这几项是重点：
  - **衔接帧数** `1`~`20`：每段开头接住上一段结尾多少帧画面。H3 原生时间栅格只有
    `5 / 22 / 39 / 56 / 73`，所以填 `1~5` 按 5 帧跑、填 `6~20` 按 22 帧跑（越大越稳、越慢），默认 `5`。
  - **衔接方式**：`尾帧续写（latent）`＝直接拿上段尾部的 latent 当上下文，无损最快
    （默认，和 Motion Context 同一套机制）；`尾帧画面（RGB）`＝把上段尾部画面重新编码成 Guide，
    像素更贴，但每段多一次解码。
  - **显存收尾**：默认「释放缓存」，每段跑完把 PyTorch 缓存显存还给驱动、模型留在显存里，
    下一段接着跑最快；显存实在紧张再切「卸载模型」（每段重载权重，长片会明显变慢）。
  - **音频模式**：`生成音频`（默认）＝每段自己出声音；`数字人（锁定音频）`＝素材库里**那一条**音频
    当驱动音轨，按整条时间轴切片后锁进每一段（音频那一半不参与去噪，画面跟着音频走），
    最终成片也用这条音轨；没有画面参考的段落自动退回纯文字出片。
    加这一档是因为：素材库里只放音频、提示词里只写 `@音频1` 时，参考生视频会直接报
    `needs an image or video in addition to audio`（音频不能单独当参考），切到数字人模式就能跑。
    整条链要共用同一条音频，中途换成另一条会在合成时明确报错，不会拼出一条音画对不上的片子。
  - **提示词优化设置**：点这一行打开提示词优化面板（优化方式 / API 地址 / API Key / 模型名 / 本地模型）。
    段落提示词框里的 `✦` 用的就是这份设置；没配好时点 `✦` 会直接把这个面板打开。
- **视频段落**：一段一个节点，参数只有 `prompt` / `seconds` / `seed`，面板上没有多余字段；
  要参考图 / 参考视频就从 `MiniMax H3 Aicg资源库` 拉一条线到**第 1 段**的 `media`，后面的段落
  自动沿用同一份素材；在素材库里点一张素材，引用会插进**光标所在的那一段**提示词的光标处，
  而不是画布上碰巧选中的那个节点（提示词框支持 `@` 补全）。
- **最终合成视频**：只接最后一段的 `segment`，它自己顺着链找回前面每一段，逐段解码、
  逐段写进同一个编码器（音画一起拼，内存只跟单段有关），存到 `output` 目录，同时输出 `VIDEO`。

段的增减就是改连线：

- 加一段：复制一个 `视频段落`，上段的 `segment` → 新节点的 `previous_segment`，
  新节点的 `segment` → `最终合成视频` 的 `final_segment`。
- 减一段：删掉中间那段，把前一段的 `segment` 直接接到后一段的 `previous_segment`。
- 只用一段：一个 `视频段落` 直接接 `最终合成视频`。

增删段落都只动 `previous_segment` / `segment` 这条链，`sequence_config` 和素材线不用管：
20 段的工作流画布上也只有一条主线，不会织成蜘蛛网。

配套工作流 `15.AICG3D_无限段落顺序生成.json`：预置三段中文分镜提示词（起手 → 中段 → 收尾），
默认 `480P / 16:9 / 每段 5 秒 / 20 步 / 衔接 5 帧`。采样预览默认关，想看正在采样那段的实时画面，
就在全局设置里把「采样预览」改成「开」，`preview_interval` 控制每隔多少步推一张。
每段结束都会打印显存 / 内存收尾日志，可以据此判断显存够不够。

### 26. 重开工作流时节点参数整体串位（已修）

症状：昨天还好好的工作流，今天打开后全局设置里「帧率」变 0、「衔接帧数」跑偏，二采放大节点
直接报红（采样器里是一个种子数字、调度器里写着 `fixed`、步数里写着 `res_multistep`），
把节点删掉重拖又正常。

原因不在插件里，是 ComfyUI 前端自己的一处不一致：

- 保存时 `serialize()` 按 widget 的**原始下标**写 `widgets_values`，中间夹着提示词框、
  画布尺寸行这类 `serialize:false` 的 DOM 控件就留一个空洞（`null`）；
- 还原时 `configure()` 却只按顺序数**可序列化**的控件，于是从空洞开始，后面每个参数都错一格。
  控件列表本身增删 / 换序（比如二采拆成一采 + 二采）同样会让旧存档整体错位，越靠后的控件错得越多。

现在所有 `AICG3D_H3*` 节点在还原存档前会先自查一次：拿存档自带的 `widgets_values_named`
（控件名 → 值）跟按位置读出来的值比一遍，对不上就改按控件名还原，并把位置数组重排成没有空洞的
版本。**打开旧工作流即自动修好，不用重拖节点、也不用重存一次**；本来就没问题的存档一个值都不会动
（命名值本来就是空字符串、而位置值非空时保留位置值，避免把素材加载器里的素材这类看得见的数据清掉）。

升级后刷新一次浏览器（F5）即可，扩展脚本本身没有强缓存。

### 27. 全局设置新增「显存档位」：8G / 12G / 16G / 自动

`无限段落顺序生成（全局设置）` 面板最下面多了一行 `显存档位`，四挡：`自动（按显卡）`（默认）/ `16G` /
`12G` / `8G`。这一挡不是装饰：它决定画布上限、什么时候把大模型卸出显存、采样预览愿意花多少显存 ——
换块显卡不用再手调一堆参数。

四挡各自实际做的是：

- **自动（按显卡）**：读一次显卡总显存自己选一挡（≥15GB 走 16G 挡、≥11GB 走 12G 挡、其余走 8G 挡）。
  本机（RTX 5070 Ti，16303MB）自动判成 16G 挡。
- **16G**：**完全等于原来的行为**，一项限制都不加（它同时也是默认值，老工作流打开后就是它）。
- **12G**：画布分辨率上限 `720P`（选了更高会自己降下来并在日志里说明）、条件算完进采样之前把文本编码器
  （Qwen3VL 32B，25GB）放回内存、解码大张量之前把主干卸出显存、采样预览最小间隔 ≥2 步、预览最长边压到 384。
- **8G**：在 12G 的基础上再加三条 —— 画布上限压到 `480P`、预览最长边压到 256 且改用轻量 latent RGB 因子
  （不再跑一次 VAE / TAESD 解码）、**衔接方式强制按 latent 跑**（RGB 尾帧每段都要整段解码一次，太吃显存，
  面板上哪怕选了 RGB 也会自动降级并在日志里说明原因）。

几处配套细节：

- 档位压了分辨率时，节点上那行只读画布尺寸会写成 `864x480（显存档位按 480P 跑）`，
  免得面板显示的尺寸和实际跑的对不上；改「分辨率」或「宽高比」时这行会跟着刷新。
- 每次生效都会打印档位名和它做了什么，例如
  `显存档位「12G 档」：采样前已把文本编码器放回内存，下一段用到时再自动加载`，
  配合每段结尾的显存 / 内存日志就能判断还差多少。
- 卸掉的只是**显存占用**，模型对象还留在内存里，ComfyUI 下次用到会自己载回来；16G 挡完全不触发这些动作，
  所以老工作流的运行结果一点都不会变。
- 要说明的是：H3 主干（int8）自己就有 31.7GB，比任何一挡的显存都大，ComfyUI 一直是按「权重放内存、
  按需搬进显存」在跑。档位能压的是叠加在它之上的那部分（画布 / 编码器 / 解码 / 预览），
  所以 8G 挡是把峰值压到最低，而不是把主干塞进显存。
- 这一行只加在 `无限段落顺序生成（全局设置）` 上；`AICG-渲染器（一采）` / `AICG-渲染器（二采放大）`
  那两个节点的控件没动。

Python 侧改动需要重启 ComfyUI 才生效，前端刷新浏览器（F5）即可。

## 鸣谢

本插件的骨架、提示词引擎与提示词规范都不是我写的，来源说清楚比什么都重要：

| 来源项目 | 作者 | 贡献 |
|---|---|---|
| `ComfyUI-MiniMaxH3-Easy`（MIT） | nkxx188 | 整个骨架：H3 主节点、素材加载器、渲染器，以及把几十个节点收敛成一个主节点的设计 |
| `Goohai-MiniMax-H3_Integration`（GPL-3.0-or-later） | goohai（B站 孤海FOTO） | 提示词优化引擎（云端 API + 本地 GGUF 双引擎）与音视频潜空间解码 |
| `MiniMax-AI/MiniMax-H3`（MiniMax H3 Community License） | MiniMax | H3 五种生成模式的提示词规范与官方风格技能 |
| `comfyUI-llama-TE`（上游未附许可证） | tl2012tl | 本地推理与多轮对话的开源工作；**本版未包含其代码**，但开发中参考过它的设计 |
| 中文 AI 创作社区的提示词合集 | 各原始作者 | `prompt_presets/` 的 144 个模板，整理自社区公开流传的文档合集 |

完整鸣谢见 `ACKNOWLEDGEMENTS.md`，发布版文案见 `RELEASE.md`。
把别人的代码说成自己的，比用别人的代码严重得多 —— 所以这一段单独写在这里。

## 开源许可

本插件自有代码按 **GPL-3.0-or-later** 发布（因为合并了 GPL-3.0-or-later 的
`Goohai-MiniMax-H3_Integration`）。许可证全文见仓库根目录 `LICENSE`。

| 来源项目 | 许可证 | 原始作者 | 原始仓库 |
|----------|--------|---------|---------|
| `ComfyUI-MiniMaxH3-Easy` | MIT | nkxx188 | https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy |
| `Goohai-MiniMax-H3_Integration` | GPL-3.0-or-later | goohai | https://github.com/goohai/Goohai-MiniMax-H3_Integration |
| MiniMax H3 官方提示词技能与方案 | MiniMax H3 Community License | MiniMax | https://github.com/MiniMax-AI/MiniMax-H3 |
| `comfyUI-llama-TE`（已移除，未包含其代码） | 上游未附许可证 | tl2012tl | https://github.com/tl2012tl/comfyUI-llama-TE |

- 许可证原文：`third_party/`
- 逐项声明、修改说明与使用限制：`THIRD_PARTY_NOTICES.md`
- 对外发布文案（含鸣谢与免责声明）：`RELEASE.md`
- 完整鸣谢名单：`ACKNOWLEDGEMENTS.md`
- `skills/` 与 `prompt_guides/` 中的 MiniMax 官方内容**不属于** GPL 作品的一部分，
  适用 MiniMax H3 Community License（含地域限制与商业条款）。不接受这些限制时，
  `git rm -r skills prompt_guides` 即可，插件仍能正常运行。
- `prompt_presets/` 未标注授权，版权归各原始作者；不需要时 `git rm -r prompt_presets`。

### 隐私与联网

提示词优化可以调用第三方 API（OpenAI / Gemini / OpenRouter / DashScope / SiliconFlow /
RunningHub），需要你自备密钥；启用后提示词与所选附件素材会发送到对应服务。
不配置密钥、使用本地 GGUF 模式时不会对外发送任何内容。完整列表见
`THIRD_PARTY_NOTICES.md` 第 7 节。

## 安装

放到 `ComfyUI/custom_nodes/comfyui-AICG3D`，重启 ComfyUI 即可。

本插件已经内置了上游 `ComfyUI-MiniMaxH3-Easy` 的节点，**不要再装同名插件**：
两边节点类同名，同时启用会让加载器面板变成空白（见下文第 16 条）。

## 目录

```text
comfyui-AICG3D/
├── __init__.py          合并后的节点入口
├── aicg3d/              公共层：注册表、配色、技能库、HTTP 接口
├── h3easy/              H3 Aicg 节点源码（含 aicg3d_sampler.py / h3_latent_upscaler.py）
├── h3goohai/            提示词优化引擎与 AV 解码（源自 Goohai-MiniMax-H3_Integration）
├── prompt_guides/       H3 场景提示词方案（增删方案只需要动这个目录）
├── prompt_presets/      提示词模板库（144 个模板 / 8 个分类）
├── skills/              技能包
├── third_party/         第三方许可证原文
├── web/                 全部前端脚本与主题
├── workflows/           原始示例工作流
├── LICENSE              GPL-3.0 全文
├── RELEASE.md           发布声明（含鸣谢与免责声明）
├── ACKNOWLEDGEMENTS.md  完整鸣谢
└── THIRD_PARTY_NOTICES.md  第三方组件与许可证声明
```

## 接口

| 路径 | 说明 |
|---|---|
| `GET /aicg3d/api/meta` | 版本与资源数量 |
| `GET /aicg3d/api/skills` | 技能目录 |
| `GET /aicg3d/api/skills/{id}` | 技能正文与 reference 列表 |
| `GET /aicg3d/api/presets` | 提示词模板目录（分类 + 144 条模板摘要） |
| `GET /aicg3d/api/presets/{id}` | 单条模板正文与元信息 |
| `GET /aicg3d/api/prompt-guides` | 提示词方案列表（来自 `prompt_guides/` 目录扫描） |
| `GET /aicg3d/api/loras` | LoRA 列表（含体积、底模、触发词、预览图） |
| `GET /aicg3d/api/media` | ComfyUI 输入目录里的素材 |
