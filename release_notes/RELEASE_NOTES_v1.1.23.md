# comfyui-AICG3D v1.1.23

![version](https://img.shields.io/badge/version-1.1.23-green)

## 本次更新

### 内置 Spark-TTS

- Spark-TTS 推理源码、ComfyUI 节点封装和 5 个 `Step-Audio-speakers` 参考音频已并入主插件。
- 内置节点：`AICG3D_SparkTTSRun`、`AICG3D_SparkTTSClone`，归入 `AICG3D/语音` 分类。
- 不再依赖外部 `ComfyUI_SparkTTS`，旧节点 ID 只在外部插件不存在时提供兼容。
- 模型目录兼容 `models/tts/Spark-TTS-0.5B` 和 `models/TTS/Spark-TTS-0.5B`。
- 缺模型时会显示模型目录、缺失文件、下载地址和缺少的运行依赖。
- 真实验证生成 16 kHz 非静音音频，RMS 约 `0.09039`。

### 可选角色音色库

- 添加 `MiniMax H3 Aicg 角色音色库` 时，固定角色声线、克隆音色和试听功能正常工作。
- 不添加该节点时，前端会清除失效的 `voice_cast` 链接，后端不会从上一段缓存继承旧音色，工作流按普通 H3 模式运行。
- 音色库节点被静音或旁路时，同样视为未添加。
- `voice_cast` 始终为可选输入，不会出现缺少必需输入的报错。

### 克隆音色模式精简界面

- 选择“克隆音色”时，仅显示角色名、画面绑定、参考音频上传/截取、授权和试听。
- 固定声线描述、声线模板、关键词、语言、年龄、性别、音高、语速等描述音色控件自动隐藏。
- 克隆模式音色只由参考音频定义，不再把隐藏的固定声线描述写入 H3 音色元数据。
- 切回“描述音色”后，全部生成控件自动恢复。

### 依赖与发布

- 增加 Spark-TTS 所需的 `omegaconf`、`soundfile`、`soxr`、`einx`、`einops`、`librosa` 和 `transformers` 依赖。
- Registry 发布流程改为仅允许手动触发，普通 GitHub 推送不会自动发布。
- 随包附带 Spark-TTS Apache 2.0 许可证与第三方组件声明。

## 版本

- Registry 版本：`1.1.23`
- 仓库：https://github.com/JGRFW/comfyui-AICG3D
- 工作流下载：https://github.com/JGRFW/comfyui-AICG3D/tree/main/workflows
