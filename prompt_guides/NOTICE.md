# 来源与修改声明（prompt_guides/）

**本目录中的方案文件已被修改。**

## 原始出处

本目录内容基于 MiniMax 官方仓库 https://github.com/MiniMax-AI/MiniMax-H3 提供的
H3 提示词编写资源与官方风格技能改写而来。

## 修改内容

1. 保留原文的提示词编写规则、结构、约束、示例、时序、运镜、动作、画面、对白、
   声音与音乐指导，**不做摘要、合并或压缩**。
2. 只删除 Agent 运行时行为：工具白名单与调用、任务委派、画布操作、交互式确认等待、
   外部生成/编辑分发、项目初始化、成片组装、文件交付。
3. 当一句操作说明同时包含提示词指导时，只删除操作部分，保留提示词指导。
4. 拆分出 `guide.md` 与 `references/`，供 ComfyUI 节点按需注入上下文。

完整改造规则见本目录 `ADAPTATION_NOTES.md`。

## 许可证

本目录内容适用 **MiniMax H3 Community License Agreement**，
全文见 `../third_party/LICENSE-MiniMax-H3-Community.txt`。

该许可要求的声明原文：

> MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.

请注意该许可的地域限制（不含欧盟、英国、韩国、美国）、商业规模条款与
Acceptable Use Policy。要点摘要见 `../THIRD_PARTY_NOTICES.md` 第 3 节。

本目录内容不适用本插件的 GPL-3.0-or-later 许可。

## 额外的社区方案

本目录另有若干来自中文 AI 创作社区公开合集的场景方案（目录名带中文前缀），
没有标注授权信息，版权归各原始作者，本仓库不作权利主张。
