# 云上仙宫·视频提示词

> 分类：古风仙侠东方 ｜ 来源：云上仙宫\“云上仙宫”视频提示词.txt

“云上仙宫”电影级动态影像工程手册

本工程旨在将 AI 生成的静态图像转化为具备 IMAX 70mm 胶片质感的史诗级视频，通过“摄影语言+动态行为”的叠加逻辑，彻底消除“AI 塑料感”。

1. 核心生成公式 (The Core Formula)

为了确保逻辑的一致性，所有生成的视频提示词必须遵循以下结构：

[核心影像基准] + [动态行为描述] + [镜头跟随指令] + [好莱坞氛围渲染] + [真实感防伪修饰]

2. 动态调度逻辑 (Dynamic Logic)

  - 默认模式 (Default)：若用户未指定动作，系统自动采用“电影级缓慢推轨推进 (Dolly Push-in)”，捕捉宏大空间感。
  - 交互模式 (Interactive)：若用户指定了动作（如：起飞、转身、施法），系统将动作逻辑强制绑定至摄像机跟随指令（Camera
    Tracking）。

3. 标准化提示词模板 (Master Prompt Template)

[CORE_VISUAL]: Cinematic 70mm IMAX film stock, Hollywood blockbuster aesthetic, anamorphic lens, shallow depth of field, cool-toned cinematic lighting, high dynamic range.

[ACTION_DYNAMIC]: {INSERT_ACTION_HERE}

[CAMERA_LOGIC]: {INSERT_CAMERA_INSTRUCTION_HERE}

[ATMOSPHERE]: Intricate volumetric fog, atmospheric depth, realistic light reflection, raw organic film grain, professional color grading.

[QUALITY_CONTROL]: Photorealistic, hyper-detailed environment, natural human motion,looks like captured real-life footage from a big-budget sci-fi epic, zero AI-generated artifacts.

4. 动作指令对照表 (Action & Camera Matrix)

当用户输入动作时，请参考以下映射表填充模板：

| 用户输入意图      | \[ACTION\_DYNAMIC\] 填充项                                                | \[CAMERA\_LOGIC\] 填充项                                                                   |
| :---------- | :--------------------------------------------------------------------- | :-------------------------------------------------------------------------------------- |
| **无动作要求**   | (Default: Static scenery)                                              | Slow, steady, immersive dolly push-in, subtle organic handheld shake.                   |
| **原地起飞/上升** | Character initiates a natural, gravity-defying ascent into the clouds. | Dynamic tracking shot following upward trajectory, camera tilts up to maintain framing. |
| **人物转身**    | Character turns around gracefully with fluid movement.                 | Slow cinematic orbit around the subject, depth of field shifts dynamically.             |
| **疾行/御剑**   | Character moves forward rapidly with swift, controlled motion.         | Tight tracking shot, subtle motion blur, matching subject's speed.                      |
| **环视/俯瞰**   | Character gazes at the vast celestial scenery.                         | Smooth pan-up or crane shot, revealing the majestic scale of the architecture.          |

5. 视频生成实战示例

示例 A：用户要求“原地起飞”

Prompt: Cinematic 70mm IMAX film stock, Hollywood blockbuster aesthetic,
anamorphic lens, shallow depth of field, cool-toned cinematic lighting, high
dynamic range. The character initiates a natural, gravity-defying ascent,
gracefully lifting off from the ground and soaring upward into the clouds.
Dynamic camera movement, smooth tracking shot following the character's upward
trajectory, subtle organic handheld shake to match the soaring speed, camera
tilt-up to maintain subject framing. Intricate volumetric fog, atmospheric
depth, realistic light reflection, raw organic film grain, professional color
grading. Photorealistic, hyper-detailed environment, natural human motion, looks
like captured real-life footage from a big-budget sci-fi epic, zero AI-generated
artifacts.

示例 B：用户未提要求

Prompt: Cinematic 70mm IMAX film stock, Hollywood blockbuster aesthetic,
anamorphic lens, shallow depth of field, cool-toned cinematic lighting, high
dynamic range. Slow, steady, and immersive dolly push-in tracking shot,
capturing the grand scale of the palace. Constant speed forward movement, subtle
organic handheld camera shake to simulate a real-world filming environment.
Intricate volumetric fog, atmospheric depth, realistic light reflection on
architecture, raw organic film grain, professional color grading.
Photorealistic, hyper-detailed environment, natural human motion, looks like
captured real-life footage from a big-budget sci-fi epic, zero AI-generated
artifacts.
