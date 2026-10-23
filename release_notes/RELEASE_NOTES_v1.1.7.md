# comfyui-AICG3D v1.1.7

![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![comfyui](https://img.shields.io/badge/ComfyUI-custom%20node-1E90FF)
![version](https://img.shields.io/badge/version-1.1.7-green)

本次更新修复资源库素材点击后无法按当前光标位置写入提示词的问题。

## 1. 光标位置插入

- 点击素材库图片、视频或音频时，标签会插入到用户最后操作的光标或选区位置。
- 编辑器失焦后仍保留最后一次光标，不会因为资源库卡片获得焦点而退回文本末尾。
- 支持替换当前选区，并在插入后把光标放在新标签之后。

## 2. 原生 textarea 兼容

- 同时检查节点内隐藏 textarea 和用户实际操作的可见编辑框。
- 存在多个输入控件时，优先使用用户最后点击的真实输入框。
- 保留富文本提示词编辑器原有的选区记录与恢复机制。

## 3. 前端缓存规避

- 前端入口从 `web/minimax_h3_easy_ui.js` 改为 `web/minimax_h3_easy_ui_v3.js`。
- 浏览器会加载新的模块路径，避免继续运行旧缓存脚本。
- ComfyUI 重启后如果页面没有自动刷新，请关闭旧页面或按 `Ctrl+F5` 强制刷新。

## 4. 同步文件

- `web/minimax_h3_easy_ui_v3.js`
- `web/minimax_h3_integration.js`
- `pyproject.toml`
- `README.md`
- 插件版本：`1.1.7`

## 升级方法

1. 更新本插件仓库。
2. 完全关闭并重新打开 ComfyUI。
3. 如果界面仍停留在旧页面，执行 `Ctrl+F5`。
4. 在“创意描述”中把光标放到指定位置，再点击资源库素材验证插入位置。
