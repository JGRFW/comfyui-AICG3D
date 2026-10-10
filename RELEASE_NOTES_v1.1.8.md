# comfyui-AICG3D v1.1.8

本次更新补齐 13 号无限长视频工作流最终合成所需的 FFmpeg 运行依赖。

## 修复

- `AICG3D_H3SequenceCombine` 使用流式解码与编码，会强制检查 FFmpeg。
- 插件现在声明 `imageio-ffmpeg` 为 Python 依赖。
- 未检测到 FFmpeg 时，节点会给出中文安装提示和当前 ComfyUI Python 的完整安装命令。
- 仍兼容系统 `PATH` 中的 `ffmpeg.exe` 和 `VHS_FORCE_FFMPEG_PATH`。

## 安装

如果在旧环境中手动安装，请使用 ComfyUI 自己的 Python：

```powershell
python.exe -m pip install imageio-ffmpeg
```

安装完成后重启 ComfyUI。