# 提示词方法论 1

> 分类：提示词工程 ｜ 来源：70-优秀提示词案例和官方提示词模板\提示词方法论1.html

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频生成提示词方法论 · 科技指南</title>
    <style>
        :root {
            --bg-primary: #08080e;
            --bg-card: #0d0d18;
            --bg-card-hover: #12121f;
            --border-glow: rgba(0, 212, 255, 0.25);
            --border-glow-strong: rgba(0, 212, 255, 0.6);
            --cyan: #00d4ff;
            --cyan-dim: rgba(0, 212, 255, 0.12);
            --purple: #7c4dff;
            --purple-dim: rgba(124, 77, 255, 0.15);
            --green: #00ff9d;
            --green-dim: rgba(0, 255, 157, 0.1);
            --text-primary: #e8e8f0;
            --text-secondary: #b0b0c8;
            --text-muted: #707090;
            --font-sans: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', system-ui, -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
            --radius: 16px;
            --radius-sm: 8px;
            --transition: 0.35s cubic-bezier(0.22, 1, 0.36, 1);
            --card-pad: clamp(1.5rem, 3vw, 2.5rem);
            --section-gap: clamp(2rem, 4vw, 3.5rem);
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html {
            scroll-behavior: smooth;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.75;
            overflow-x: hidden;
            min-height: 100vh;
            position: relative;
        }

        /* ── 背景网格与光晕 ── */
        .bg-grid {
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
            background-size: 48px 48px;
            pointer-events: none;
            z-index: 0;
            mask-image: radial-gradient(ellipse at 50% 0%, rgba(0, 0, 0, 1) 40%, rgba(0, 0, 0, 0.3) 80%, transparent 100%);
            -webkit-mask-image: radial-gradient(ellipse at 50% 0%, rgba(0, 0, 0, 1) 40%, rgba(0, 0, 0, 0.3) 80%, transparent 100%);
        }
        .bg-glow {
            position: fixed;
            border-radius: 50%;
            pointer-events: none;
            z-index: 0;
            filter: blur(80px);
            opacity: 0.4;
            animation: pulseGlow 8s ease-in-out infinite;
        }
        .bg-glow-1 {
            width: 500px;
            height: 500px;
            background: rgba(0, 212, 255, 0.12);
            top: -100px;
            left: -100px;
            animation-delay: 0s;
        }
        .bg-glow-2 {
            width: 400px;
            height: 400px;
            background: rgba(124, 77, 255, 0.1);
            bottom: 5%;
            right: -80px;
            animation-delay: 4s;
        }
        @keyframes pulseGlow {
            0%,
            100% {
                transform: scale(1);
                opacity: 0.35;
            }
            50% {
                transform: scale(1.15);
                opacity: 0.55;
            }
        }

        /* ── 滚动进度条 ── */
        .scroll-progress {
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, var(--cyan), var(--purple), var(--green));
            z-index: 10000;
            transition: width 0.1s ease-out;
            box-shadow: 0 0 12px rgba(0, 212, 255, 0.6);
            border-radius: 0 2px 2px 0;
        }

        /* ── 主容器 ── */
        .container {
            position: relative;
            z-index: 1;
            max-width: 920px;
            margin: 0 auto;
            padding: 0 1.5rem;
            padding-bottom: 4rem;
        }

        /* ── 头部 ── */
        header {
            padding: clamp(3rem, 7vw, 5rem) 0 1.5rem;
            text-align: left;
            border-bottom: 1px solid rgba(0, 212, 255, 0.12);
            margin-bottom: var(--section-gap);
            position: relative;
        }
        .header-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--cyan);
            background: var(--cyan-dim);
            border: 1px solid rgba(0, 212, 255, 0.2);
            padding: 0.4rem 1rem;
            border-radius: 100px;
            margin-bottom: 1.25rem;
            animation: fadeInDown 0.8s ease-out both;
        }
        .header-tag::before {
            content: '';
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 8px var(--green);
            animation: blink 2s ease-in-out infinite;
        }
        @keyframes blink {
            0%,
            100% {
                opacity: 1;
            }
            50% {
                opacity: 0.3;
            }
        }
        h1 {
            font-size: clamp(2rem, 5.5vw, 3.2rem);
            font-weight: 700;
            line-height: 1.2;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 30%, var(--cyan) 65%, var(--purple) 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeInDown 0.8s ease-out 0.1s both;
        }
        .subtitle {
            font-size: clamp(1rem, 1.8vw, 1.15rem);
            color: var(--text-secondary);
            margin-top: 0.8rem;
            max-width: 600px;
            animation: fadeInDown 0.8s ease-out 0.2s both;
        }
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-18px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* ── 导航锚点 ── */
        .nav-links {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1.5rem;
            animation: fadeInDown 0.8s ease-out 0.3s both;
        }
        .nav-links a {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            letter-spacing: 0.04em;
            color: var(--text-muted);
            text-decoration: none;
            padding: 0.35rem 0.8rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 100px;
            transition: var(--transition);
            background: rgba(255, 255, 255, 0.02);
        }
        .nav-links a:hover {
            color: var(--cyan);
            border-color: var(--border-glow);
            background: var(--cyan-dim);
            box-shadow: 0 0 18px rgba(0, 212, 255, 0.15);
        }

        /* ── 卡片通用 ── */
        .card {
            background: var(--bg-card);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: var(--radius);
            padding: var(--card-pad);
            margin-bottom: var(--section-gap);
            position: relative;
            transition: var(--transition);
            overflow: hidden;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--card-accent, var(--cyan)), transparent);
            opacity: 0.7;
            transition: var(--transition);
        }
        .card:hover {
            border-color: var(--border-glow);
            background: var(--bg-card-hover);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 30px rgba(0, 212, 255, 0.06);
            transform: translateY(-2px);
        }
        .card:hover::before {
            opacity: 1;
        }

        /* 卡片编号 - 已放大 */
        .card-num {
            font-family: var(--font-mono);
            font-size: 1.3rem;
            /* 原为0.8rem，增大 */
            letter-spacing: 0.08em;
            color: var(--card-accent, var(--cyan));
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.75rem;
            font-weight: 700;
            /* 加粗 */
        }
        .card-num::after {
            content: '';
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, var(--card-accent, var(--cyan)), transparent);
            opacity: 0.3;
        }
        .card-tag {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            letter-spacing: 0.08em;
            color: var(--card-accent, var(--cyan));
            background: color-mix(in srgb, var(--card-accent, var(--cyan)) 12%, transparent);
            border: 1px solid color-mix(in srgb, var(--card-accent, var(--cyan)) 25%, transparent);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
        }
        .card-title {
            font-size: clamp(1.3rem, 2.5vw, 1.6rem);
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }
        .card-core {
            font-size: 1rem;
            font-weight: 600;
            color: var(--card-accent, var(--cyan));
            margin-bottom: 1rem;
            padding: 0.75rem 1.1rem;
            background: color-mix(in srgb, var(--card-accent, var(--cyan)) 8%, transparent);
            border-left: 3px solid var(--card-accent, var(--cyan));
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            line-height: 1.6;
        }
        .card-body {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.85;
        }
        .card-body strong {
            color: #ffffff;
            font-weight: 600;
        }
        .card-body .highlight {
            color: var(--cyan);
            font-weight: 500;
        }
        .card-body ul {
            list-style: none;
            padding-left: 0.25rem;
            margin-top: 0.75rem;
        }
        .card-body ul li {
            position: relative;
            padding-left: 1.4rem;
            margin-bottom: 0.45rem;
            color: var(--text-secondary);
        }
        .card-body ul li::before {
            content: '›';
            position: absolute;
            left: 0;
            color: var(--card-accent, var(--cyan));
            font-weight: 700;
            font-size: 1.1rem;
            line-height: 1.4;
        }

        /* 颜色变体 */
        .card-accent-cyan {
            --card-accent: var(--cyan);
        }
        .card-accent-purple {
            --card-accent: var(--purple);
        }
        .card-accent-green {
            --card-accent: var(--green);
        }
        .card-accent-amber {
            --card-accent: #ffb300;
        }
        .card-accent-pink {
            --card-accent: #ff6ec7;
        }
        .card-accent-orange {
            --card-accent: #ff8a00;
        }
        .card-accent-teal {
            --card-accent: #1de9b6;
        }

        /* ── 底部总结 ── */
        .summary-card {
            background: linear-gradient(145deg, rgba(0, 212, 255, 0.06), rgba(124, 77, 255, 0.06));
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: var(--radius);
            padding: var(--card-pad);
            margin-top: 1rem;
            position: relative;
            overflow: hidden;
        }
        .summary-card::before {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(ellipse at top left, rgba(0, 212, 255, 0.08), transparent 60%),
                radial-gradient(ellipse at bottom right, rgba(124, 77, 255, 0.08), transparent 60%);
            pointer-events: none;
        }
        .summary-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.75rem;
            position: relative;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .summary-title::before {
            content: '⚡';
            font-size: 1.1rem;
        }
        .summary-text {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.85;
            position: relative;
        }
        .summary-text strong {
            color: var(--cyan);
        }

        /* ── 页脚 ── */
        footer {
            text-align: center;
            padding: 2rem 0 1rem;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 2rem;
        }
        footer .dot {
            color: var(--cyan);
            margin: 0 0.4rem;
        }

        /* ── 滚动动画 ── */
        .animate-on-scroll {
            opacity: 0;
            transform: translateY(28px);
            transition: opacity 0.7s ease-out, transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .animate-on-scroll.visible {
            opacity: 1;
            transform: translateY(0);
        }

        /* ── 响应式 ── */
        @media (max-width: 768px) {
            .container {
                padding: 0 1rem;
                padding-bottom: 2.5rem;
            }
            .card {
                padding: 1.25rem 1.25rem 1.5rem;
                border-radius: 12px;
            }
            .card-core {
                font-size: 0.9rem;
                padding: 0.6rem 0.9rem;
            }
            .card-body {
                font-size: 0.88rem;
            }
            .nav-links a {
                font-size: 0.65rem;
                padding: 0.3rem 0.6rem;
            }
            /* 移动端也保持序号较大 */
            .card-num {
                font-size: 1.1rem;
                /* 原为0.7rem，现在增大 */
            }
        }
        @media (max-width: 480px) {
            .card-body ul li {
                padding-left: 1.1rem;
            }
            .card-title {
                font-size: 1.15rem;
            }
            header {
                padding-top: 2rem;
            }
            .card-num {
                font-size: 1rem;
            }
        }

        /* ── 自定义滚动条 ── */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(0, 212, 255, 0.25);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(0, 212, 255, 0.45);
        }

        /* ── 选择文本 ── */
        ::selection {
            background: rgba(0, 212, 255, 0.3);
            color: #ffffff;
        }
    </style>
</head>


    <!-- 背景装饰 -->


    <!-- 滚动进度条 -->


        <!-- 头部 -->
        <header>

// PROMPT_METHODOLOGY.md


视频生成提示词方法论


一套通用的提示词工作流 —— 让模型生成更稳定、更可控、更符合预期的视频内容。

            <nav class="nav-links" aria-label="快速导航">
                <a href="#step1">01 任务类型</a>
                <a href="#step2">02 结构顺序</a>
                <a href="#step3">03 变化路径</a>
                <a href="#step4">04 素材职责</a>
                <a href="#step5">05 视觉锚点</a>
                <a href="#step6">06 任务拆分</a>
                <a href="#step7">07 限制条件</a>
            </nav>
        </header>

        <!-- 步骤 01 -->
        <section id="step1" class="card card-accent-cyan animate-on-scroll">


[01]


TASK_TYPE


先确定任务类型


任务不同，提示词需要解决的问题也不同。


                在编写提示词之前，必须先明确这次生成属于哪一类：


文生视频
 —— 只有文字描述，从零生成视频


首帧生视频
 —— 给一张起始画面，让视频从这张图开始动起来


首尾帧生视频
 —— 给开头和结尾两张图，让模型生成中间变化过程


多图 / 多视频参考
 —— 用多张图或多个视频作为风格、角色、场景参考


                    比如首尾帧任务的重点是
"怎么从A变到B"
，而文生视频的重点是从无到有地建立画面。先定位类型，才能精准发力。


        </section>

        <!-- 步骤 02 -->
        <section id="step2" class="card card-accent-purple animate-on-scroll">


[02]


STRUCTURE


先概括整体，再按时间顺序展开


先全局认知，再逐步执行。


                不要一上来就写细节，分两步走：


Step 1：
告诉模型这条视频整体在讲什么、氛围是什么、大概是什么场景


Step 2：
按时间顺序，一段一段描述动作、变化、结果


                    例如：
"整体是一个女孩在雨夜街道上行走的短片。开头她站在路灯下，随后抬头看天，接着雨变大，她撑起伞向前走，最后消失在街角。"
 模型先有全局画面，输出才会连贯。


        </section>

        <!-- 步骤 03 -->
        <section id="step3" class="card card-accent-green animate-on-scroll">


[03]


TRANSITION


不要只写结果，要写清楚变化路径


把"怎么变过去"写出来。


                尤其是变形和首尾帧任务，不能只说
"从猫变成汽车"
，而要写清楚：


形状
怎么变 —— 拉长、收缩、扭曲、分裂


材质
怎么过渡 —— 毛发转金属、布料转玻璃


颜色
怎么衔接 —— 从黑灰过渡到红色


运动方向
怎么延续 —— 旋转、平移、缩放


                    例如：
"猫的身体逐渐拉长，四肢收进身体两侧，毛发质感转为金属反光，颜色从黑灰色过渡为红色，同时整体向画面右侧旋转。"
 这能帮助模型找到A到B之间的对应关系，减少跳变和崩坏。


        </section>

        <!-- 步骤 04 -->
        <section id="step4" class="card card-accent-amber animate-on-scroll">


[04]


REFERENCE_ROLE


给参考素材分配明确职责


一张图尽量只承担一个主要任务。


                如果提供了多张参考图或多段视频，要说明每张图负责什么：


图1：
角色形象


图2：
场景构图


图3：
色彩风格


图4：
某个关键帧动作


                    不要指望一张图同时决定角色、场景、光影和构图，否则模型容易混淆。职责越清晰，生成越精准。


        </section>

        <!-- 步骤 05 -->
        <section id="step5" class="card card-accent-pink animate-on-scroll">


[05]


VISUAL_ANCHOR


设置稳定的视觉锚点


固定不变的元素，让画面保持统一。


                视频生成中，不同镜头或时间段之间容易"画风突变"。解决方法是固定一些锚点：


主体外观：
发型、体型、五官特征


服装：
颜色、款式、材质


镜头构图：
一直保持中景、低角度等


色彩系统：
整体色调偏冷、胶片感等


遮罩 / 界面框架：
如果有UI或特定画幅，要固定


        </section>

        <!-- 步骤 06 -->
        <section id="step6" class="card card-accent-orange animate-on-scroll">


[06]


DECOMPOSE


复杂视频要拆成可执行的小任务


不要只给抽象故事，要给具体可执行的镜头指令。


                将每个镜头写清楚：


当前状态：
他站在哪里、什么样子


主体动作：
他做了什么


画面变化：
周围发生了什么


镜头运动：
推近、拉远、跟随、环绕


声音反馈：
脚步声、风声、音乐变化


                    每个小任务越具体，模型越容易生成稳定结果。


        </section>

        <!-- 步骤 07 -->
        <section id="step7" class="card card-accent-teal animate-on-scroll">


[07]


CONSTRAINTS


用限制条件收住发挥范围


划定边界，防止画面失控。


                在提示词最后，加上明确的"不要"或"必须"：


禁止新增人物


禁止重复文字


保持服装一致


保持遮罩不变


不要改变色调


不要出现额外物体


                    这些限制条件相当于给模型划定边界，防止它自由发挥导致结果偏离预期。


        </section>

        <!-- 总结 -->
        <section class="summary-card animate-on-scroll">

整体逻辑总结


                这段文案的核心思路是：


先定义任务 → 再建立全局 → 然后描述变化过程 → 分配参考素材 → 固定视觉锚点 → 拆分镜头执行 → 最后用限制条件收束。


                它强调的是：
视频提示词不是写故事，而是写"可执行的画面指令"。
越具体、越有结构、越有边界，生成结果就越稳定可控。


        </section>

        <!-- 页脚 -->
        <footer>

PROMPT_METHODOLOGY


·


v1.0


·


STABLE_VIDEO_OUTPUT

        </footer>


    <script>
        // ── 滚动进度条 ──
        const progressBar = document.getElementById('scrollProgress');
        window.addEventListener('scroll', () => {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
            progressBar.style.width = progress + '%';
        });

        // ── 滚动渐入动画 (Intersection Observer) ──
        const observerOptions = {
            root: null,
            rootMargin: '0px 0px -80px 0px',
            threshold: 0.08,
        };
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    // 可选：一旦可见就不再观察，减少性能开销
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.animate-on-scroll').forEach((el) => {
            observer.observe(el);
        });

        // ── 平滑滚动（对锚点链接增强） ──
        document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId && targetId.length > 1) {
                    const targetEl = document.querySelector(targetId);
                    if (targetEl) {
                        e.preventDefault();
                        targetEl.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start',
                        });
                    }
                }
            });
        });

        // ── 页面加载完成后，立即触发首屏动画 ──
        window.addEventListener('load', () => {
            // 稍微延迟，确保初始动画状态正确
            setTimeout(() => {
                document.querySelectorAll('.animate-on-scroll').forEach((el) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.top < window.innerHeight && rect.bottom > 0) {
                        el.classList.add('visible');
                        observer.unobserve(el);
                    }
                });
            }, 150);
        });
    </script>


</html>
