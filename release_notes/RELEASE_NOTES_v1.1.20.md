# comfyui-AICG3D v1.1.20

> 版本日期：2026-10-28  
> 本次更新面向 ComfyUI Manager / Comfy Registry 的干净安装、旧工作流兼容和前端初始化稳定性。

## 严格审核结果

本次不是只检查“本机能不能打开”，而是按全新用户安装路径重新审核了以下环节：

- Python 包入口、节点注册表、依赖声明和可选模块导入。
- Registry `pyproject.toml` 元数据、`.comfyignore`、Web 静态文件打包范围。
- Nodes 2.0 与经典节点模式的前端扩展安装。
- 资源库上传、媒体状态保存、文件列表恢复。
- 分段提示词解析节点的文本控件、一键填入、优化提示词按钮和旧节点 ID。
- 与上游 `ComfyUI-MiniMaxH3-Easy`、旧 `PromptSplit` 插件的命名空间冲突。

## 修复

- `AICG3D_H3PromptSegmentSplit` 和旧 ID `AICG3DPromptSegmentSplit` 现在都会安装完整前端控件。
- 增加 `loadedGraphNode` 兜底初始化，工作流加载后即使 `nodeCreated` 时机不同，也不会丢失“一键填入全部视频段落”和“✦ 优化提示词”按钮。
- 当没有其他上游 H3 插件占用时，注册旧版 `MiniMaxH3EasyMediaLoader`、`MiniMaxH3EasySequenceGlobal`、`MiniMaxH3EasySequenceSegment`、`MiniMaxH3EasySequenceCombine` 兼容 ID，避免旧工作流显示白板。
- 前端归属判断改为大小写不敏感的包名匹配，并区分“本插件的旧版兼容节点”和真正的外部上游节点。
- Nodes 2.0 资源库面板严格限制在节点内部 320px 区域，素材列表内部滚动，不再向下溢出。
- 资源库上传面板现在会同步清理和恢复父容器布局状态，收起后不会残留固定高度或遮挡节点。
- 上传按钮改为复用已挂载到页面的隐藏文件输入控件，避免部分浏览器或内嵌 WebView 中点击“上传媒体”无反应。
- 资源面板只在 Nodes 2.0 下执行父容器高度修补，经典节点模式不再受到 Nodes 2.0 布局代码影响。
- “抽卡时段”现在只执行被点击的目标段：前端会把上一段改为从本次 ComfyUI 进程的段落缓存读取，并切断 `previous_segment` 的上游调度，避免第一段或前半链陪跑。
- 单段抽卡完成后，右上角运行只进入最终缓存合成模式，不重新生成其他段落。
- README 和安装文档明确：资源库、分段提示词解析与 H3 核心节点已内置，不需要额外安装上游 Easy 或独立 PromptSplit 插件。
- `pyproject.toml` 的许可证元数据改为引用随包分发的 `LICENSE` 文件，符合 Comfy Registry 推荐格式。

## 验证

- Python `compileall` 通过。
- 全部 `web/*.js` 的 `node --check` 通过。
- `comfy node validate` 通过。
- 10 项开源安全与兼容回归测试通过。
- 5 项接缝、曝光锁定和段落缓存连续性回归测试通过。
- 后端 `/upload/image` 与前端文件选择器实测上传成功，图片、音频和视频均能保存为资源库媒体，卡片和状态同步更新。
- Nodes 2.0 下资源库面板实测：面板底部不超出节点内容区域；默认节点高度不足时只增高，已有尺寸不会被缩小。
- 新旧分段提示词解析节点均实测包含文本控件、`一键填入全部视频段落`、`✦ 优化提示词`。
- 三段工作流实测自动填入每个段落正文，第一段提示词编辑器可输入，节点在填词前后保持 `420×760` 不变。
- 13 号工作流实测单段抽卡目标、最终缓存合成目标和节点尺寸不变。
- Registry 打包实测包含 9 个工作流、完整 Web 文件、许可证和第三方声明，并正确排除测试与 `.github` 开发目录。

## 版本

- 版本号提升至 `1.1.20`。
- Registry 包名保持 `aicg3d-h3-suite`，Publisher 保持 `aicg3d`。
