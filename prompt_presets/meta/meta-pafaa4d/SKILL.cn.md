# H3 极速工作流·安装说明

> 分类：提示词工程 ｜ 来源：MiniMaxH3_提示词Skill_极速工作流\安装说明.md

# MiniMax H3 提示词 Skill — 安装说明

## 一、Skill 简介
本 Skill 用于编写 MiniMax H3 系列视频生成提示词（T2VA / I2VA / FL2VA / L2VA / Ref2VA），自动将多模态请求转换为 H3 提示词结构。

## 二、安装位置
Codex 会扫描用户级 Skills 目录，安装目标：
`C:\Users\用户你的电脑\.codex\skills\h3-prompt-writing\`

## 三、安装步骤
1. 在资源管理器中打开 `C:\Users\wuke_\.codex\skills\`（不存在则先创建）。
2. 将本文件夹整体复制到上述目录下，最终路径为：
   `C:\Users\用户你的电脑\.codex\skills\h3-prompt-writing\`
   注意：必须保留文件夹名 `h3-prompt-writing` 及 `SKILL.md` 文件位于其根目录，否则无法识别。
3. 重启 Codex 应用（或新建对话）使 Skill 生效。

## 四、验证是否安装成功
- 检查最终目录结构：
  ```
  h3-prompt-writing/
  ├─ SKILL.md
  ├─ agents/
  │  └─ openai.yaml
  └─ references/
     ├─ base-en.txt
     └─ ref-en.txt
  ```
- 在 Codex 对话中提问涉及 MiniMax H3 提示词编写的内容，若自动调用本 Skill 即安装成功。

## 五、常见问题
| 问题 | 解决 |
| --- | --- |
| Skill 未被识别 | 确认文件夹名、SKILL.md 位置正确，重启 Codex |
| 想卸载 | 直接删除 `h3-prompt-writing` 文件夹即可 |
| 需要更新 | 用本目录文件覆盖对应位置后重启 Codex |
