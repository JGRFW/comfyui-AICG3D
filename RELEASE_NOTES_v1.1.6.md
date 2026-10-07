# comfyui-AICG3D v1.1.6

![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![comfyui](https://img.shields.io/badge/ComfyUI-custom%20node-1E90FF)
![version](https://img.shields.io/badge/version-1.1.6-green)

本次更新集中修复提示词优化的停止链路与英文输出稳定性，不包含工作流文件更新。

## 1. 分段提示词解析支持停止优化

`AICG3D 分段提示词解析` 的优化按钮现在会在运行中变为：

`■ 停止优化`

再次点击同一个按钮即可取消，不再出现只能等待模型跑完、没有停止入口的情况。

## 2. 视频段落停止按钮真正中断本地模型

提示词优化的请求现在带有唯一 `request_id`。点击停止时：

- 浏览器会中断当前请求。
- 前端会调用后端取消接口。
- 后端会设置对应请求的取消事件。
- 本地 GGUF 流式生成会在下一个 token 之间停止。
- Transformers 本地模型会在生成步之间停止。
- 取消完成后继续执行模型释放与缓存清理。

## 3. 英文输出规则优先级提高

修复小模型选择英文输出后仍然返回中文或几乎不变化的问题：

- 最终输出语言规则移动到系统提示词最末。
- 分段格式自动重试时再次附加语言锁。
- 英文模式会明确要求叙述、镜头、声音和音乐说明全部改写为英文。
- 用户对白、歌词和画面文字仍保留原语言。

## 4. 同步文件

- `h3easy/nodes.py`
- `h3goohai/prompt_optimizer.py`
- `web/minimax_h3_easy_ui.js`
- `web/aicg3d_prompt_split.js`
- 插件版本：`1.1.6`
- 本版本未更新 `workflows/` 目录中的工作流文件。

## 升级方法

1. 更新本插件仓库。
2. 重启 ComfyUI。
3. 浏览器执行 `Ctrl+F5`，确保新的前端脚本加载。
4. 重新打开提示词优化设置，确认输出语言仍为所需的 `English` 或 `中文`。
