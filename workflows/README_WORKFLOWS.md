# MiniMax H3 Aicg 工作流说明

## 中文说明

使用本文件夹中的工作流前，请先安装所需插件，并下载对应模型。

### 可能需要安装的插件

- [ComfyUI-MiniMaxH3-Easy](https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy)
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- [Comfyui-Memory_Cleanup](https://github.com/LAOGOU-666/Comfyui-Memory_Cleanup)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use)

也可以在 ComfyUI Manager 中搜索插件名称安装。安装或更新后请重启 ComfyUI。

`3.MiniMax_H3_Easy_Selected_Video_Refine.json` 里上游自带的 `Fast Groups Bypasser (rgthree)` 分组开关节点已移除：新版 rgthree 不再提供这个节点，留着只会报「缺失节点」；其余连线与参数一律未改，需要分组开关时自己拖一个 `Fast Groups Muter` 之类的节点即可。

### 模型与资源

工作流需要的插件、模型和相关资源：

<https://pan.quark.cn/s/8be70c7581e6?pwd=6LmC>

- [LightX2V MiniMax H3 Turbo（正式版 8-step LoRA）](https://huggingface.co/lightx2v/Minimax-h3-Turbo)
- [MiniMax H3 FL2VA 剪枝 W4A8（minimax_h3_fl2va_pruned_w4a8_mixed.safetensors）](https://huggingface.co/Kijai/MiniMax-H3-experimental)

不同工作流需要的模型可能不同，请按照工作流中的加载器选择对应文件。如果列表中找不到模型，请检查模型是否放入了正确的 `ComfyUI/models` 子目录，然后刷新或重启 ComfyUI。

部分工作流还需要额外的 LoRA 或其他自定义节点，具体以工作流中的节点为准。

### 上下文分段模式

节点 `MiniMax H3 Aicg Context Segments` 用于多分段连续创作：在提示词中用单独一行 `---`（或输入 `~`）划分分段，在“分段秒数”中按 `10,8,5` 的形式填写每段时长，素材仍连接该节点的 Media 口，各段通过显式媒体标签声明自己使用的素材。Latent/RGB 引导使用 `5、22、39、56、73`；柔性/硬性 AV 前缀使用独立的 `39、90、141` 网格，不能混用。RGB 引导会把上一段尾部作为一个连续多帧 Guide 块，并在编码前对上下文加入渐进式刷新噪声，以减轻长链画质劣化。上下文条件通过 ComfyUI 原生 Guide 数据结构传递；每段自己的参考媒体仍独立进入该段的 `minimax_refs`。柔性 AV 保持画面重叠前缀，只对音频前缀末端渐进释放；硬性 AV 同时严格保持视频和音频重叠前缀。`音频模式` 默认为生成音频；切换为 `数字人` 并连接且只连接一条音频时，该音频按累计时间轴切片并锁定到每段 AV latent，最终预览和视频也使用这条完整音轨；若未提供音频，则自动回退到普通生成音频/参考生视频流程，不会报错。图片/视频参考仍按分段独立生效。需要逐段控制和局部重跑时，把 `H3 Context`、`Model`、`SAMPLER`、`SIGMAS` 接入 `MiniMax H3 Aicg Sample Setup`，再把它接到第一个 `MiniMax H3 Aicg Segment Step`。后续 Step 只串联 `Previous segment`，不再重复连接这些公共输入；分段顺序由串联关系自动确定。最后一个 Step 接到 `MiniMax H3 Aicg Segment Collect`，再接 `MiniMax H3 Aicg Segment Decode`。常规整链仍可直接使用 `MiniMax H3 Aicg Segment Sample`。需要二采时，将第一采 `Segments`、同一个 `H3 Context`、SAMPLER/SIGMAS 接到 `MiniMax H3 Aicg Segment Refine`；`latent_upscale` 模式复用一采的 H3 模型，只额外加载 3D latent upscaler，不再加载 W4A8 二采模型。像素放大或需要独立二采模型时，才接入另一套模型。该节点会逐段重建各自的提示词和参考媒体条件，并把上一段二采尾部传给下一段。再将二采节点的输出接到第二个 `MiniMax H3 Aicg Segment Decode`，保存其 `Preview`。这样不会把整条片段先合成成一个全局 latent，也不会把不同分段的参考媒体混在一起；二采后的音频默认沿用第一采音频，数字人模式则沿用 Media 驱动音频时间线。

`Segment Refine` 的“二采执行方式”默认是“常规模式”。显存不足而需要更高分辨率时，选择“Low VRAM Tile”：它仍以用户的上下文分段为时间单位，只把当前分段的空间 latent 切成有重叠的 tile 二采。每个 tile 使用从同一整段噪声场裁切的坐标噪声，接缝区域先冻结再渐变融合；提示词、每段 `@` 媒体、上下文尾帧和音频模式都不会混入其他分段。Tile 越小显存越低，但二采次数和耗时越高；默认 `512 / 512 / 128 / 32` 分别是宽、高、重叠和接缝渐变（像素）。

`7.MiniMax_H3_Easy_Context_Segments_Control.json` 是逐段控制示例：先用一个 `MiniMax H3 Aicg Sample Setup` 接收公共的 Context、Model、SAMPLER、SIGMAS，再接 3 个 `MiniMax H3 Aicg Segment Step`。第一次运行仍会完整生成；需要时再利用 ComfyUI 原生缓存进行局部重跑。第一个 Step 接 Setup，后两个只按 `1 → 2 → 3` 串联 `Previous segment`；最后一个 Step 单独接 `Segment Collect` 和 `Segment Decode`。每个 Step 的 Seed 独立可改，分段顺序不需要手填；只改第 N 段时，前面的段可以命中缓存，第 N 段及其后续段才会重新采样。常规整链的 `Segment Sample` 和 `Segment Refine` 中，`Segment seeds` 默认填 `default`，表示所有分段沿用主 Seed；如需独立控制，可填写数字 Seed 列表，列表少于分段数时，末尾剩余分段自动沿用主 Seed，不能把 `default` 和数字混在一起。需要临时改某一段提示词时，可选接入一个外部 STRING 到该段的 `Prompt override`，不接则继续使用上下文节点中的分段提示词和 `@` 参考素材。这个节点只负责单个分段的处理，二采仍使用现有的 `Segment Refine` 或已选视频二采节点，避免把工作流混成一团。

### 插件融合冒烟测试（8.AICG3D_Smoke_Test.json）

这个工作流只用来验证本插件自身，不接外挂 LoRA，也不依赖加速补丁，链路是：

`MiniMax H3 Aicg Loader`（1 个主模型 + 4 个内置 LoRA 槽位）→ `MiniMax H3 Aicg`（参考生视频，提示词里 `@图片1`、`@图片2` 指向素材加载器）→ `MiniMax H3 Aicg Output` → `BasicGuider` / `BasicScheduler` / `RandomNoise` / `KSamplerSelect` → `SamplerCustomAdvanced` → `MiniMax H3 AV Decode T8` → `VHS_VideoCombine`（带音频的 mp4，输出到 `output/AICG3D/H3_SmokeTest*`）。

旁支 `AICG3D 技能加载器`（选“3D动画短片生成器”）→ `ShowText`，用来确认技能库能取到正文。

测试要点：

- 加载器面板应显示 1 个主模型、4 个 LoRA 槽位和“LoRA N”汇总徽标。本工作流只启用前 2 个 LoRA（第 3、4 槽为“不使用”），用来验证“不再外挂模型加载、内置 4 槽按顺序叠加”。
- 参考模型留空（“双模型”关闭）时，参考生视频会自动复用主模型。
- 素材加载器里放了 `01.png`、`02.png`。单击素材卡片就会把 `@图片N` 写进主节点提示词；提示词里已预置两个引用，可以先删掉再点一次复现。
- 首次跑通建议保持 `480P / 16:9 / 3 秒 / 8 步`，确认无误后再改分辨率和时长。
- 需要测视频、音频引用时，把文件放进 `ComfyUI/input`，在素材加载器里添加，再点卡片插入 `@视频N` / `@音频N`。

### 一条龙出片测试（10.AICG3D_渲染器_测试.json）

用来验证"主节点一条线 + AICG-渲染器（高级）"这条最简链路：

`MiniMax H3 Aicg Loader` → `MiniMax H3 Aicg`（参考生视频）→ **`AICG-渲染器（高级）`** → `SaveVideo`

`MiniMax H3 Aicg` 的 `H3 Context` 输出直接进渲染器；渲染器内部完成
采样 + 视频/音频解码 + 合成，只输出一条 `VIDEO`，接原生 `SaveVideo` 即可出片。
主节点第 1 个输出 `Model` 是给上游老工作流（`2.`~`7.`）用的，这条链路不需要它。
旁支 `AICG3D 技能加载器` → `ShowText` 用于确认技能库正文。

测试要点：

- 主节点有 **2 个输出点**：第 1 个 `Model`、第 2 个 `H3 Context`（与上游 `ComfyUI-MiniMaxH3-Easy` 一致，二采工作流靠它取模型）。本工作流只用 `H3 Context`，`Model` 悬空不影响运行。
- 媒体包里放了 `01.png`、`02.png`、`03.png` 三张素材，提示词只引用了
  `<Picture 1>` 和 `<Picture 3>`。点一次 `✦` 优化：下发给优化器的素材应该只有 2 张，
  优化结果里不应该出现 `<Picture 2>`。
- 把主节点模式切到 `图生或首尾帧`，素材库 / 技能库按钮和 `@` 补全仍然可用，
  点素材卡片能把 `@` 引用写进提示词。
- 优化成功后应能听到一声提示音。
- 渲染器控件：`Seed / 采样器 / 调度器 / 步数 / 降噪`；首次跑通建议 `8 步`，
  与加载器里的 Turbo LoRA 匹配。

### 全链路测试样板（11.AICG3D_测试样板.json）

上手用的“照抄就能跑”样板，把插件里的新节点和融合后的加载器串成一条最短链路：

`MiniMax H3 Aicg 加载器` → `MiniMax H3 Aicg`（参考生视频）→ **`AICG-渲染器（高级）`** → `SaveVideo`

提示词侧走 `AICG3D 提示词模板` → 主节点 `prompt`，旁支 `AICG3D 技能加载器` → `ShowText`。

测试要点：

- 画布左侧有三个 Note（看这里 / 提示词模板用法 / 技能分支），第一次跑先照着读一遍。
- 加载器默认只开 1 个 LoRA 槽（第 1 槽 Turbo 4-step，第 2 槽写实 LoRA 0.5），
  需要更多就点面板下方的 `+` 加槽位。
- 素材库预置 `01.png`、`02.png`、`03.png`，主节点提示词用 `<Picture 1/2/3>` 引用；
  点素材卡片也能把 `@` 引用插进提示词。
- 提示词模板选了「H3 专题｜前置词｜3D动画短片制作助手」，它的 `提示词` 输出直接接主节点
  `prompt`：换模板、改 `task` 都立刻生效；想自己手写就删掉这条线。
- 技能分支是可选的：`AICG3D 技能加载器` 的 `提示词` 接 `ShowText` 看正文，
  要更细的分镜脚本时再把这条线接到主节点。
- 首次跑通建议 `480P / 16:9 / 3 秒 / 20 步`（渲染器默认），确认无误再提高分辨率或时长。

---

# MiniMax H3 Aicg Workflow Guide

## English

Before using any workflow in this folder, install the required custom nodes and download the models used by that workflow.

### Required custom nodes

- [ComfyUI-MiniMaxH3-Easy](https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy)
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- [Comfyui-Memory_Cleanup](https://github.com/LAOGOU-666/Comfyui-Memory_Cleanup)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use)

You can also install them by searching for their names in ComfyUI Manager. Restart ComfyUI after installing or updating custom nodes.

The upstream `Fast Groups Bypasser (rgthree)` group-toggle node has been removed from `3.MiniMax_H3_Easy_Selected_Video_Refine.json`: recent rgthree releases no longer ship that node, so keeping it only produced a "missing node types" warning. Every other link and setting is untouched; add a `Fast Groups Muter`-style node yourself if you want group toggles.

### Models and assets

The plugins, models, and related assets used by the workflows are available here:

- [LightX2V MiniMax H3 Turbo (official 8-step LoRA)](https://huggingface.co/lightx2v/Minimax-h3-Turbo)
- [MiniMax H3 FL2VA pruned W4A8 (minimax_h3_fl2va_pruned_w4a8_mixed.safetensors)](https://huggingface.co/Kijai/MiniMax-H3-experimental)

Model requirements may differ between workflows. Select the matching files in each workflow's loader node. If a model is not listed, place it in the correct `ComfyUI/models` subdirectory, then refresh or restart ComfyUI.

Some workflows may also require additional LoRAs or custom nodes. Please check the nodes included in the workflow.

### Context Segment mode

The `MiniMax H3 Aicg Context Segments` node covers multi-shot creation. Split the prompt into shots with a standalone `---` line (or type `~`), fill "Segment seconds" as `10,8,5`, keep media linked to the node's Media port, and declare per-shot media with explicit tags. The shared context media library accepts up to 45 resources (27 images, 9 videos, 9 audio clips), while each segment still sends only its own referenced subset and keeps the normal per-segment H3 budget. Latent/RGB guide modes use `5, 22, 39, 56, 73`; Soft/Hard AV prefix modes use a separate `39, 90, 141` grid. RGB continuation uses ComfyUI's native Guide data structure as one continuous multi-frame block, and each segment's references remain in its own `minimax_refs` payload. Soft AV keeps the picture prefix exact and releases only the tail of the carried audio prefix; Hard AV holds both streams strictly. `Audio mode` defaults to generated audio; in `Digital Human`, connect exactly one audio resource through Media to drive the sequence. It is sliced on the cumulative timeline, locked into each segment AV latent, and used as the final soundtrack, while visual references remain segment-local. When no audio is connected, the node automatically falls back to its normal generated-audio/reference path. For per-segment control and local reruns, connect `H3 Context`, `Model`, `SAMPLER`, and `SIGMAS` to **MiniMax H3 Aicg Sample Setup**, then connect its output to the first **MiniMax H3 Aicg Segment Step**. Chain only `Previous segment` on later Steps; their order is inferred automatically from the chain. Connect the final Step to **MiniMax H3 Aicg Segment Collect**, then to **MiniMax H3 Aicg Segment Decode**. The regular one-node chain remains available as **MiniMax H3 Aicg Segment Sample**. For a second pass, connect the first-pass `Segments`, the same `H3 Context`, and SAMPLER/SIGMAS to **MiniMax H3 Aicg Segment Refine**. In `latent_upscale` mode, reuse the first-pass H3 model and load only the 3D latent upscaler; do not add a separate W4A8 second-pass model. Pixel resize or an intentionally separate second model remains available as another mode. The refine node rebuilds each segment's prompt and reference-media conditioning independently and passes the previous refined tail into the next segment. Connect the refine output to a second **MiniMax H3 Aicg Segment Decode** and save that `Preview`. This avoids a global latent second pass and prevents references from different segments from being mixed; second-pass audio follows the first-pass timeline, or the Media driving timeline in Digital Human mode.

`Segment Refine` defaults to `Standard mode`. Select `Low VRAM Tile` when a higher-resolution second pass does not fit in VRAM. User context segments remain the temporal units; only the current segment's spatial latent is sampled as overlapping tiles. Tiles crop one shared full-segment noise field by coordinate, freeze then fade their seams, and retain the segment's own prompt, `@` media, carried context tail, and selected audio mode. Smaller tiles reduce VRAM but increase the number and duration of sampling runs. The default `512 / 512 / 128 / 32` values are tile width, height, overlap, and seam fade in pixels.

`7.MiniMax_H3_Easy_Context_Segments_Control.json` demonstrates per-segment control with one `MiniMax H3 Aicg Sample Setup` for the shared Context, Model, SAMPLER, and SIGMAS, followed by three `MiniMax H3 Aicg Segment Step` nodes. The first run still generates the complete video; selective reruns are optional. The first Step receives Setup; the later Steps only chain `Previous segment` as `1 → 2 → 3`; the final Step alone connects to `Segment Collect` and `Segment Decode`. Each Step has its own seed and the segment order is inferred, not entered manually. If only segment N changes, earlier steps can hit ComfyUI's native cache while segment N and its dependent later steps resample. In the regular `Segment Sample` and `Segment Refine` nodes, `Segment seeds` defaults to `default`, meaning every segment uses the main seed. For independent control, enter a numeric comma-separated list; if it is shorter than the segment count, remaining trailing segments automatically use the main seed. Do not mix `default` with numbers. To temporarily replace one segment's prompt, optionally connect a STRING node to that Step's `Prompt override`; without it, the Context node's segment prompt and `@` media remain in use. This node handles one segment at a time. Use the existing `Segment Refine` or selected-video refine workflow for second-pass upscaling, keeping the graph readable.

### Plugin smoke test (8.AICG3D_Smoke_Test.json)

This workflow exists only to verify the merged plugin itself. It does not use an external LoRA loader or attention patches:

`MiniMax H3 Aicg Loader` (one main model plus four built-in LoRA slots) -> `MiniMax H3 Aicg` (Reference-to-video, with `@` references to the Media Loader) -> `MiniMax H3 Aicg Output` -> `BasicGuider` / `BasicScheduler` / `RandomNoise` / `KSamplerSelect` -> `SamplerCustomAdvanced` -> `MiniMax H3 AV Decode T8` -> `VHS_VideoCombine` (mp4 with audio, saved under `output/AICG3D/H3_SmokeTest*`).

A side branch runs `AICG3D Skill Loader` (3D animation short generator) into `ShowText` so the skill library body is visible.

What to check:

- The loader panel shows one main model, four LoRA slots, and the "LoRA n" summary badge. Only slots 1 and 2 are active here, which verifies the built-in ordered LoRA stack instead of an external model loader.
- Leaving the reference model empty (dual-model switch off) makes reference mode reuse the main model.
- The Media Loader holds `01.png` and `02.png`. Clicking an asset card inserts its `@` reference into the main node's prompt; two references are pre-seeded, so you can delete one and click again to reproduce.
- Keep `480P / 16:9 / 3 s / 8 steps` for the first run, then raise resolution and duration.
- To test video or audio references, drop files into `ComfyUI/input`, add them in the Media Loader, and click their cards to insert `@Video n` / `@Audio n`.


### One-stop render test (10.AICG3D_渲染器_测试.json)

Verifies the shortest chain built around the single output line and the new render node:

`MiniMax H3 Aicg Loader` -> `MiniMax H3 Aicg` (Reference-to-video) -> **`AICG Render (Advanced)`** -> `SaveVideo`

`MiniMax H3 Aicg` feeds its `H3 Context` output straight into the render node; the first `Model` output stays for the upstream workflows (`2.`-`7.`) and is not needed here;
the render node samples, decodes video/audio, and muxes them into a single `VIDEO` output that
connects to the native `SaveVideo`. A side branch runs `AICG3D Skill Loader` into `ShowText`.

What to check:

- The main node shows two output dots: `Model` (1st) and `H3 Context` (2nd), matching upstream `ComfyUI-MiniMaxH3-Easy` (the second-pass workflows take the model from the first one). This workflow only uses `H3 Context`; leaving `Model` unconnected is fine.
- The Media Loader holds `01.png`, `02.png`, and `03.png`, while the prompt references only
  `<Picture 1>` and `<Picture 3>`. Press `+`/`✦` to optimize: only two assets should be sent and
  `<Picture 2>` must not appear in the optimized prompt.
- Switching the main node to "I2V or First/Last Frame" keeps the asset and skill buttons working,
  and clicking an asset card still inserts its `@` reference.
- A short completion sound plays when optimization finishes.
- Render widgets: `Seed / Sampler / Scheduler / Steps / Denoise`; use 8 steps for the first run to
  match the bundled Turbo LoRA.

### Full-chain sample (11.AICG3D_测试样板.json)

A copy-and-run sample that wires the new AICG3D nodes and the merged loader into the shortest chain:

`MiniMax H3 Aicg Loader` -> `MiniMax H3 Aicg` (Reference-to-video) -> **`AICG Render (Advanced)`** -> `SaveVideo`

On the prompt side, `AICG3D Prompt Preset` feeds the main node `prompt`, with an optional
`AICG3D Skill Loader` -> `ShowText` branch.

What to check:

- Three Notes on the left (read me / preset usage / skill branch) explain the flow before the first run.
- The loader opens with a single LoRA slot (slot 1 Turbo 4-step, slot 2 realism LoRA at 0.5);
  press `+` under the panel to add more slots.
- The media library ships `01.png`, `02.png`, `03.png` and the prompt references `<Picture 1/2/3>`;
  clicking an asset card also inserts its `@` reference.
- The preset is 「H3 专题｜前置词｜3D动画短片制作助手」 and its `提示词` output goes straight into
  the main node `prompt`: switching presets or editing `task` takes effect immediately; delete that link to write by hand.
- The skill branch is optional: route `AICG3D Skill Loader` `提示词` into `ShowText` to read the body,
  or into the main node when you want a detailed shot script.
- First run: keep `480P / 16:9 / 3s / 20 steps` (render node defaults), then raise resolution or duration.
