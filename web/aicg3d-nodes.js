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
    markWidgetHidden, autoHideWidgets, refreshVueWidgets,
} from "./aicg3d-core.js";

const SKILL_NODE = "AICG3D_SkillLoader";
const PRESET_NODE = "AICG3D_PromptPreset";

/* ------------------------------ 统一配色 ------------------------------ */
const GROUP_STYLE = [
    { match: /^MiniMaxH3Easy/, color: "#34517c", bgcolor: "#151b24" },
    { match: /^AICG3D_/, color: "#26594f", bgcolor: "#131d1c" },
];

function paintNodeType(nodeType, nodeData) {
    const name = String(nodeData?.name || "");
    const style = GROUP_STYLE.find((entry) => entry.match.test(name));
    if (!style || nodeType.__a3Painted) return;
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
        setTimeout(installNoteColor, 1500);
        setTimeout(installNoteColor, 6000);

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
    },
    loadedGraphNode(node) {
        applyNodeColorPolicy(node);
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        paintNodeType(nodeType, nodeData);
        installPaletteNode(nodeType, nodeData);
    },
});

export { selectionText, toast };
