# AICG3D 内置 Spark-TTS

本目录把 Spark-TTS 推理源码、ComfyUI 节点封装和 5 个说话人参考音频一起打包进
`comfyui-AICG3D`。用户不需要再安装 `ComfyUI_SparkTTS`。

## 节点

- `AICG3D_SparkTTSRun`：按性别、年龄、音高和语速生成固定声线。
- `AICG3D_SparkTTSClone`：使用内置说话人或自定义参考音频克隆声线。

只有外部 Spark 插件没有注册旧节点时，本插件才提供 `SparkTTSRun` / `SparkTTSClone`
兼容 ID，避免和其他插件抢占。

## 模型目录

模型权重不随插件分发。把 Hugging Face 的完整模型目录放到：

```text
ComfyUI/
└─ models/
   └─ tts/
      └─ Spark-TTS-0.5B/
         ├─ config.yaml
         ├─ BiCodec/
         ├─ LLM/
         └─ wav2vec2-large-xlsr-53/
```

`models/TTS/Spark-TTS-0.5B` 也兼容。也可设置：

```text
AICG3D_SPARK_TTS_MODEL=<完整的 Spark-TTS-0.5B 目录>
AICG3D_SPARK_TTS_SPEAKERS=<可选的 Step-Audio-speakers 覆盖目录>
```

下载地址：https://huggingface.co/SparkAudio/Spark-TTS-0.5B

插件内置 `assets/Step-Audio-speakers`。如果 `models/tts/Step-Audio-speakers` 存在，
则优先使用外部目录，便于用户添加或替换说话人。

## 缺模型时

- 角色音色库会显示模型状态和下载入口。
- Spark 文本输入框的鼠标提示包含模型目录和下载地址。
- 运行时若模型缺失，会报告期望目录、缺失文件、下载地址和需要的运行依赖，不会只报
  `FileNotFoundError`。

## 许可证

推理源码来自 SparkAudio/Spark-TTS 及其 ComfyUI 集成，按 Apache License 2.0 使用。
许可证全文位于 `third_party/LICENSE-ComfyUI_SparkTTS-Apache-2.0.txt`。
