# comfyui-AICG3D v1.1.19

> 版本日期：2026-10-25  
> 本次更新是一次面向公开发布的开源安全、节点兼容和 UI 稳定性审计。

## 开源安全

- 集成节点改用 `AICG3D_H3*` 独立命名空间，不再注册通用 `MiniMaxH3IntegrationGH*` 节点 ID。
- 旧工作流加载时通过 `beforeConfigureGraph` 自动迁移到新节点 ID，不需要重新接线。
- 提示词优化 API Key 移出插件源码目录，保存到 `ComfyUI/user/default/aicg3d/`。
- 工作流和设置接口只保存、返回 `has_api_key`，不再写入真实 Key。
- 旧版配置文件会自动迁移，迁移成功后删除源码目录中的旧文件。
- 参考素材路径增加目录边界校验，拒绝绝对路径、NUL、`..` 和符号链接逃逸。
- 移除 KJNodes 预览功能的 `sys.modules` 伪包注入，改用 ComfyUI 已注册节点表。
- 插件初始化期间临时加入的 `sys.path` 会在加载结束后移除，避免影响其他插件。
- 后端初始化失败时不再启动半套前端扩展。

## 兼容与 UI

- 修复 Goohai 四个集成节点的显示名、分类和可选依赖加载。
- 补齐内置 3D Latent 放大节点分类，统一归入 `AICG3D/H3 工作流`。
- 资源库节点加入尺寸计算合并调度和重入锁，避免恢复工作流时重复触发 resize。
- 移除多余的 `LGraphCanvas.processKey` 第二层全局包装，仅保留 H3 提示词编辑框所需的保护层。
- 修复本地视觉模型 JPEG 参考图缺少 Data URL 前缀的问题。
- 素材扫描达到上限后立即结束目录遍历，避免大型 `input` 目录产生无效 IO。
- 13 号工作流继续输出 `seam_report` 接缝报告。

## 验证

- 7 项开源安全回归测试通过。
- 4 项接缝曝光与硬切保护测试通过。
- 数字人旧版 RIFE 参数兼容测试通过。
- Python `compileall`、Ruff 致命错误检查和 Pyflakes 通过。
- 全部前端 JavaScript 语法检查通过。
- ComfyUI 重启后注册 40 个生产节点，所有节点均有显示名和有效分类。
- Nodes 2.0 开启时，11、13、15 号工作流完整加载通过。
- Nodes 2.0 关闭时，13 号完整加载通过，11、15 号插件节点逐项创建和配置通过。

## 版本

- 版本号提升至 `1.1.19`。
- Comfy Registry 包名保持 `aicg3d-h3-suite`，Publisher 保持 `aicg3d`。
