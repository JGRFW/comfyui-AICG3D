kpop-girl-group-mv · Skill 完整文档
版本： 2.0（含分镜14字段结构 + 负面提示词优化） 输入： 成员数量 + 参考图片节点 + MV风格描述 输出： 30秒 · 16:9 · 1080p 电影级KPOP女团高能MV成片

一、角色提示词规范
1.1 三层锁定框架
每位成员的身份信息拆为三层，Layer 1 + 2 全程不可变，Layer 3 按分镜变化。

层级	内容	是否可变
Layer 1 · 面部生物特征	眼型、眼距、鼻梁高度、鼻翼宽度、唇厚、唇峰、脸型、下颌角、肤色（记录为色值）	❌ 绝对不变
Layer 2 · 造型身份	发型（长度/纹理/分缝）、发色（主色+挑染）、上衣、下装、袜子/丝袜、鞋子、全部配饰	❌ 全程锁定
Layer 3 · 表演动态	身体姿势、面部表情、机位角度、场景灯光	✅ 按分镜变化
1.2 成员档案模板
成员X档案：
- 角色名：___
- 面部特征：[肤色/脸型/眉形/眼型/鼻型/唇形/标志性特征]
- 发型：[长度/纹理/刘海/颜色/发饰]
- 服装：
    上衣：[款式/袖长/领口/面料/颜色/图案]
    下装：[款式/长度/面料/颜色/图案]
    袜子：[类型/透明度/颜色]
    鞋子：[类型/跟高/颜色]
    配饰：[逐件列出]
- 妆容：[眼妆/唇色/腮红/整体风格]
- 气质关键词：[3–5个词]
- 色调锁定：[主色/辅色/点缀色]
- 角色定位：[主唱/Rapper/舞担/门面/领队]
二、场景提示词规范
场景定义模板（建议定义2–3个）
场景A · 主舞台（全程主场景）

地面类型：镜面地板（高反光，完整倒映人物与灯光）
主光色：蓝紫冷色调顶光矩阵，从上方分束打下
背景：暗背景，灯架轮廓隐现，LED灯阵矩阵闪烁
地面效果：流光倒影，人物与倒影上下呼应
整体感：赛博感 · 高对比 · 专业演出级
关键词：mirror floor stage · blue-purple cold overhead lighting matrix ·
        high-contrast dark background · reflective floor with light streaks
场景B · 彩色渐变光束区（个人/组合镜头）

背景：蓝/紫/绿三色光束交替横扫，形成动态渐变光幕
特效：全息/亮片服装产生衍射折射效果
色调：高饱和度，充满能量感
关键词：colorful gradient light beams · blue purple green alternating sweep ·
        dynamic light curtain · iridescent reflection on costumes
场景C · 暖白逆光结尾区（结尾专用）

光源：强烈暖白逆光，打亮全员轮廓，形成发光边缘光晕
背景：朦胧虚化，前景人物清晰
氛围：神圣感 · 仪式感 · 温暖收尾
关键词：warm white strong backlight · glowing halo rim light ·
        soft bokeh background · ethereal stage ending atmosphere
三、分段动作提示词
段落	时间	能量值	核心动作关键词
开场段	0–5s	40→60%	从黑暗走入灯光 · 双臂展开 · 低头猛然抬起 · 卡点定格 · 直视镜头
个人展示A	5–10s	70%	手臂切割空气 · 发丝甩动 · 向前一步 · 双手叉腰 · 凌厉眼神
三人组合段	10–15s	75%	中心旋转 · 全息反光 · 两侧对称手势 · 三角站位 · 卡点定格
齐舞高潮段	15–20s	90%	同步下蹲 · 弹起 · 急转身 · 定格freeze · 裙摆飞扬 · 发丝飘动
个人爆发段	20–25s	100%	身体前倾 · 双臂向前推出 · 表情凌厉 · 快速拉远 · 全员最强pose
结尾收束段	25–30s	50%	缓缓转身 · 低头后抬起 · 自信微笑 · ending pose · 画面定格
四、分镜提示词（14字段完整结构）
每个分镜按以下14个字段填写，生成视频时将「画面描述+动作+运镜+情绪」拼合为正向prompt，配合成员锚点图（reference_nodes）和负面提示词同步输入。

🎞 镜号 01 · 开场定格（0–5s）
字段	内容
镜号	01
时长	0–5s（5秒）
构图	五人对称横排居中，镜面地板完整反射，框式构图
画面描述	五位成员从舞台黑暗区走入蓝紫顶光区，排成一字横排，双臂同步向两侧展开，低头后猛然抬起直视镜头形成卡点定格，地面倒影与本体上下呼应
景别	全景 → 中景（推进过渡）
机位	正面低角度（仰拍约15°）
运镜	平滑向前推进（dolly push in），速度匀速，贴合鼓点落拍
情绪	压迫感 · 宣告感 · 强势登场
动作	双臂向两侧水平展开 → 低头 → 猛然抬头定格
微表情	抬头瞬间眼神锁定镜头，嘴角微抿，眉头轻压
情绪变化	黑暗中的蓄势 → 灯光亮起的爆发 → 定格时的压迫
节奏	跟随强拍鼓点，抬头动作精准卡在第一个downbeat
剪辑点	定格动作完成后的静止帧，硬切入下一镜
声音	强节奏开场鼓点 + 低频bass铺底，无人声
🎞 镜号 02 · 个人特写A（5–10s）
字段	内容
镜号	02
时长	5–10s（5秒）
构图	单人居中，背景虚化蓝紫光斑，浅景深
画面描述	成员A做手臂切割空气的卡点动作，发丝随势甩动；横移切换至成员B，她向前一步双手叉腰，眼神凌厉锁定镜头
景别	近景（腰部以上）
机位	正面平拍，轻微随舞蹈晃动
运镜	横向跟移（tracking横移），两人之间自然过渡焦点
情绪	干练爆发（成员A） · 暗黑压迫（成员B）
动作	成员A：手臂斜向切割 + 发丝甩动；成员B：迈步向前 + 叉腰定格
微表情	成员A：嘴角微扬，眉眼凌利；成员B：眼神下压，嘴唇微抿成线
情绪变化	利落帅气 → 神秘强势，两种气场对比切换
节奏	每个卡点动作对应一个鼓击，横移切换在弱拍完成
剪辑点	成员B叉腰定格的静止帧处硬切
声音	持续舞曲，伴随手臂动作的切割音效
🎞 镜号 03 · 三角构图旋转（10–15s）
字段	内容
镜号	03
时长	10–15s（5秒）
构图	三角形站位：中心成员前置，左右两侧成员后退半步
画面描述	中心成员在舞台中央旋转，服装随旋转折射出光芒；左右两侧成员同步做出对称卡点手势，三人形成稳定三角视觉结构
景别	中景（膝盖以上）
机位	正面平拍，轻微低角度
运镜	固定机位 + 轻微弧形环绕（约10°），配合中心成员旋转方向
情绪	灵动闪耀（中心） · 冷艳衬托（两侧） · 整体：视觉张力
动作	中心：原地旋转一圈后定格；两侧：同步伸出对称手势
微表情	中心旋转后定格时嘴角上扬，眼神飞扬；两侧表情冷静，眼神向中心聚焦
情绪变化	旋转中的动态张力 → 定格后的三人聚焦感
节奏	旋转跟随律动，定格卡在副歌第一拍
剪辑点	三人同时定格的瞬间，静止帧处切出
声音	副歌旋律铺入，旋转动作配合音符上行
🎞 镜号 04 · 五人齐舞全景（15–20s）
字段	内容
镜号	04
时长	15–20s（5秒）
构图	全员横排居中对称，镜面地板完整反射，框式构图（灯架上下边框）
画面描述	全员执行高难度齐舞：同步下蹲 → 弹起 → 急转身 → 定格freeze，裙摆与发丝随每个爆发动作飞扬，镜面地板倒影形成双层视觉冲击
景别	中全景（含全身至头顶）
机位	正面固定机位，略低角度
运镜	固定机位，轻微随节拍前后微晃（handheld feel，幅度极小）
情绪	整齐爆发 · 团队力量 · 视觉震撼
动作	下蹲（拍1）→ 弹起（拍2）→ 转身180°（拍3）→ 定格freeze（拍4）
微表情	转身后定格时全员眼神同步锁定镜头，表情坚定，嘴唇微张
情绪变化	蓄力下蹲 → 爆发弹起 → 急促转身 → 强势定格，四拍完成情绪递进
节奏	每个动作精准对应一个强拍，四拍一循环
剪辑点	定格freeze的最高张力帧，保持0.5秒后切出
声音	高潮舞曲全力推进，强鼓点每拍清晰，无人声台词
🎞 镜号 05 · 个人爆发→全员定格（20–25s）
字段	内容
镜号	05
时长	20–25s（5秒）
构图	先单人居中特写，后快速拉远为全员全景
画面描述	主推成员身体前倾，双臂向镜头方向猛力推出，表情凌厉逼近镜头；镜头迅速拉远，全员同时亮出各自最强个人pose，五种气场同框爆发
景别	近景（胸部以上）→ 中全景
机位	正面，先平拍后拉远
运镜	快速zoom out（或dolly pull back），速度快，配合音效冲击感
情绪	个人爆发的侵略感 → 全员集体的压倒性气场
动作	主推成员：上身前倾 + 双臂向前猛推；全员：各自最强个人定格pose
微表情	主推成员：眼神逼视，眉头微皱，嘴唇微开；全员定格时各自表情达到最强烈状态
情绪变化	单人爆发侵略感 → 拉远后全员集体压迫感，层层递进
节奏	zoom out卡在副歌最强拍，全员定格与鼓点同步
剪辑点	全员定格最强帧，短暂停留后切出
声音	副歌高潮，音量最大，伴随拉远动作有低频冲击音效
🎞 镜号 06 · 结尾收束（25–30s）
字段	内容
镜号	06
时长	25–30s（5秒）
构图	全员横排，中心成员占最大视觉比重，两侧成员轻微虚化
画面描述	全员在暖白强逆光下从背对镜头缓缓转身，中心成员低头后抬起直视镜头露出自信微笑；两侧成员同步摆出各自ending pose，画面在微笑特写中定格
景别	中全景 → 面部特写
机位	正面平拍
运镜	平滑向前推进（dolly push in），速度缓慢，节奏收束
情绪	温暖收尾 · 自信从容 · 仪式感定格
动作	背对→转身（缓慢，3秒）→ 低头→抬头（中心成员，1秒）→ 微笑定格（最后1秒）
微表情	中心成员：嘴角上扬，眼神柔和有神，眼睛微眯；两侧保持各自角色气质的收束表情
情绪变化	转身时的期待感 → 抬头时的从容感 → 微笑定格时的温暖满足感
节奏	音乐节奏放缓，推进速度与音乐减速同步，定格在最后一个音符
剪辑点	微笑定格帧，淡出（fade to black）或直接硬切黑场
声音	舞曲节奏渐弱收尾，最后0.5秒静音或留尾音余韵
五、结尾提示词
Slow dolly push-in toward all members standing in a row under warm white strong backlight.
Center member slowly turns to face camera, gently drops head then lifts it with a confident
warm smile directly into the lens. Flanking members simultaneously strike individual ending
poses. Camera settles on a close-up. Warm halo rim light glowing behind all members.
Pace slows to a gentle hold. Freeze on the smiling close-up.
Subtle film grain overlay. Cinematic fade.
六、负面提示词
人物一致性（最高优先级）
face swap, identity drift, wrong face, facial feature change between shots,
eye size inconsistency, skin tone shift, nose shape change,
costume color error, outfit replacement, wrong hairstyle, hair color change,
missing member, extra member, wrong member count, duplicate character,
clothing swap between members, accessory missing
画面质量
blurry face, motion blur on face, overexposed face, underlit face,
low resolution, pixelated, jpeg artifacts, watermark, text overlay,
bad anatomy, distorted limbs, extra fingers, missing fingers,
deformed body, unnatural pose, stiff movement, robotic motion
风格污染
cartoon style, anime style, illustration, painting, 3D render,
plastic skin, over-smoothed skin, wrong era costume, casual wear,
street clothes, wrong background, outdoor scene, daytime natural light
技术问题
flickering, frame drop, inconsistent lighting between cuts,
color grading inconsistency, aspect ratio wrong, vertical video,
black bars, letterbox, pillarbox, audio desync
七、重生成决策矩阵
问题类型	严重程度	处理方式
换脸 / 面部特征改变	🔴 致命	立即重生成，加强面部锁定描述
服装颜色偏移	🟠 高	重生成，prompt中加入hex色值
配饰缺失	🟡 中	重生成，逐件列出配饰
轻微灯光色温偏差	🟢 低	可接受（亮度差<10%）
动作轻微偏差	🟢 低	可接受（动作意图保留即可）
八、输出规格
项目	规格
比例	16:9
分辨率	1080p（最低）
总时长	30秒（±0.2秒/镜）
分镜数	6段 × 5秒
帧率	30fps
剪辑	硬切（结尾可淡出）
质感	全程轻微胶片颗粒叠加（10–20%透明度）
