# comfyui-AICG3D v1.1.10

本次更新解决单独安装本插件时资源库节点白板、必须额外安装 `ComfyUI-MiniMaxH3-Easy` 的问题。

## 根因

插件启动时会输出带 Emoji 的初始化日志。部分 Windows 环境使用 GBK 控制台编码，无法编码 Emoji，`print` 抛出 `UnicodeEncodeError`，插件加载流程随后把整个插件判定为加载失败，节点注册被清空。

当用户另外安装上游 `ComfyUI-MiniMaxH3-Easy` 时，上游补上了同名或相近节点注册，所以表面上看起来资源库恢复可用。

## 修复

- 插件启动日志全部改为编码安全输出。
- 不再输出无法被 GBK 编码的 Emoji。
- 异常日志改为先格式化，再通过安全输出函数写入。
- 单独加载 `ComfyUI-AICG3D-Integrated` 时，后端不会再因为控制台编码而整体加载失败。
- 资源库前端面板已经随本插件内置，不需要上游 Easy 插件补界面。

## 验证

使用 ComfyUI 的隔离模式仅加载本插件：

```text
--disable-all-custom-nodes
--whitelist-custom-nodes ComfyUI-AICG3D-Integrated
```

验证结果：

- `AICG3D_H3MediaLoader` 正常注册。
- 资源库节点正常创建。
- 上传媒体、图片、音频、视频分区正常显示。
- 未出现 Python 加载失败或前端白板。

## 升级方法

1. 更新到 v1.1.10。
2. 不需要再安装 `ComfyUI-MiniMaxH3-Easy`。
3. 重启 ComfyUI。
4. 浏览器执行 `Ctrl+F5`。
