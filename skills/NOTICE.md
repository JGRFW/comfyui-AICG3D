# 来源与修改声明（skills/）

**本目录中的技能文件已被修改。**

## 原始出处

本目录内容源自 MiniMax 官方仓库 https://github.com/MiniMax-AI/MiniMax-H3 的
`skills/` 目录，包含 `h3-prompt-writing`（H3 提示词编写规范）与官方风格技能
（3D 动画短片、品牌宣传短片、双人游戏开场、手绘实拍融合、极简产品广告、
音乐 MV 动态字幕、纸拼贴讲解、纸艺定格科普）。

## 修改内容

与上游相比，本目录做了以下改动：

1. 按 ComfyUI 节点场景改写：删除 Agent 运行时行为（工具分发与调用、画布操作、
   交互式确认等待、外部生成/编辑分发、项目初始化、成片组装、文件交付）。
2. 保留全部提示词编写知识、结构、约束、示例与参考资料原文，未作摘要或压缩。
3. 为技能补充 `meta.yaml`，加入中文显示名、摘要与分类，供插件技能库检索。
4. 部分目录名改为中文前缀，用于技能库中的分组显示。

改造规则详见 `../prompt_guides/ADAPTATION_NOTES.md`。

## 许可证

本目录内容适用 **MiniMax H3 Community License Agreement**，
全文见 `../third_party/LICENSE-MiniMax-H3-Community.txt`。

该许可要求的声明原文：

> MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.

请注意该许可的地域限制（不含欧盟、英国、韩国、美国）、商业规模条款与
Acceptable Use Policy。要点摘要见 `../THIRD_PARTY_NOTICES.md` 第 3 节。

本目录内容不适用本插件的 GPL-3.0-or-later 许可。

## 目录中另外补充的非 MiniMax 技能

本目录下另有若干来自中文 AI 创作社区公开合集的技能包（详见各自 `meta.yaml` 的
`source:` 字段），它们没有标注授权信息，版权归各原始作者，本仓库不作权利主张。
权利人要求移除时请在仓库提 issue。
