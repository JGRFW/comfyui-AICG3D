/* ==========================================================================
    Copyright (C) 2026 AICG3D
    SPDX-License-Identifier: GPL-3.0-or-later
    本模块为新增代码（整合三个来源插件）
    ========================================================================== */

/* ==========================================================================
    AICG3D · 节点外观与技能节点面板
   - 给合并后的全部节点统一配色，一眼区分三个来源
   - 备注节点（Note / Markdown Note）默认改用系统深灰配色
   - AICG3D_SkillLoader / AICG3D_PromptPreset：把原生下拉换成可检索的卡片面板
   ========================================================================== */
import { app } from "../../scripts/app.js";
import {
    ensureTheme, el, toast, widgetOf, setWidgetValue,
    library, openSkillPalette, selectionText,
    isOwnH3NodeData,
    markWidgetHidden, autoHideWidgets, refreshVueWidgets,
} from "./aicg3d-core.js";

const SKILL_NODE = "AICG3D_SkillLoader";
const PRESET_NODE = "AICG3D_PromptPreset";

/* ------------------------------ 统一配色 ------------------------------ */
const GROUP_STYLE = [
    { match: /^(?:MiniMaxH3Easy|AICG3D_H3)/, color: "#34517c", bgcolor: "#151b24" },
    { match: /^AICG3D_/, color: "#26594f", bgcolor: "#131d1c" },
];

function paintNodeType(nodeType, nodeData) {
    const name = String(nodeData?.name || "");
    const style = GROUP_STYLE.find((entry) => entry.match.test(name));
    if (!style || nodeType.__a3Painted) return;
    // 上游同名插件（ComfyUI-MiniMaxH3-Easy）注册的 H3 节点不刷本插件的配色，
    // 否则两套节点在画布上看起来完全一样。
    const isH3Name = name.startsWith("AICG3D_H3") || name.startsWith("MiniMaxH3Easy");
    if (isH3Name && !isOwnH3NodeData(nodeData)) return;
    nodeType.__a3Painted = true;
    nodeType.color = style.color;
    nodeType.bgcolor = style.bgcolor;
}

/* --------------------- 备注节点配色 --------------------- */
/* ComfyUI 前端把 Note / Markdown Note 硬编码成黄色色板（node_colors.yellow），
   这里把新建的备注节点改回系统默认配色；工作流里已保存的颜色不受影响。 */
const NOTE_NODE_TYPES = new Set(["Note", "MarkdownNote"]);
const NOTE_COLOR_SETTING = "AICG3D.NoteUseSystemColor";

function useSystemNoteColor() {
    try {
        const value = app?.ui?.settings?.getSettingValue?.(NOTE_COLOR_SETTING);
        return value === undefined || value === null ? true : !!value;
    } catch (error) {
        return true;
    }
}

function noteColors() {
    if (useSystemNoteColor()) {
        return {
            color: globalThis.LiteGraph?.NODE_DEFAULT_COLOR || "#333",
            bgcolor: globalThis.LiteGraph?.NODE_DEFAULT_BGCOLOR || "#353535",
        };
    }
    const yellow = globalThis.LGraphCanvas?.node_colors?.yellow || { color: "#432", bgcolor: "#653" };
    return { color: yellow.color, bgcolor: yellow.bgcolor };
}

function paintNote(node) {
    if (!node || !NOTE_NODE_TYPES.has(String(node.type || ""))) return;
    const palette = noteColors();
    node.color = palette.color;
    node.bgcolor = palette.bgcolor;
    node.setDirtyCanvas?.(true, true);
}

function repaintNotes() {
    for (const node of app?.graph?._nodes || []) paintNote(node);
    app?.graph?.setDirtyCanvas?.(true, true);
}

function hookNoteType(nodeType) {
    const proto = nodeType?.prototype;
    if (!proto || proto.__a3NoteColor) return;
    proto.__a3NoteColor = true;
    const original = proto.onNodeCreated;
    proto.onNodeCreated = function (...args) {
        const result = original?.apply(this, args);
        try {
            paintNote(this);
            installNotePasteButton(this);
        } catch (error) {
            console.error("[AICG3D]", error);
        }
        return result;
    };
}

/** Note / Markdown Note 是前端自带的虚拟节点，不会走 beforeRegisterNodeDef，
    所以直接在节点工厂上补配色；工作流已保存的颜色在 configure() 时会被还原。 */
function installNoteColor() {
    const lite = globalThis.LiteGraph;
    if (!lite) return;

    const registered = lite.registered_node_types || {};
    for (const type of NOTE_NODE_TYPES) hookNoteType(registered[type]);

    const factory = lite.createNode;
    if (typeof factory !== "function" || factory.__a3NoteFactory) return;
    const wrapped = function (type, title, options) {
        const node = factory.call(this, type, title, options);
        try {
            paintNote(node);
            installNotePasteButton(node);
        } catch (error) {
            console.error("[AICG3D]", error);
        }
        return node;
    };
    wrapped.__a3NoteFactory = true;
    lite.createNode = wrapped;
}

/* ------------------- 新节点配色（恢复系统默认） ------------------- */
/* 新节点为什么会带颜色？根因不在本插件：tinyterraNodes（ttN）的
   「🌏 Default Node BG Color」会把选中的色板写进
   localStorage['Comfy.Settings.ttN.defaultBGColor']，然后挂在 nodeCreated /
   loadedGraphNode 上给**每一个**节点上色。所以"新建节点"永远带着红/黄/棕的
   色板色，看起来完全不像系统默认配色。这里做两件事：
     ① 启动时清掉这个全局默认色，ttN 之后就不会再染色；
     ② 把已经被它染色的节点还原成系统配色。
   只处理 ttN 自己打过标记（properties.ttNbgOverride 且颜色一致）的节点，
   手动配色、工作流自带配色、其它插件的节点配色都不动。 */
const TTN_COLOR_KEY = "Comfy.Settings.ttN.defaultBGColor";
const TTN_FIX_SETTING = "AICG3D.ResetTtnDefaultNodeColor";

function ttnFixEnabled() {
    try {
        const value = app?.ui?.settings?.getSettingValue?.(TTN_FIX_SETTING);
        return value === undefined || value === null ? true : !!value;
    } catch (error) {
        return true;
    }
}

/** ttN 染过的节点：它会把自己写进 node.properties.ttNbgOverride。 */
function stripTtnTint(node) {
    const override = node?.properties?.ttNbgOverride;
    if (!override || typeof override !== "object" || !override.color) return false;
    if (node.color !== override.color) return false;
    delete node.color;
    delete node.bgcolor;
    delete node.properties.ttNbgOverride;
    node.setDirtyCanvas?.(true, true);
    return true;
}

function clearTtnDefaultColor() {
    if (!ttnFixEnabled()) return false;
    try {
        const raw = globalThis.localStorage?.getItem(TTN_COLOR_KEY);
        if (!raw) return false;
        let parsed = raw;
        try {
            parsed = JSON.parse(raw);
        } catch (error) {
            parsed = raw;
        }
        if (parsed === "default" || parsed === null) return false;
        globalThis.localStorage.removeItem(TTN_COLOR_KEY);
        return true;
    } catch (error) {
        return false;
    }
}

function sweepTtnTints(graph = app?.graph) {
    if (!graph || !ttnFixEnabled()) return 0;
    let fixed = 0;
    const walk = (current) => {
        for (const node of current?._nodes || []) {
            if (stripTtnTint(node)) fixed += 1;
            if (node?.subgraph) walk(node.subgraph);
        }
    };
    walk(graph);
    if (fixed) graph.setDirtyCanvas?.(true, true);
    return fixed;
}

/** 新建 / 载入节点时兜底：ttN 是在 setTimeout 里上色的，所以延后一拍再看一次。 */
function applyNodeColorPolicy(node) {
    if (!node || !ttnFixEnabled()) return;
    const fix = () => {
        try {
            stripTtnTint(node);
        } catch (error) {
            console.error("[AICG3D]", error);
        }
    };
    fix();
    setTimeout(fix, 0);
}

/* ------------------------------ 技能节点 ------------------------------ */
function hideWidget(widget) {
    if (!widget) return;
    widget.__a3Hidden = true;
    markWidgetHidden(widget);
}

function refreshLayout(node) {
    node._widgetSlotsDirty = true;
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
}

function buildSkillPanel(node) {
    const panel = el("div", "a3-panel");
    panel.addEventListener("pointerdown", (event) => event.stopPropagation());

    const head = el("div", "a3-head");
    head.append(el("span", "a3-logo", "AI"), el("span", "a3-title", "技能加载器"));
    const badge = el("span", "a3-badge", "");
    head.append(el("span", "a3-spacer"), badge);
    panel.append(head);

    const card = el("div", "a3-item");
    card.style.cursor = "default";
    const main = el("div", "a3-item-main");
    const title = el("div", "a3-item-title", "自动选择");
    const desc = el("div", "a3-item-desc", "由下游大模型按任务自行挑选技能。");
    main.append(title, desc);
    card.append(main);
    panel.append(card);

    const actions = el("div", "a3-field");
    const pick = el("button", "a3-btn a3-btn--accent", "浏览技能库");
    pick.type = "button";
    const clear = el("button", "a3-btn", "取消技能");
    clear.type = "button";
    actions.append(pick, clear);
    panel.append(actions);

    const hint = el("div", "a3-hint");
    panel.append(hint);

    let detail = null;

    function sync() {
        const value = String(widgetOf(node, "skill")?.value || "");
        const skill = detail?.find((item) => value === item.id || value === `${item.name} [${item.id}]`);
        badge.textContent = skill?.guide_id ? "H3 方案" : skill ? "技能" : "自动";
        title.textContent = skill?.name || "自动选择";
        desc.textContent = skill?.summary || "由下游大模型按任务自行挑选技能。";
        hint.textContent = skill
            ? "输出：技能正文 + 你的任务描述，可直接接到 H3 主节点或对话节点。"
            : "未指定技能时，节点直接输出任务描述文本。";
        clear.disabled = !skill;
    }

    pick.addEventListener("click", () => {
        // 直接复用公共技能库，选中后写回原生下拉，保持工作流可序列化。
        openSkillPaletteForSkillWidget(node, pick);
    });
    clear.addEventListener("click", () => {
        setWidgetValue(node, "skill", "自动选择");
        sync();
    });

    library.skills().then((items) => { detail = items; sync(); }).catch(() => sync());

    return { panel, sync: () => { library.skills().then((items) => { detail = items; sync(); }).catch(sync); } };
}

/** 选中后写回原生下拉，并立即刷新面板。 */
function openPaletteFor(node, anchor = null) {
    globalThis.AICG3D?.openSkillPalette?.(node, anchor);
}

/** 提示词模板节点：和技能节点同款卡片面板，只是数据源换成模板库。 */
function buildPresetPanel(node) {
    const panel = el("div", "a3-panel");
    panel.addEventListener("pointerdown", (event) => event.stopPropagation());

    const head = el("div", "a3-head");
    head.append(el("span", "a3-logo", "AI"), el("span", "a3-title", "提示词模板"));
    const badge = el("span", "a3-badge a3-badge--preset", "未选");
    head.append(el("span", "a3-spacer"), badge);
    panel.append(head);

    const card = el("div", "a3-item");
    card.style.cursor = "default";
    const main = el("div", "a3-item-main");
    const title = el("div", "a3-item-title", "未选择模板");
    const desc = el("div", "a3-item-desc", "从模板库里挑一条提示词模板，点选即写入提示词。");
    const meta = el("div", "a3-item-meta");
    main.append(title, desc, meta);
    card.append(main);
    panel.append(card);

    const actions = el("div", "a3-field");
    const pick = el("button", "a3-btn a3-btn--accent", "浏览提示词模板");
    pick.type = "button";
    const clear = el("button", "a3-btn", "清空模板");
    clear.type = "button";
    actions.append(pick, clear);
    panel.append(actions);

    const hint = el("div", "a3-hint");
    panel.append(hint);

    let detail = null;

    function sync() {
        const value = String(widgetOf(node, "preset")?.value || "");
        const item = detail?.find((entry) => value === entry.label || value === entry.id);
        badge.textContent = item ? (item.category_name || "模板") : "未选";
        title.textContent = item?.name || "未选择模板";
        desc.textContent = item?.summary || "从模板库里挑一条提示词模板，点选即写入提示词。";
        meta.textContent = "";
        if (item) {
            meta.append(el("span", "a3-tag", item.category_name || "模板"));
            if (item.chars) meta.append(el("span", "a3-dim", `${item.chars} 字`));
        }
        hint.textContent = item
            ? "输出：模板正文 + 你的任务描述，可直接接到 H3 主节点或对话节点。"
            : "未选择模板时，节点直接输出任务描述文本。";
        clear.disabled = !item;
    }

    pick.addEventListener("click", () => openPaletteFor(node, pick));
    clear.addEventListener("click", () => {
        const widget = widgetOf(node, "preset");
        if (widget) setWidgetValue(node, "preset", "");
        sync();
    });

    const load = () => library.presets()
        .then((items) => { detail = items; sync(); })
        .catch(() => sync());
    load();

    return { panel, sync: load };
}

const PALETTE_NODES = [
    { id: SKILL_NODE, widget: "skill", dom: "aicg3d_skill", build: buildSkillPanel },
    { id: PRESET_NODE, widget: "preset", dom: "aicg3d_preset", build: buildPresetPanel },
];

/** 把两个下拉节点都换成本插件统一的卡片面板。 */
function installPaletteNode(nodeType, nodeData) {
    const config = PALETTE_NODES.find((entry) => entry.id === nodeData?.name);
    if (!config) return;
    if (nodeType.prototype.__a3PaletteInstalled) return;
    nodeType.prototype.__a3PaletteInstalled = true;

    autoHideWidgets(nodeType, [config.widget]);

    const setup = (node) => {
        if (!node || node.__a3PaletteSetup || typeof node.addDOMWidget !== "function") return;
        const widget = widgetOf(node, config.widget);
        if (!widget) return;
        node.__a3PaletteSetup = true;
        ensureTheme();

        let built;
        try {
            built = config.build(node);
        } catch (error) {
            console.error("[AICG3D] 面板初始化失败", error);
            node.__a3PaletteSetup = false;
            return;
        }

        hideWidget(widget);
        refreshVueWidgets(node);
        const domWidget = node.addDOMWidget(config.dom, config.dom, built.panel, {
            serialize: false,
            getMinHeight: () => Math.max(1, Number(node.__a3PaletteHeight) || 132),
            afterResize: () => resize(node),
        });
        if (!domWidget) return;
        domWidget.serialize = false;
        node.__a3PaletteWidget = domWidget;
        node.__a3PaletteSync = built.sync;
        built.sync();
        setTimeout(() => resize(node), 0);
    };

    const resize = (node) => {
        const widget = node.__a3PaletteWidget;
        const panel = node.__a3PaletteWidget?.element;
        if (!widget || !panel) return;
        panel.style.height = "auto";
        node.__a3PaletteHeight = Math.max(1, Math.ceil(panel.scrollHeight || 0)) + 8;
        widget.options ||= {};
        widget.options.getMinHeight = () => node.__a3PaletteHeight;
        refreshLayout(node);
    };

    const chain = (name) => {
        const original = nodeType.prototype[name];
        nodeType.prototype[name] = function (...args) {
            const result = original?.apply(this, args);
            try {
                setup(this);
                this.__a3PaletteSync?.();
                setTimeout(() => resize(this), 0);
            } catch (error) {
                console.error("[AICG3D]", error);
            }
            return result;
        };
    };
    chain("onNodeCreated");
    chain("onAdded");
    chain("onConfigure");
}

/* ==========================================================================
    多段提示词 · 一次粘贴，按段落链顺序分发
   --------------------------------------------------------------------------
    段落链本身就是生成顺序：第 1 段的 previous_segment 是空的，顺着 segment
    输出往下就是第 2 段、第 3 段…… 这里把整块模板文本切成 N 段，按这条链的
    顺序分别写进每个段落的提示词，省掉逐段复制粘贴。
   ========================================================================== */
const SEGMENT_NODE_TYPES = new Set(["MiniMaxH3EasySequenceSegment", "AICG3D_H3SequenceSegment"]);
const SEGMENT_PREVIOUS_INPUT = "previous_segment";
const SEGMENT_PROMPT_WIDGET = "prompt";
const SEGMENT_SECONDS_WIDGET = "seconds";
const SEGMENT_PROMPT_DOC_PROP = "minimax_h3_prompt_reference_doc";
const SEGMENT_SECONDS_RANGE = [0.2, 30];
const PASTE_PREVIEW_LIMIT = 40;
const FENCE_SOURCE = "```[^\\n]*\\n([\\s\\S]*?)```";
const SECONDS_RANGE_SOURCE = "(\\d+(?:\\.\\d+)?)\\s*(?:[-\u2013\u2014~\uFF5E]|\u81F3|\u5230)\\s*(\\d+(?:\\.\\d+)?)\\s*\u79D2";

/* 段头：既认工作流里的 【第1段｜秒数=5】，也认模板里的 **第 1 段（5 秒）** / ### 第 1 段。 */
const CN_ORDINAL = "[0-9\uFF10-\uFF19\u4E00\u4E8C\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341\u767E\u96F6\u4E24]{1,4}";
const SEGMENT_HEAD_BRACKET = new RegExp(`^\u3010\\s*\u7B2C\\s*${CN_ORDINAL}\\s*\u6BB5[^\u3011]*\u3011$`);
const SEGMENT_HEAD_PLAIN = new RegExp(
    `^(?:#{1,6}\\s+|>\\s+|[-*+]\\s+)?(?:\\*\\*|__)?\\s*\u7B2C\\s*${CN_ORDINAL}\\s*\u6BB5\\s*`
    + `(?:[\uFF08(][^\uFF09)]*[\uFF09)])?\\s*(?:\\*\\*|__)?\\s*[:\uFF1A]?$`,
);
const SECONDS_ASSIGN = /\u79D2\u6570\s*[=\uFF1D:\uFF1A]?\s*(\d+(?:\.\d+)?)/;
const SECONDS_WORD = /(\d+(?:\.\d+)?)\s*\u79D2/;

function isSequenceSegment(node) {
    const name = String(node?.type || node?.comfyClass || "");
    if (SEGMENT_NODE_TYPES.has(name)) return true;
    return !!widgetOf(node, SEGMENT_PROMPT_WIDGET)
        && (node?.inputs || []).some((input) => input?.name === SEGMENT_PREVIOUS_INPUT);
}

function graphNodes() {
    const graph = app?.graph;
    return (graph?._nodes || graph?.nodes || []).filter(Boolean);
}

function segmentHeadMarker(line) {
    const text = String(line ?? "").trim();
    if (!text) return null;
    if (SEGMENT_HEAD_BRACKET.test(text)) return { label: text, keep: true };
    if (SEGMENT_HEAD_PLAIN.test(text)) return { label: text, keep: false };
    return null;
}

function fenceContents(text) {
    const pattern = new RegExp(FENCE_SOURCE, "g");
    const list = [];
    let match;
    while ((match = pattern.exec(text)) !== null) list.push(match[1].trim());
    return list;
}

function unwrapFence(text) {
    const first = new RegExp(FENCE_SOURCE).exec(text);
    if (!first || fenceContents(text).length !== 1) return text;
    const outside = `${text.slice(0, first.index)}${text.slice(first.index + first[0].length)}`.trim();
    return outside ? text : first[1].trim();
}

/** 段头行里的秒数：秒数=8 / （8 秒）。 */
function secondsFromHeaderLine(line) {
    const text = String(line ?? "").trim();
    if (!text || !segmentHeadMarker(text)) return null;
    const match = text.match(SECONDS_ASSIGN) || text.match(SECONDS_WORD);
    if (!match) return null;
    const value = Number.parseFloat(match[1]);
    return Number.isFinite(value) && value > 0 ? value : null;
}

/** 正文时间轴里的秒数：0-2秒 / 2-4秒 / 4-5秒 -> 5。 */
function secondsFromTimeline(text) {
    let best = null;
    const range = new RegExp(SECONDS_RANGE_SOURCE, "g");
    let match;
    while ((match = range.exec(text)) !== null) {
        const value = Number.parseFloat(match[2]);
        if (Number.isFinite(value) && (best == null || value > best)) best = value;
    }
    if (best != null) return best;
    const single = new RegExp(SECONDS_WORD.source, "g");
    while ((match = single.exec(text)) !== null) {
        const value = Number.parseFloat(match[1]);
        if (Number.isFinite(value) && (best == null || value > best)) best = value;
    }
    return best;
}

function segmentSeconds(label, body) {
    const firstLine = String(body || "").split("\n")[0] || "";
    const raw = secondsFromHeaderLine(label) ?? secondsFromHeaderLine(firstLine) ?? secondsFromTimeline(body);
    if (raw == null) return null;
    const clamped = Math.min(SEGMENT_SECONDS_RANGE[1], Math.max(SEGMENT_SECONDS_RANGE[0], raw));
    return Math.round(clamped * 10) / 10;
}

function finalizeSegment(block) {
    const body = unwrapFence(String(block?.text ?? ""));
    const lines = body.split("\n");
    while (lines.length && !lines[0].trim()) lines.shift();
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
    // 复制时截断留下的孤立围栏：不是提示词内容，直接去掉。
    while (lines.length && isFenceLine(lines[0])) lines.shift();
    while (lines.length && isFenceLine(lines[lines.length - 1])) lines.pop();
    // 粘进来的东西后面还跟着说明文档的小节标题（## 七、…）：那之后不属于这一段。
    const heading = lines.findIndex((line) => /^#{1,6}\s/.test(line));
    if (heading > 0) lines.length = heading;
    const text = lines.join("\n");
    if (!text.trim()) return null;
    return { text, seconds: segmentSeconds(block?.label, text) };
}

function isFenceLine(line) {
    return /^\s*(?:`{3,}|~{3,})/.test(String(line ?? ""));
}

function headeredBlocks(text) {
    const lines = text.split("\n");
    const marks = [];
    // 围栏里的「第 N 段」是提示词正文（工作流里每段第一行就是它），不是段落边界。
    let fenced = false;
    lines.forEach((line, index) => {
        if (isFenceLine(line)) {
            fenced = !fenced;
            return;
        }
        if (fenced) return;
        const marker = segmentHeadMarker(line);
        if (marker) marks.push({ ...marker, index });
    });
    if (marks.length < 2) return [{ text, label: "" }];
    return marks.map((marker, order) => {
        const from = marker.index + (marker.keep ? 0 : 1);
        const to = order + 1 < marks.length ? marks[order + 1].index : lines.length;
        return { text: lines.slice(from, to).join("\n"), label: marker.label };
    });
}

/** 切分容错顺序：段头 → ``` 围栏 → 空行分块；都不成立就整块当一段。 */
function splitPromptSegments(raw) {
    const text = String(raw ?? "").replace(/\r\n?/g, "\n").trim();
    if (!text) return [];
    let blocks = headeredBlocks(text);
    if (blocks.length < 2) {
        const fenced = fenceContents(text);
        if (fenced.length >= 2) blocks = fenced.map((item) => ({ text: item, label: "" }));
    }
    if (blocks.length === 1) {
        const fenced = fenceContents(blocks[0].text);
        if (fenced.length >= 2) blocks = fenced.map((item) => ({ text: item, label: "" }));
    }
    if (blocks.length === 1) {
        const parts = blocks[0].text.split(/\n{2,}/).map((item) => item.trim()).filter(Boolean);
        const timed = parts.filter((item) => SECONDS_WORD.test(item) || item.includes("环境声")).length;
        if (parts.length >= 2 && timed >= Math.ceil(parts.length / 2)) {
            blocks = parts.map((item) => ({ text: item, label: "" }));
        }
    }
    return blocks.map(finalizeSegment).filter(Boolean);
}

function segmentPreviousLink(node) {
    const input = (node?.inputs || []).find((item) => item?.name === SEGMENT_PREVIOUS_INPUT);
    return input?.link ?? null;
}

function nextSegmentNode(node, pool) {
    const links = new Set(((node?.outputs || [])[0]?.links || []).map(String));
    if (!links.size) return null;
    return pool.find((candidate) => candidate !== node
        && (candidate.inputs || []).some((input) => input?.name === SEGMENT_PREVIOUS_INPUT
            && input.link != null && links.has(String(input.link)))) || null;
}

function canvasOrder(first, second) {
    const firstY = first?.pos?.[1] ?? 0;
    const secondY = second?.pos?.[1] ?? 0;
    if (firstY !== secondY) return firstY - secondY;
    return (first?.pos?.[0] ?? 0) - (second?.pos?.[0] ?? 0);
}

/** 从 previous_segment 为空的那一段开始，顺着 segment 输出走成生成顺序。 */
function segmentChains() {
    const pool = graphNodes().filter(isSequenceSegment);
    const chains = [];
    const seen = new Set();
    for (const head of pool.filter((node) => segmentPreviousLink(node) == null).sort(canvasOrder)) {
        const chain = [];
        let current = head;
        while (current && !seen.has(current)) {
            seen.add(current);
            chain.push(current);
            current = nextSegmentNode(current, pool);
        }
        if (chain.length) chains.push(chain);
    }
    for (const node of pool) if (!seen.has(node)) chains.push([node]);
    return chains;
}

/** 图里有多条段落链时：先看画布选中，其次取离入口框最近的那条。 */
function pickSegmentChain(anchor) {
    const chains = segmentChains();
    if (chains.length <= 1) return chains[0] || [];
    const selected = app?.canvas?.selected_nodes || {};
    const picked = chains.find((chain) => chain.some((node) => selected[node.id] || selected[String(node.id)]));
    if (picked) return picked;
    const anchorPos = anchor?.pos || anchor?._pos;
    if (!anchorPos || !Number.isFinite(anchorPos[0])) return chains[0];
    let best = chains[0];
    let bestDistance = Infinity;
    for (const chain of chains) {
        const head = chain[0];
        const distance = Math.hypot((head.pos?.[0] ?? 0) - anchorPos[0], (head.pos?.[1] ?? 0) - anchorPos[1]);
        if (distance < bestDistance) {
            bestDistance = distance;
            best = chain;
        }
    }
    return best;
}

function segmentLabel(node) {
    const title = String(node?.title || node?.type || "");
    return `#${node?.id ?? "?"}${title ? ` 「${title}」` : ""}`;
}

/** 写整段提示词：优先走 H3 前端桥，结构化编辑器与属性一起刷新。 */
function applySegmentPrompt(node, text) {
    const bridge = globalThis.AICG3D_H3;
    if (typeof bridge?.setPromptText === "function") {
        return bridge.setPromptText(node, text, { notifyGraphChange: false }) !== false;
    }
    const widget = widgetOf(node, SEGMENT_PROMPT_WIDGET);
    if (!widget) return false;
    widget.value = text;
    if (widget._state) widget._state.value = text;
    node.properties ||= {};
    node.properties[SEGMENT_PROMPT_DOC_PROP] = { version: 1, text, parts: [{ type: "text", text }] };
    return true;
}

function distributeSegments(chain, segments, syncSeconds) {
    const count = Math.min(chain.length, segments.length);
    let secondsWritten = 0;
    for (let index = 0; index < count; index += 1) {
        const node = chain[index];
        const segment = segments[index];
        applySegmentPrompt(node, segment.text);
        if (syncSeconds && segment.seconds != null
            && setWidgetValue(node, SEGMENT_SECONDS_WIDGET, segment.seconds)) {
            secondsWritten += 1;
        }
        node.setDirtyCanvas?.(true, true);
    }
    app.graph?.setDirtyCanvas?.(true, true);
    app.graph?.change?.();
    return { count, secondsWritten };
}

/* ------------------------------ 粘贴分发面板 ------------------------------ */
let pastePanelNodes = null;

function closeSegmentPastePanel() {
    if (!pastePanelNodes) return;
    pastePanelNodes.scrim.remove();
    pastePanelNodes.panel.remove();
    pastePanelNodes = null;
    document.removeEventListener("keydown", pastePanelKeydown, true);
}

function pastePanelKeydown(event) {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    closeSegmentPastePanel();
}

function openSegmentPastePanel(anchorNode) {
    closeSegmentPastePanel();
    ensureTheme();

    const chain = pickSegmentChain(anchorNode);
    const scrim = el("div", "a3-scrim");
    const panel = el("div", "a3-palette");
    panel.style.width = "min(680px, calc(100vw - 32px))";
    panel.style.left = "50%";
    panel.style.top = "6vh";
    panel.style.transform = "translateX(-50%)";
    panel.addEventListener("pointerdown", (event) => event.stopPropagation());

    const head = el("div", "a3-palette-head");
    head.append(el("span", "a3-logo", "AI"), el("span", "a3-title", "粘贴多段提示词"));
    head.append(el("span", "a3-sub", "按段落链顺序分发"));
    const badge = el("span", "a3-badge", chain.length ? `目标 ${chain.length} 段` : "无段落链");
    head.append(el("span", "a3-spacer"), badge);
    const close = el("button", "a3-btn a3-btn--ghost a3-btn--icon", "\u00D7");
    close.type = "button";
    close.title = "关闭";
    close.addEventListener("click", closeSegmentPastePanel);
    head.append(close);

    const body = el("div", "a3-paste-body");
    const hint = el("div", "a3-hint");
    const area = el("textarea", "a3-paste-area");
    area.spellcheck = false;
    area.placeholder = [
        "把模板生成的多段提示词整块粘到这里（5 段、10 段都行）：",
        "",
        "**第 1 段（5 秒）**",
        "【第1段｜秒数=5】",
        "竖屏9:16……",
        "0-2秒：……",
        "环境声：……",
        "",
        "**第 2 段（5 秒）**",
        "……",
        "",
        "段头（第 N 段 / 【第N段｜秒数=5】）、``` 围栏、空行 分隔都能识别。",
    ].join("\n");
    const list = el("div", "a3-paste-list");
    body.append(hint, area, list);

    const foot = el("div", "a3-palette-foot");
    const toggleWrap = el("div", "a3-paste-toggle");
    const toggle = el("button", "a3-switch is-on", "");
    toggle.type = "button";
    toggle.title = "按段头 / 时间轴自动同步 seconds 控件";
    toggle.addEventListener("click", () => toggle.classList.toggle("is-on"));
    toggleWrap.append(toggle, el("span", "a3-hint", "同步秒数"));
    const clear = el("button", "a3-btn", "清空");
    clear.type = "button";
    const apply = el("button", "a3-btn a3-btn--accent", "分发");
    apply.type = "button";
    foot.append(toggleWrap, el("span", "a3-spacer"), clear, apply);

    panel.append(head, body, foot);

    function currentSegments() {
        return splitPromptSegments(area.value);
    }

    function refresh() {
        const segments = currentSegments();
        const usable = Math.min(segments.length, chain.length);
        badge.textContent = segments.length
            ? `识别 ${segments.length} 段`
            : (chain.length ? `目标 ${chain.length} 段` : "无段落链");
        hint.textContent = chain.length
            ? `目标：第 1 段 ${segmentLabel(chain[0])} → 共 ${chain.length} 段，按生成顺序依次写入。`
            : "画布上没找到「视频段落」节点，先把段落链摆好。";
        list.textContent = "";
        for (let index = 0; index < segments.length && index < PASTE_PREVIEW_LIMIT; index += 1) {
            const segment = segments[index];
            const node = chain[index];
            const row = el("div", `a3-paste-row${node ? "" : " is-over"}`);
            row.append(el("span", "a3-paste-index", String(index + 1).padStart(2, "0")));
            row.append(el("span", "a3-tag", segment.seconds != null ? `${segment.seconds} 秒` : "—"));
            row.append(el("span", "a3-paste-target", segment.text.replace(/\s+/g, " ").slice(0, 42)));
            row.append(el("span", "a3-dim", node ? `→ ${segmentLabel(node)}` : "超出链长"));
            list.append(row);
        }
        if (segments.length > PASTE_PREVIEW_LIMIT) {
            list.append(el("div", "a3-dim", `……还有 ${segments.length - PASTE_PREVIEW_LIMIT} 段`));
        }
        apply.disabled = !segments.length || !chain.length;
        apply.textContent = usable ? `分发到 ${usable} 段` : "分发";
    }

    function run() {
        const segments = currentSegments();
        if (!segments.length) {
            toast("没有识别到提示词段落", "warn");
            return;
        }
        if (!chain.length) {
            toast("画布上没有「视频段落」节点", "warn");
            return;
        }
        const result = distributeSegments(chain, segments, toggle.classList.contains("is-on"));
        const parts = [`已分发 ${result.count} 段到段落链`];
        if (result.secondsWritten) parts.push(`同步了 ${result.secondsWritten} 段秒数`);
        const over = segments.length - result.count;
        if (over > 0) parts.push(`多出的 ${over} 段没地方放`);
        const rest = chain.length - result.count;
        if (rest > 0) parts.push(`链上还有 ${rest} 段未改动`);
        toast(parts.join("，"), over > 0 || rest > 0 ? "warn" : "ok");
        closeSegmentPastePanel();
    }

    area.addEventListener("input", refresh);
    area.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            run();
        }
    });
    clear.addEventListener("click", () => {
        area.value = "";
        refresh();
        area.focus();
    });
    apply.addEventListener("click", run);
    scrim.addEventListener("pointerdown", closeSegmentPastePanel);
    document.addEventListener("keydown", pastePanelKeydown, true);

    document.body.append(scrim, panel);
    pastePanelNodes = { scrim, panel };
    refresh();
    setTimeout(() => area.focus(), 0);
}

/** Note / MarkdownNote 上的入口按钮：备注节点不走 beforeRegisterNodeDef，只能这样挂。 */
function installNotePasteButton(node) {
    if (!node || !NOTE_NODE_TYPES.has(String(node.type || ""))) return;
    if (node.__a3PasteButton || typeof node.addWidget !== "function") return;
    node.__a3PasteButton = true;
    try {
        const widget = node.addWidget("button", "📋 粘贴多段提示词 · 自动分发", "",
            () => openSegmentPastePanel(node), { serialize: false });
        if (widget) widget.serialize = false;
        refreshVueWidgets(node);
        node.setDirtyCanvas?.(true, true);
    } catch (error) {
        node.__a3PasteButton = false;
        console.error("[AICG3D]", error);
    }
}

function sweepNotePasteButtons() {
    for (const node of graphNodes()) installNotePasteButton(node);
}

app.registerExtension({
    name: "AICG3D.Nodes",
    setup() {
        app?.ui?.settings?.addSetting?.({
            id: NOTE_COLOR_SETTING,
            name: "备注节点使用系统默认配色（不再用黄色）",
            tooltip: "关闭后备注节点恢复 ComfyUI 自带的黄色。切换时会同步当前工作流里的备注节点。",
            type: "boolean",
            defaultValue: true,
            onChange: () => repaintNotes(),
        });
        app?.ui?.settings?.addSetting?.({
            id: TTN_FIX_SETTING,
            name: "新节点保持系统默认配色（自动清理 ttN 全局默认色）",
            tooltip: "tinyterraNodes(ttN) 的「🌏 Default Node BG Color」会给所有新建节点上色，这是新节点颜色不是系统默认的原因。保持开启会自动清掉它，并还原已被染色的节点；关闭后完全交给 ttN。",
            type: "boolean",
            defaultValue: true,
            onChange: () => {
                clearTtnDefaultColor();
                sweepTtnTints();
            },
        });
        installNoteColor();
        sweepNotePasteButtons();
        setTimeout(() => { installNoteColor(); sweepNotePasteButtons(); }, 1500);
        setTimeout(() => { installNoteColor(); sweepNotePasteButtons(); }, 6000);

        const cleared = clearTtnDefaultColor();
        const stripped = sweepTtnTints();
        if (cleared || stripped) {
            const extra = stripped ? `，并还原了 ${stripped} 个已染色节点` : "";
            toast(`已恢复系统默认节点配色（清理了 ttN 的全局默认色${extra}）`, "ok");
        }
        setTimeout(() => sweepTtnTints(), 1500);
    },
    nodeCreated(node) {
        applyNodeColorPolicy(node);
        installNotePasteButton(node);
    },
    loadedGraphNode(node) {
        applyNodeColorPolicy(node);
        installNotePasteButton(node);
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        paintNodeType(nodeType, nodeData);
        installPaletteNode(nodeType, nodeData);
    },
});

export { selectionText, toast };
