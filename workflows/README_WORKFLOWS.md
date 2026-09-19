# MiniMax H3 Aicg 工作流说明

## 中文说明

使用本文件夹中的工作流前，请先安装所需插件，并下载对应模型。

### 工作流总览

| # | 文件 | 干什么用 | 关键链路 | 主要模型 / LoRA | 额外依赖 |
|---|---|---|---|---|---|
| 1 | `1.MiniMax_H3_Easy.json` | 基础示例：文生视频 / 图生或首尾帧 / 参考生视频的最短链路 | 加载器 → 主节点 → 输出 → 外挂 LoRA → 原生采样 → 视频/音频解码 → 合成 | FL2VA int8、Qwen3VL 文本编码、video/audio VAE、Turbo 8step LoRA | 无 |
| 2 | `2.MiniMax_H3_Easy_Pass2.json` | **二采放大（像素级）**：一采出片 → 解码成帧 → 放大 → 重新编码成 latent 再采一遍；节点最多、最吃显存 | 主节点 → 输出 → 分辨率/宽高比 → 图像缩放 → VAE 编码 → 二采条件 → 第二套采样 → 合成 | 一采 FL2VA int8 + 二采 W4A8、taeh3 预览 VAE、Turbo LoRA | KJNodes、Easy-Use、Memory Cleanup |
| 3 | `3.MiniMax_H3_Easy_Selected_Video_Refine.json` | **已选视频分段二采**：挑一条已经生成好的视频，按时间/帧切开逐段二采 | 已选视频上下文 → 分段采样 → 分段二采 → 分段解码 | Ref2VA pruned int8、Ref2V Turbo 4step LoRA、3D latent 放大器 | 无 |
| 4 | `4.MiniMax_H3_Easy_Context_Segments.json` | 上下文分段基础版：提示词用单独一行 `---` 切段，一次采样出一段连续长视频 | 素材库 + 上下文分段 → 分段采样 → 分段解码 | FL2VA int8、FL2V Turbo 4step LoRA | 无 |
| 5 | `5.MiniMax_H3_Easy_Context_Segments_Latent_Refine.json` | 上下文分段 + **latent 二采**：复用一采模型，只多加载 3D latent 放大器，最省显存的二采 | 上下文分段 → 一采分段 → 分段二采（`latent_upscale`）→ 分段解码 | Ref2VA int8、3D latent 放大器、Ref2V Turbo LoRA | 无 |
| 6 | `6.MiniMax_H3_Easy_Context_Segments_Pixel_Refine.json` | 上下文分段 + **像素二采**：二采可走独立模型和目标分辨率，画质上限最高 | 上下文分段 → 一采分段 → 分段二采（`pixel_resize`）→ 分段解码 | FL2VA pruned int8、Ref2V Turbo LoRA、3D latent 放大器 | 无 |
| 7 | `7.MiniMax_H3_Easy_Context_Segments_Control.json` | 上下文分段 + **逐段控制**：公共输入只接一次，3 个分段步骤串起来，可只重跑第 N 段 | 上下文分段 → 采样设置 → 分段步骤 ×3 → 分段汇总 → 分段解码 | FL2VA int8、FL2V Turbo 4step LoRA | 无 |
| 8 | `8.AICG3D_Smoke_Test.json` | 插件自检：验证加载器 4 个 LoRA 槽、主节点、素材库、技能库 | 加载器（4 槽）→ 主节点 → 输出 → 原生采样 → AV Decode T8 → VHS 合成 | 合并版 hybrid int8、Qwen3VL、video/audio VAE、Turbo 4step + 写实 LoRA | VHS、pysssss、T8 解码插件 |
| 9 | `9.AICG3D_合并采样器_测试.json` | 验证 **AICG-采样器（高级）**：原生五个采样节点合并成一个 | 加载器 → 主节点 → AICG-采样器（高级）→ 解码 → 合成 | 同 8 | VHS、pysssss |
| 10 | `10.AICG3D_渲染器_测试.json` | 验证 **AICG-渲染器（高级）**：主节点一条线到底直接出片（只有 7 个节点） | 加载器 → 主节点 → 渲染器（内部完成采样+解码+合成）→ 保存视频 | 同 8 | pysssss（ShowText 旁支） |
| 11 | `11.AICG3D_测试样板.json` | 上手样板：提示词模板 + 技能库 + 渲染器整套串起来 | 提示词模板 → 主节点 → 渲染器 → 保存视频；旁支技能库 | 同 8 | pysssss |
| 13 | `13.AICG3D_渲染器_二采_单节点.json` | **二采单节点**：一采 + Latent 3D 放大 + 二采收成一个节点，只剩两条连线 | 加载器 → 主节点 → 渲染器（二采，内部完成一采+放大+二采+解码+合成，可开「二采分块采样」防爆显存）→ 保存视频 | 同 8，另加 3D latent 放大器 | 无 |
| 14 | `14.AICG3D_渲染器_一采二采_拆分.json` | **一采 / 二采放大拆成两个节点**：可以只用一采，也可以自由串上二采放大 | 加载器 → 主节点 → 渲染器（一采）→ 保存视频；一采的「一采数据」→ 渲染器（二采放大）→ 保存视频 | 同 8，另加 3D latent 放大器 | 无 |
| 15 | `15.AICG3D_无限段落顺序生成.json` | **无限段落顺序生成 + 自动拼接**：全局设置与素材库只接第 1 段、后面段落自动继承，段落可自由增减，段间自动衔接上段尾帧 | 加载器 → 全局设置 → 视频段落 ×3（可无限加）→ 最终合成视频 → 保存视频 | 同 8 | 无 |

**怎么挑**：

- 先跑通、快点看到画面：`11`（上手样板）→ `10`（一条龙渲染）。
- 做长视频 / 多镜头连续：`4`（基础分段）→ `7`（要逐段重跑）→ `5`（省显存二采）→ `6`（画质优先二采）。
- 已经有满意的成片、只想挑几段放大：`3`。
- 单条短片整体二采放大：`2`（像素级，二采可换模型）/ `13`（latent 级，一个节点搞定，最省事；
  显存吃紧就把节点里的「二采分块采样」改成「开」，二采会按空间分块跑）。
- 想让一采 / 二采放大分开用（只跑一采，或临时加上放大）：`14`，两个节点各自独立，接不接二采自己挑。
- 想让一条长片按段落顺序拍下去、段落数量随时增减：`15`，全局设置只管分辨率 / 宽高比 / 帧率 / 衔接帧数 / 显存，
  段落节点一段一个，段尾自动接下一段开头，最后 `最终合成视频` 一次拼成完整 mp4。
- `8` / `9` 是插件自检用的，平时不用跑。

> 二采（`3` / `5` / `6` / `2` / `13` / `14`）需要额外的二采模型：`latent_upscale` 模式要 3D latent 放大器，
> `pixel_resize` 模式要第二套 H3 模型或目标分辨率；模型文件按工作流里的加载器选择为准。

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

### 无限段落顺序生成（15.AICG3D_无限段落顺序生成.json）

把「顺序生成长视频」拆成一套最简的独立节点，一条线连到底：

`MiniMax H3 Aicg 加载器` → **`无限段落顺序生成（全局设置）`** → **`视频段落`**（可无限增减）→ **`最终合成视频`** → `SaveVideo`

节点分工：

- `无限段落顺序生成（全局设置）`：`sequence_config` 只在**第 1 段**接一次，后面的段落顺着
  `previous_segment` 自动继承（想给某段换配置，单独把线接到那一段），管全局的分辨率、宽高比、
  帧率（H3 原生 24fps 锁定）、参考图尺寸、采样器 / 调度器 / 步数 / 降噪；分辨率只有预设档，宽高由
  「分辨率 + 宽高比」算出来，节点上只读显示（如 `1920x1080`），不用手填。其中这几项是重点：
  - **衔接帧数**（`1`~`20`）：每段开头接住上一段结尾多少帧画面。H3 原生时间栅格只有 `5 / 22 / 39 / 56 / 73`，
    所以填 `1~5` 按 5 帧跑、填 `6~20` 按 22 帧跑（越大越稳、越慢），默认 `5`。
  - **衔接方式**：`尾帧续写（latent）`＝直接拿上段尾部的 latent 当上下文，无损最快，走 Motion Context 同款机制；
    `尾帧画面（RGB）`＝把上段尾部画面重新编码成 Guide，画面更贴但多一次解码。
  - **显存收尾**（`vram_policy`）：每个段落跑完做一次。默认「释放缓存」＝把 PyTorch 占着的缓存显存还给驱动，
    模型留在显存里，下一段接着跑最快；显存实在吃紧再改「卸载模型」（每段重载权重，长片会慢）。
  - **音频模式**（`audio_mode`）：默认 `生成音频`＝每段自己出声音；
    `数字人（锁定音频）`＝素材库里那**一条**音频当驱动音轨，按整条时间轴切片锁进每一段
    （音频那一半不参与去噪，生成的画面跟着音频走），最终成片也用这条音轨。
    素材库里只放音频（提示词里只写 `@音频1`）时，参考生视频会报
    `needs an image or video in addition to audio`，切到这一档就能直接跑，没有画面参考的段落退回纯文字出片。
    整条链必须共用同一条音频，中途换成另一条会在合成时报错。
  - **提示词优化设置**：点这一行打开提示词优化面板（优化方式 / API 地址 / API Key / 模型名 / 本地模型）。
    段落提示词框里的 `✦` 用的就是这份设置；没配好时点 `✦` 会直接把这个面板打开。
- `视频段落`：一段一个节点，参数只有 `prompt` / `seconds` / `seed`；要参考图、参考视频就从
  `MiniMax H3 Aicg资源库` 拉一条线到**第 1 段**的 `media`（后面的段落自动沿用同一份素材，想换素材
  再单独接线），在素材库里点一张素材，引用就插进**光标所在那一段**提示词的光标处。
  把上一段的 `segment` 接到本节点的 `previous_segment`，
  它就会自动接住上段结尾往下拍；第一段不接 `previous_segment`。只放一段也是完整流程。
- `最终合成视频`：只接最后一段的 `segment`，它自己顺着链找回前面每一段，逐段解码、逐段写进同一个编码器
  （音画一起拼，内存只跟单段有关），保存到 `output` 目录，同时输出 `VIDEO` 方便再接别的节点。

怎么增减段落：

- 加一段：复制现成的 `视频段落` 节点，把上一段的 `segment` 接到新节点的 `previous_segment`，
  再把新节点的 `segment` 接到 `最终合成视频` 的 `final_segment`。
- 减一段：删掉中间某个段落节点，把它的前一段 `segment` 直接接到后一段的 `previous_segment` 即可。
- 只出一段：一个 `视频段落` 直接接 `最终合成视频`。

增删段落只动 `previous_segment` / `segment` 这条链，全局设置与素材线不用重新接：
20 段的工作流画布上也只有一条主线，不会织成蜘蛛网。

测试要点：

- 先保持默认 `480P / 16:9 / 每段 5 秒 / 20 步 / 衔接 5 帧`，跑通再往上加。
- 工作流预置三段中文提示词（起手 → 中段 → 收尾），照着改成自己的分镜即可。
- 采样预览默认关闭，想看正在采样那一段的实时画面，就在全局设置里把「采样预览」改成「开」，
  `preview_interval` 控制每隔多少步推一张。
- 每段结束都会打印显存 / 内存收尾日志（`[MiniMax H3 Aicg] ...`），可以用它判断显存够不够。

---

# MiniMax H3 Aicg Workflow Guide

## English

Before using any workflow in this folder, install the required custom nodes and download the models used by that workflow.

### Workflow overview

| # | File | What it does | Key chain | Main models / LoRAs | Extra nodes |
|---|---|---|---|---|---|
| 1 | `1.MiniMax_H3_Easy.json` | Baseline sample: shortest text-to-video / image / reference-to-video chain | Loader -> main node -> Output -> external LoRA -> native sampling -> video/audio decode -> mux | FL2VA int8, Qwen3VL text encoder, video/audio VAE, Turbo 8-step LoRA | none |
| 2 | `2.MiniMax_H3_Easy_Pass2.json` | **Pixel-level second pass**: first pass -> decode to frames -> resize -> encode back to latent -> second pass; heaviest graph | main node -> Output -> resolution/aspect -> image resize -> VAE encode -> second-pass conditioning -> second sampling -> mux | first-pass FL2VA int8 + second-pass W4A8, taeh3 preview VAE, Turbo LoRA | KJNodes, Easy-Use, Memory Cleanup |
| 3 | `3.MiniMax_H3_Easy_Selected_Video_Refine.json` | **Refine a selected video**: pick an already rendered clip, cut it into segments and refine segment by segment | selected-video context -> segment render -> segment refine -> segment decode | Ref2VA pruned int8, Ref2V Turbo 4-step LoRA, 3D latent upscaler | none |
| 4 | `4.MiniMax_H3_Easy_Context_Segments.json` | Context-segment baseline: split the prompt with a standalone `---` line and sample one continuous long clip | media loader + context segments -> segment render -> segment decode | FL2VA int8, FL2V Turbo 4-step LoRA | none |
| 5 | `5.MiniMax_H3_Easy_Context_Segments_Latent_Refine.json` | Context segments + **latent second pass**: reuse the first-pass model, only add the 3D latent upscaler (lowest VRAM) | context segments -> first pass -> segment refine (`latent_upscale`) -> segment decode | Ref2VA int8, 3D latent upscaler, Ref2V Turbo LoRA | none |
| 6 | `6.MiniMax_H3_Easy_Context_Segments_Pixel_Refine.json` | Context segments + **pixel second pass**: optional separate model and target resolution, best quality ceiling | context segments -> first pass -> segment refine (`pixel_resize`) -> segment decode | FL2VA pruned int8, Ref2V Turbo LoRA, 3D latent upscaler | none |
| 7 | `7.MiniMax_H3_Easy_Context_Segments_Control.json` | Context segments + **per-segment control**: shared inputs connected once, three segment steps chained, rerun segment N only | context segments -> sample setup -> segment step x3 -> segment collect -> segment decode | FL2VA int8, FL2V Turbo 4-step LoRA | none |
| 8 | `8.AICG3D_Smoke_Test.json` | Plugin self-test: 4 LoRA slots, main node, media library, skill library | loader (4 slots) -> main node -> Output -> native sampling -> AV Decode T8 -> VHS combine | merged hybrid int8, Qwen3VL, video/audio VAE, Turbo 4-step + realism LoRA | VHS, pysssss, T8 decode plugin |
| 9 | `9.AICG3D_合并采样器_测试.json` | Verifies **AICG Sampler (Advanced)**: five native sampling nodes collapsed into one | loader -> main node -> AICG sampler -> decode -> mux | same as 8 | VHS, pysssss |
| 10 | `10.AICG3D_渲染器_测试.json` | Verifies **AICG Render (Advanced)**: one wire from the main node to the file (7 nodes) | loader -> main node -> render node (sampling + decode + mux inside) -> SaveVideo | same as 8 | pysssss (ShowText side branch) |
| 11 | `11.AICG3D_测试样板.json` | Starter sample: prompt preset + skill library + render node together | prompt preset -> main node -> render node -> SaveVideo; skill side branch | same as 8 | pysssss |
| 13 | `13.AICG3D_渲染器_二采_单节点.json` | **Single-node second pass** (legacy: its widget list no longer matches the node, re-add the node or use 14) | loader -> main node -> render (pass 2) -> SaveVideo | same as 8, plus 3D latent upscaler | none |
| 14 | `14.AICG3D_渲染器_一采二采_拆分.json` | **First pass / upscale-refine split into two nodes**: use pass 1 alone, or chain the optional second pass | loader -> main node -> render (pass 1) -> SaveVideo; pass 1 `pass1` -> render (pass 2) -> SaveVideo | same as 8, plus 3D latent upscaler | none |
| 15 | `15.AICG3D_无限段落顺序生成.json` | **Unlimited ordered segments + auto-stitch**: the global config and media lines connect to segment 1 only and later segments inherit them, the segment count is changed at will, and each segment starts from the previous one tail frames | loader -> global config -> video segment x3 (add as many as you like) -> final combine -> SaveVideo | same as 8 | none |

**Which one to pick**

- Get something on screen fast: `11` (starter) then `10` (one-wire render).
- Long, multi-shot continuous video: `4` first, then `7` for per-segment reruns, `5` for a low-VRAM second pass, `6` when quality matters most.
- You already have a clip you like and only want to upscale parts of it: `3`.
- Whole-clip second pass for a short video: `2`.
- Want the first pass and the upscale refine to run as separate, optional nodes: `14`.
- Want a long video built segment by segment with the segment count changed at will: `15`.
- `8` / `9` are plugin self-tests; you normally do not run them.

> The second-pass workflows (`2` / `3` / `5` / `6` / `14`) need extra models: `latent_upscale` mode
> requires a 3D latent upscaler, `pixel_resize` mode uses a second H3 model or a target
> resolution. Select the files matching the loaders inside each workflow.

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

### Unlimited ordered segments (15.AICG3D_无限段落顺序生成.json)

Splits ordered long-video generation into a minimal set of standalone nodes, one wire end to end:

`MiniMax H3 Aicg Loader` -> **`Sequence Global`** -> **`Video Segment`** (add as many as you want) -> **`Final Combine`** -> `SaveVideo`

How the nodes split the work:

- `Sequence Global` connects its `sequence_config` wire to the **first** segment only; later segments
  inherit it through `previous_segment` (wire a segment's own `sequence_config` when it needs different
  settings). It owns the global resolution, aspect ratio, frame rate (locked to the native 24 fps),
  reference image size, sampler / scheduler / steps / denoise, plus a few settings that matter here:
  - **Handoff frames** (`1`-`20`): how many tail frames of the previous segment each segment starts from.
    H3 only has the native temporal grid `5 / 22 / 39 / 56 / 73`, so `1`-`5` runs as 5 frames and
    `6`-`20` runs as 22 frames (higher is steadier but slower). Default is `5`.
  - **Handoff mode**: `latent` reuses the previous tail latent as context (lossless and fastest, the same
    path as Motion Context); `RGB` re-encodes the previous tail frames as a Guide (a closer match, one
    extra decode).
  - **VRAM cleanup** runs after every segment. The default "release cache" hands cached VRAM back to the
    driver while keeping the model resident so the next segment starts fastest; "unload models" uses the
    least VRAM but reloads the weights for every segment.
  - **Audio mode** (`audio_mode`): the default `生成音频` lets every segment generate its own sound;
    `数字人（锁定音频）` treats the single audio clip in the media library as a driver track, slices it
    along the whole timeline and locks it into every segment (that half of the AV latent is not denoised,
    so the generated picture follows the track), and the final combine uses that same track.
    With an audio-only library (and `@音频1` in the prompt) reference-to-video raises
    `needs an image or video in addition to audio`; switching to this mode runs it, falling back to
    text-only generation for segments without a visual reference. The whole chain must share one track -
    swapping in a different audio mid-chain raises a clear error at combine time.
- **Prompt optimizer settings**: click this row to open the optimizer panel (engine, API URL, API key,
  model, local model). The `✦` button in a segment's prompt box uses exactly these settings, and clicking
  `✦` while the optimizer is unconfigured opens the panel for you.
- `Video Segment`: one node per segment, with only `prompt` / `seconds` / `seed`. Pull a wire from the
  media library into the **first** segment's `media` when you need reference images or video; later
  segments inherit the same library (wire their own `media` to swap it). Clicking media in the library
  inserts the reference at the caret of the segment you last placed the caret in. Connect the previous
  segment `segment` into `previous_segment` and it continues from that tail; leave `previous_segment`
  empty for the first segment. A single segment is a complete run on its own.
- `Final Combine`: takes only the last segment `segment`, walks the chain back to the first segment,
  decodes and encodes one segment at a time into a single encoder (video and audio together, so memory
  only depends on one segment), saves into the `output` folder, and also returns `VIDEO` for other nodes.

Adding and removing segments:

- Add one: copy an existing `Video Segment` node, wire the previous segment `segment` into the new node
  `previous_segment`, then wire the new node `segment` into `Final Combine` `final_segment`.
- Remove one: delete a middle segment node and wire the one before it straight into the one after it.
- Single segment: connect one `Video Segment` straight into `Final Combine`.

Adding or removing segments only touches the `previous_segment` / `segment` chain; the global config and
media wires stay where they are, so a 20-segment graph keeps a single main line instead of a spider web.

What to check:

- Keep the defaults (`480P / 16:9 / 5s per segment / 20 steps / 5 handoff frames`) for the first run.
- The workflow ships three Chinese prompts (opening / middle / closing) that you can replace with your own shots.
- Sampling preview is off by default; turn `sample preview` on in the global node to watch the segment being
  sampled live, and use `preview interval` to control how often a frame is pushed.
- Every segment prints a VRAM / RAM cleanup log line (`[MiniMax H3 Aicg] ...`) you can use to judge headroom.
