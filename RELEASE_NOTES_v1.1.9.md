# comfyui-AICG3D v1.1.9

本次更新修复部分用户打开工作流后，“MiniMax H3 Aicg资源库”节点显示为白板的问题。

## 问题原因

`mediaLoaderResize()` 在测量节点固定高度时，会临时把资源库的 DOM 面板标记为隐藏：

- `domWidget.hidden = true`
- `domWidget.type = "hidden"`

测量结束后，原逻辑会恢复测量前的值。某些工作流加载、标签切换或 Nodes 2.0 重建顺序下，测量开始前面板已经是隐藏状态，因此测量结束后仍保持隐藏，用户看到的就是一块只有节点标题的白板。

## 修复内容

- 测量结束后强制把资源库 DOM 面板恢复为可见。
- 同步修复 `hidden`、`type`、`options.hidden`、`options.canvasOnly` 和 `_state`。
- 保留面板原有类型；即使进入测量时类型已经是 `hidden`，也会恢复到 `h3_media_loader`。
- 不影响节点折叠、画布切换和其他原生控件的独立隐藏状态。

## 前端缓存

入口文件更新为：

- `web/minimax_h3_easy_ui_v4.js`

旧入口不再使用，避免浏览器继续运行旧模块。

## 验证

已在真实 ComfyUI 页面中模拟“resize 前面板已经隐藏”的状态：

- `domWidget.hidden` 恢复为 `false`
- `domWidget.type` 恢复为 `h3_media_loader`
- `options.hidden` 与 `options.canvasOnly` 恢复为 `false`
- `_state` 同步恢复
- 资源库面板保持连接并正常显示“上传媒体 / 图片 / 音频 / 视频”区域

## 升级方法

1. 更新插件仓库。
2. 完全关闭并重新打开 ComfyUI。
3. 如果浏览器仍保留旧页面，按 `Ctrl+F5`。
4. 打开或重新加载工作流，确认“MiniMax H3 Aicg资源库”面板正常显示。
