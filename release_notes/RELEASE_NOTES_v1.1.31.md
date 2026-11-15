# comfyui-AICG3D v1.1.31

![version](https://img.shields.io/badge/version-1.1.31-green)

本版本是针对 Comfy Registry 安全扫描的修复发布。插件功能、节点接口和现有工作流保持不变，重点消除可携带 API Key 的请求被重定向或发送到非预期地址的风险。

## Registry 安全扫描修复

- Gemini Native 接口的 API Key 仅通过 `x-goog-api-key` 请求头发送，不再拼接到 URL 查询参数。
- 用户填写的接口地址会先清理 URL 中可能包含的 `key`、`token`、`secret`、`password`、`signature` 等凭据参数。
- 携带凭据的远程请求只允许使用 HTTPS，并且只允许受支持的官方服务地址。
- 本地 Ollama、本地模型和自建回环服务继续支持 HTTP，但只允许回环地址。
- 禁止 API 地址包含内嵌用户名、密码或 URL 片段。
- 禁止非回环私有 IP、链路本地地址和本地专用域名，降低服务端请求伪造风险。

## 请求链路加固

- 提示词优化、Gemini、OpenAI Compatible、Responses 和 RunningHub 请求全部禁用自动重定向。
- 上述请求不使用系统环境代理，避免凭据被代理配置转发到其他主机。
- RunningHub 返回的文本结果在下载前执行相同的目标地址校验。
- Ollama 模型卸载接口使用相同的地址校验、重定向和代理策略。
- 不支持的远程密钥地址会在发送任何凭据之前直接给出明确错误。

## 兼容说明

- ComfyUI 内置节点、AICG3D 节点名称、接口和工作流绑定关系不变。
- `10`、`11`、`12`、`13`、`18`、`20`、`22` 号工作流随 Registry 包继续完整发布。
- 使用官方 Gemini、OpenAI、OpenRouter、DashScope、SiliconFlow 或 RunningHub 接口不受影响。
- 使用本地 Ollama 时仍可使用 `http://127.0.0.1:11434` 或 `http://localhost:11434`。

## 验证

- ComfyUI 运行环境 Python 编译检查通过。
- 17 项开源发布审计全部通过。
- 已验证带凭据 URL 清理、Gemini 请求头传 Key、重定向禁用、环境代理禁用和危险地址拦截。
- Registry 发布 Action 继续精确校验前端文件、后端入口、许可证和 7 个维护中的工作流。

## 版本

- Registry 版本：`1.1.31`
- 仓库：https://github.com/JGRFW/comfyui-AICG3D
- 版本说明：https://github.com/JGRFW/comfyui-AICG3D/blob/main/release_notes/RELEASE_NOTES_v1.1.31.md
