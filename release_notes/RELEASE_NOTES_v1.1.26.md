# comfyui-AICG3D v1.1.26

![version](https://img.shields.io/badge/version-1.1.26-green)

## 本次更新

### ComfyUI Manager 启动卡死修复

- 根目录 `requirements.txt` 改为零自动安装，不再让 ComfyUI Manager 在启动阶段联网下载大型依赖。
- `pyproject.toml` 的强制依赖改为空列表，Registry 安装不会再额外触发 `imageio-ffmpeg` 等包的自动安装。
- 修复部分用户安装后在 ComfyUI 启动界面长期卡在 `pip install imageio-ffmpeg` 或下载超时的问题。
- ComfyUI、PyTorch、torchaudio、requests、aiohttp、numpy 等运行环境继续使用 ComfyUI 本体提供版本，不重复安装或覆盖。

### 可选依赖拆分

- 新增 `requirements-optional.txt`，集中列出音色克隆、Spark-TTS、提示词优化和 FFmpeg 合成所需依赖。
- 根目录不会自动安装可选依赖；需要相应功能时，用户可手动执行：

```bash
python -m pip install -r requirements-optional.txt
```

- 最终视频合成优先使用系统 FFmpeg；没有 FFmpeg 时，节点会提示安装 `imageio-ffmpeg`、设置 `VHS_FORCE_FFMPEG_PATH` 或将 `ffmpeg.exe` 加入 `PATH`。
- Spark-TTS 和角色音色库缺少依赖时只在对应功能运行时提示，不会阻止 ComfyUI、主 H3 节点和其他工作流启动。

### 兼容性

- 保留上一版 SeedVR2、RTX VSR、VOSR2 二采修复链。
- 保留角色音色库在经典节点模式与 Nodes 2.0 下的自动布局修复。
- 适用于 ComfyUI 自定义节点管理器和 Comfy Registry 安装方式。

## 版本

- Registry 版本：`1.1.26`
- 仓库：https://github.com/JGRFW/comfyui-AICG3D
- 可选依赖：https://github.com/JGRFW/comfyui-AICG3D/blob/main/requirements-optional.txt
