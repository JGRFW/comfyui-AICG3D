# Prompt Guides

## 怎么增删提示词方案（不用改代码，也不用重启 ComfyUI）

「提示词优化设置 → 提示词方案」里的下拉列表就是这个目录扫出来的，**一个子目录 = 一个方案**。

新增：在 `prompt_guides/` 下建一个目录，把正文放进去，刷新浏览器（`Ctrl+F5`）即可。

```
prompt_guides/
    我的方案/                目录名就是方案 id（想另起 id 就写 meta.json）
        guide-zh.md          中文正文（可选）
        guide.md             英文正文（可选；只有一份时中英共用）
        meta.json            可选，见下
        references/          可选：附带的参考文件（.md / .txt），会一起喂给模型
```

`meta.json`（可选）——用来指定 id、显示名和适用语言：

```json
{ "id": "my_guide", "name": "My Scheme", "name_zh": "我的方案", "languages": ["zh", "en"] }
```

删减：直接删掉对应的目录即可，列表和节点参数会跟着消失。

几点说明：

- 正文文件名只有这几种会被认：`guide-zh.md` / `guide.cn.md` / `SKILL.cn.md`（中文），`guide.md` / `SKILL.md` / `README.md`（中英共用）。
- 没有 `meta.json` 时，方案名就是目录名，适用语言按实际存在的正文判断。
- `languages` 控制它在哪种「提示词语言」下出现，不写就是中英都出现。
- `manifest.json` 仍然保留，优先级高于目录扫描：它固定了随插件发布的方案的 id 与显示名，以及「H3 通用 / 基础模式 / 完整参考模式」三份公共规则，所以旧工作流里已经选好的方案不会因为目录改名而错位。自建方案不需要动它。
- `h3_general/` 是常驻的通用规则，不会出现在可选方案列表里。

## Upstream notes

These are complete node-adapted prompt guides based on the MiniMax H3 official prompt-writing resources. They retain the original prompt-writing rules, structures, constraints, examples, and required reference documents. Only Agent-runtime operations that a ComfyUI prompt optimizer cannot execute are removed, such as tool dispatch, canvas manipulation, staged approval waits, external asset generation, assembly, and delivery actions.

The files are intentionally not summarized or simplified. Runtime behavior is defined separately by the optimizer so that a selected prompt guide is used to produce one final MiniMax H3 prompt instead of attempting an Agent workflow.
