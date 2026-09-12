# LTX-2.3 视频生成模型 LoRA 适配器

> 分类：提示词工程 ｜ 来源：提示词人物风格\LTX-2.3 视频生成模型的 LoRA 适配器.docx

这些文件主要是LTX-2.3 视频生成模型的 LoRA 适配器，它们并非用于静态图像生成（如 Stable Diffusion），而是专门用于增强或修改 LTX-2.3 基础模型在视频生成任务中的表现。以下是每个文件的用途、搭配模型、推荐参数及触发标签的详细说明：
1. gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors
用途：为 Gemma-3-12B 语言模型提供低秩适配，可能用于文本理解或对话生成任务的微调。
搭配模型：Gemma-3-12B-IT（文本模型）。
参数设置：Rank=64，BF16 精度，适用于消费级显卡。
激发标签：无特定视觉触发词，需在文本提示中明确调用“Gemma-3”或“abliterated”相关语境。
2. Kook_Qwen_真实幻想V2.safetensors
用途：结合 Qwen 与 Kook 模型，用于生成“真实幻想”风格的视频内容，可能偏向写实与奇幻融合。
搭配模型：LTX-2.3-22b 或 Qwen-VL 多模态模型。
参数设置：建议强度 0.8–1.2，配合“realistic fantasy”、“cinematic lighting”等提示词。
激发标签：realistic fantasy, Kook style, Qwen enhanced
3. LTX2.3_reasoning_I2V_V3.safetensors
用途：增强 LTX-2.3 在“图像到视频”生成中的推理能力，使运动更连贯、逻辑更合理。
搭配模型：LTX-2.3-22b（I2V 模式）。
参数设置：强度 1.0，推荐使用“smooth motion”, “logical transition”等提示。
激发标签：reasoning I2V, motion coherence, V3 logic
4. LTX-2.3-22b-AV-LoRA-talking-head-v1.safetensors
用途：专为“数字人说话”场景设计，优化口型同步与面部表情。
搭配模型：LTX-2.3-22b（文生视频或图生视频）。
参数设置：强度 1.0–1.5，配合“talking head”, “lip sync”, “facial expression”等提示。
激发标签：talking head v1, AV sync, digital human
5. ltx-2.3-22b-distilled-1.1_lora-dynamic_fro09_avg_rank_111_bf16.safetensors
用途：蒸馏版 LoRA，用于加速推理并保持高质量，适合快速预览或低显存环境。
搭配模型：LTX-2.3-22b-dev。
参数设置：强度 0.7–1.0，可搭配“fast generation”, “distilled quality”等提示。
激发标签：distilled 1.1, dynamic fro09, rank 111
6. ltx-2.3-22b-distilled-lora-384-1.1.safetensors
用途：针对 384px 分辨率优化的蒸馏 LoRA，适合小尺寸视频快速生成。
搭配模型：LTX-2.3-22b-dev。
参数设置：强度 1.0，推荐“384p”, “low-res preview”等提示。
激发标签：distilled 384, 1.1 version, small resolution
7. ltx-2.3-22b-ic-lora-hdr-0.9.safetensors
用途：启用 HDR（高动态范围）视频生成，提升画面亮度与色彩层次。
搭配模型：LTX-2.3-22b。
参数设置：强度 0.9，配合“HDR”, “high dynamic range”, “vivid colors”等提示。
激发标签：HDR 0.9, IC-LoRA, enhanced contrast
8. ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors
用途：可能用于控制视频中“元素”或“成分”的生成，如特定物体、材质或特效。
搭配模型：LTX-2.3-22b。
参数设置：强度 0.9，需在提示中明确指定“ingredients”如“metallic texture”, “glass reflection”。
激发标签：ingredients 0.9, material control, IC-LoRA
9. LTX2.3-IC-LORA-Dual-Character.safetensors
用途：支持双角色同框生成，优化角色间互动与空间关系。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“dual character”, “two people interacting”等提示。
激发标签：dual character, IC-LoRA, character interaction
10. ltx2.3-ic-subtitles-remove-general.safetensors
用途：自动移除视频中的字幕或文字水印。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，无需特殊提示词，加载即可生效。
激发标签：subtitle removal, watermark clean, general purpose
11. ltx2.3-ic-video-upscale-general.safetensors
用途：通用视频超分 LoRA，提升视频分辨率与细节清晰度。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0–1.5，配合“upscale”, “enhance detail”, “4K output”等提示。
激发标签：video upscale, general super-resolution, IC-LoRA
12. ltx2.3-ic-watermark-remove-general.safetensors
用途：移除视频中的水印或品牌标识。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，无需特殊提示词。
激发标签：watermark removal, clean video, general purpose
13. LTX-2.3-ID-LoRA-TalkVid-3K.safetensors
用途：专为“TalkVid”场景设计，可能用于生成 3K 分辨率的数字人讲话视频。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“TalkVid”, “3K resolution”, “speech video”等提示。
激发标签：TalkVid 3K, ID-LoRA, digital speaker
14. LTX-2.3-Licon-MSR-V1.safetensors
用途：Licon 系列 MSR（Multi-Scale Refinement）版本，用于多尺度细节优化。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“multi-scale”, “detail refinement”, “MSR V1”等提示。
激发标签：Licon MSR V1, multi-scale enhancement, detail boost
15. LTX-2.3-Licon-MSR-V1-ef88d72e5312.safetensors
用途：MSR-V1 的特定哈希版本，可能为实验性或优化版。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，与 V1 相同，但可尝试不同种子或提示词组合。
激发标签：Licon MSR V1 ef88d72e5312, experimental version
16. LTX2.3-Licon-VBVR-I2V-240K-R32.safetensors
用途：VBVR（Video-Based Visual Reasoning）I2V 版本，用于图像到视频的语义推理生成。
搭配模型：LTX-2.3-22b（I2V）。
参数设置：强度 1.0，配合“visual reasoning”, “semantic motion”, “240K steps”等提示。
激发标签：VBVR I2V, 240K R32, reasoning video
17. LTX2.3-Licon-VBVR-I2V-390K-R32.safetensors
用途：VBVR I2V 的高阶版本，训练步数更多，推理能力更强。
搭配模型：LTX-2.3-22b（I2V）。
参数设置：强度 1.0–1.2，配合“advanced reasoning”, “390K steps”, “complex motion”等提示。
激发标签：VBVR I2V 390K, R32 high fidelity, deep reasoning
18. LTX-2.3-OmniNFT-RL-LoRA_bf16.safetensors
用途：OmniNFT 强化学习 LoRA，可能用于生成 NFT 风格或艺术化视频。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“NFT style”, “artistic video”, “RL enhanced”等提示。
激发标签：OmniNFT RL, BF16 precision, art generation
19. ltx2.3-transition.safetensors
用途：专为视频过渡效果设计，如淡入淡出、镜头切换、变形等。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“transition”, “scene change”, “smooth cut”等提示。
激发标签：transition effect, video editing, cinematic cut
20. ltx-2-19b-lora-camera-control-static.safetensors
用途：相机控制 LoRA，用于固定视角或静态镜头的视频生成。
搭配模型：LTX-2-19b（注意：非 2.3 版本）。
参数设置：强度 1.0，配合“static camera”, “fixed angle”, “no movement”等提示。
激发标签：camera control static, LTX-2-19b, fixed shot
21. put_loras_here
说明：此文件非模型，仅为占位符或提示文件，提醒用户将 LoRA 放入此目录。
22. Singularity-LTX-2.3_OmniCine_V1.safetensors
用途：OmniCine 电影级 LoRA，用于生成具有电影感、叙事性强的视频。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0–1.5，配合“cinematic”, “film grain”, “storytelling”等提示。
激发标签：OmniCine V1, Singularity, movie style
23. skin texture Photorealistic style v4.5.safetensors
用途：专用于增强皮肤纹理的真实感，适合人物特写或肖像视频。
搭配模型：LTX-2.3-22b。
参数设置：强度 0.8–1.2，配合“skin texture”, “photorealistic”, “v4.5”等提示。
激发标签：skin texture v4.5, photorealistic style, human detail
24. zit_fdpo_v1.safetensors
用途：FDPO（Face Detail Preservation Optimization）LoRA，用于优化人脸细节保留。
搭配模型：LTX-2.3-22b。
参数设置：强度 1.0，配合“face detail”, “FDPO v1”, “preserve features”等提示。
激发标签：zit FDPO v1, face preservation, detail optimization
