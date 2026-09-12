# third_party — 第三方许可证原件

这个目录只放**许可证原文**，不放代码。它们的正文被本插件的
`THIRD_PARTY_NOTICES.md` 引用。

| 文件 | 对应组件 | 许可证 |
|---|---|---|
| `GPL-3.0.txt` | 本插件自身 + `h3goohai/`（源自 Goohai-MiniMax-H3_Integration） | GPL-3.0（全文） |
| `LICENSE-ComfyUI-MiniMaxH3-Easy-MIT.txt` | `h3easy/`、`web/minimax_h3_easy_ui.js` | MIT |
| `LICENSE-Goohai-MiniMax-H3_Integration-GPL-3.0-or-later.txt` | `h3goohai/`、`web/minimax_h3_integration.js`、`web/audio/done.mp3` | GPL-3.0-or-later（原始声明） |
| `LICENSE-MiniMax-H3-Community.txt` | `skills/`、`prompt_guides/` 中的 MiniMax H3 官方提示词内容 | MiniMax H3 Community License Agreement |

## 为什么 `LICENSE` 是 GPL-3.0 全文

本插件由 MIT 组件（`h3easy/`）与 GPL-3.0-or-later 组件（`h3goohai/`）合并而成。
把两者组合成一个作品分发时，整体必须按 GPL-3.0-or-later 发布，并且必须向接收者
提供 GPL 全文——所以仓库根目录的 `LICENSE` 就是 GPL-3.0 的完整正文。

MIT 组件**不会**因为被合并而失去它的 MIT 许可：它的版权声明与许可声明保留在
`h3easy/` 各文件头部与 `LICENSE-ComfyUI-MiniMaxH3-Easy-MIT.txt` 里。

## MiniMax H3 内容单独说明

`skills/`、`prompt_guides/` 里的 MiniMax 官方提示词内容**不适用** GPL-3.0，而是
适用 MiniMax H3 Community License Agreement。它带有 GPL 不允许的附加限制
（地域、商业规模、Acceptable Use Policy），因此这两套内容在本仓库中是**独立分区**，
不是"整体 GPL 作品"的组成部分。详见 `THIRD_PARTY_NOTICES.md` 第 3 节。
