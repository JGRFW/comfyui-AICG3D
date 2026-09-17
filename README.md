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
├── prompt_guides/       H3 场景提示词方案
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
| `GET /aicg3d/api/loras` | LoRA 列表（含体积、底模、触发词、预览图） |
| `GET /aicg3d/api/media` | ComfyUI 输入目录里的素材 |
