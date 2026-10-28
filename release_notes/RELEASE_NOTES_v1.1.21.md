# comfyui-AICG3D v1.1.21

> 版本日期：2026-10-28  
> 本版本修复 ComfyUI Registry / Manager 发布包遗漏工作流和中文资源的问题。

## 为什么发布 1.1.21

`1.1.20` 已成功上传到 Registry，但下载发布包检查后发现：GitHub 仓库里有工作流，Registry 生成的 `node.zip` 却没有任何 `workflows/` 文件。原因是 Registry 发布 Action 在 Linux 上保留了 Git 默认的路径转义，打包工具无法正确识别中文文件名，因而跳过了全部中文工作流和部分中文技能资源。

Registry 已发布版本不可覆盖，因此使用 `1.1.21` 发布完整安装包。

## 修复

- Registry 发布 Action 在打包前关闭 `core.quotepath`，保证中文路径按真实 UTF-8 文件名处理。
- 发布任务设置 `PYTHONUTF8=1`，避免 Windows/Linux 默认编码差异。
- 新增 Registry 下载包自动验收：发布后下载 `node.zip`，必须包含完整 Web 入口、后端节点、许可证以及至少 9 个工作流，否则工作流失败。
- 保留 1.1.20 的全部修复：旧节点兼容、资源库上传、PromptSplit 新旧 ID、Nodes 2.0 布局和单段抽卡缓存。

## 验证

- Python `compileall` 通过。
- 全部 `web/*.js` 语法检查通过。
- `comfy node validate` 通过。
- 10 项开源安全与兼容回归测试通过。
- 5 项接缝、曝光锁定和段落缓存连续性测试通过。
- Registry 发布包下载后会自动验证工作流数量和关键文件，防止再次发布空工作流包。

## 版本

- Registry 版本：`1.1.21`。
- Registry 包名：`aicg3d-h3-suite`。
- Publisher：`aicg3d`。
