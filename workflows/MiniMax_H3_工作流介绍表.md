# MiniMax H3 工作流介绍表

围绕 MiniMax H3 视频/音频生成模型（ComfyUI-MiniMaxH3-Easy 插件 + AICG3D 融合节点）搭建，从单段生成到多分段创作、二采精修、插件自测，覆盖完整创作链路。

## 工作流总览

| # | 文件名 | 类型 | 用途简介 | 核心链路 / 关键节点 | 节点数 |
|---|--------|------|----------|---------------------|--------|
| 1 | MiniMax_H3_Easy | 基础入门 | 最简单的单段文/图生视频：一张图片 + 提示词直接出带音频的视频 | Loader → MiniMaxH3Easy → Output → 采样器组 → VAEDecode → SaveVideo | 16 |
| 2 | MiniMax_H3_Easy_Pass2 | 二采精修 | 两遍生成：第一遍出片后 VAEEncode 回 latent，第二遍用独立模型重采样提高画质 | 两套完整采样链 + LTXVSeparateAV/ConcatAVLatent 音视频 latent 拆合 + SecondPassConditioning | 37 |
| 3 | MiniMax_H3_Easy_Selected_Video_Refine | 视频精修 | 输入已有视频，选定片段做二采精修 | LoadVideo → SelectedVideoContext → SegmentRender + SegmentRefine 双路输出（原片与精修片各存一份）；原 rgthree 分组开关节点已移除 | 22 |
| 4 | MiniMax_H3_Easy_Context_Segments | 多分段基础 | 多镜头连续创作：提示词用 `---` 分段（分段秒数如 `10,8,5`），一条链生成整条多段视频 | ContextSegments → SegmentRender → SegmentDecode → SaveVideo | 10 |
| 5 | ..._Context_Segments_Latent_Refine | 多分段 + Latent 二采 | 在 4 的基础上加 latent 域二采放大，复用一采 H3 模型 + 3D latent upscaler | ContextSegments → SegmentRender → SegmentRefine（latent_upscale）→ 双 Decode 双存 | 15 |
| 6 | ..._Context_Segments_Pixel_Refine | 多分段 + 像素二采 | 在 4 的基础上加像素域二采：UNETLoader 加载独立二采模型放大重采样 | 同 5 但走像素放大路线（ResolutionSelector / AspectRatio），二采模型独立 | 19 |
| 7 | ..._Context_Segments_Control | 多分段 + 逐段控制 | 逐段可控：SampleSetup 接公共输入，3 个 SegmentStep 串联，每段 Seed/提示词独立，支持局部重跑命中缓存 | SampleSetup → SegmentStep×3 → SegmentCollect → SegmentDecode | 14 |
| 8 | AICG3D_Smoke_Test | 插件自测 | 验证 AICG3D 融合插件本身：内置 4 槽 LoRA 加载器、素材库 `@` 引用、AVDecodeT8 解码 | Loader → MiniMaxH3Easy → Output → SamplerCustomAdvanced → AVDecodeT8 → VHS 出 mp4，旁支技能库 ShowText | 13 |
| 9 | AICG3D_合并采样器_测试 | 插件自测 | 验证合并版采样器节点：一个节点替代整套采样器组 | Loader → MiniMaxH3Easy → Output → SamplerAdvanced（单节点采样）→ AVDecodeT8 → VHS | 9 |
| 10 | AICG3D_渲染器_测试 | 一条龙测试 | 「主节点 + AICG-渲染器（高级）」最简出片链：渲染器内部完成采样+解码+合成，只输出一条 VIDEO | Loader → MiniMaxH3Easy（H3 Context 输出）→ RenderAdvanced → SaveVideo | 7 |
| 11 | AICG3D_测试样板 | 上手样板 | “照抄就能跑”的新手样板：加提示词模板节点和三篇说明 Note，换模板/改 task 立即生效 | Loader → MiniMaxH3Easy ← PromptPreset（提示词模板）→ RenderAdvanced → SaveVideo | 11 |

## 按需求选工作流

| 使用场景 | 推荐工作流 |
|----------|-----------|
| 第一次上手 / 快速出片 | 1（原生链路）或 11（AICG3D 融合样板，带提示词模板） |
| 单镜头精修画质 | 2（Pass2 二采）或 3（对已有视频的选定片段精修） |
| 多镜头短片（分镜脚本） | 4 基础版；显存够用选 5（latent 二采）；要独立二采模型选 6（像素二采）；需逐段调 Seed/提示词、局部重跑选 7 |
| 验证插件安装是否正常 | 8（冒烟测试）、9（合并采样器）、10（一条龙渲染器） |

## 前置依赖与建议

- **插件**：ComfyUI-MiniMaxH3-Easy、KJNodes、Memory_Cleanup、VideoHelperSuite、Easy-Use
- **主要模型**：LightX2V MiniMax H3 Turbo LoRA（8-step）、Kijai MiniMax H3 FL2VA 剪枝 W4A8（README 内有夸克网盘链接）
- **首次跑通参数建议**：480P / 16:9 / 3 秒 / 8 步（8、10）或 20 步（11 默认）
- 分段模式细节（引导网格、柔性/硬性 AV 前缀、数字人音频模式、Low VRAM Tile 二采等）见 `README_WORKFLOWS.md`
