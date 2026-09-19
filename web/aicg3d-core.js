/* ==========================================================================
   Copyright (C) 2026 AICG3D
   SPDX-License-Identifier: GPL-3.0-or-later
   本模块为新增代码（AICG3D 前端公共层）
   ========================================================================== */

/* ==========================================================================
   AICG3D 前端公共层
   - 统一主题注入
   - /aicg3d/api/* 数据访问（技能库 / LoRA / 素材）
   - 通用控件：可搜索下拉、提示条、悬浮面板
   - 素材库（点选后 @ 到提示词）与技能库（点选后写入提示词）
   ========================================================================== */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const THEME_URL = new URL("./aicg3d-theme.css", import.meta.url).href;

/* --------------------- 节点归属 --------------------- */
/* 上游 ComfyUI-MiniMaxH3-Easy 注册的是同一批 MiniMaxH3Easy* 节点。
   两边同时启用时本插件会改用 AICG3D_H3* 前缀（见 aicg3d/compat.py），
   但前端原来只按类名比较，会把上游那一整套也当成本插件的节点：名字改成
   「MiniMax H3 Aicg」、分类改成 AICG3D，节点菜单里就出现两套一样的节点。
   下面统一判断某个节点定义 / 节点实例是不是本插件注册的那一份。 */
const NODE_ID_PREFIX = "AICG3D_H3";
const UPSTREAM_NODE_PREFIX = "MiniMaxH3Easy";

/* 本插件 web 目录名 = custom_nodes 下的插件目录名。后端会把注册该节点的包名
   写进 nodeData.python_module（custom_nodes.<目录名>），用它就能分辨归属。 */
const OWN_PACK_NAME = (() => {
    try {
        const segments = String(new URL(import.meta.url).pathname).split("/").filter(Boolean);
        const index = segments.lastIndexOf("extensions");
        return index >= 0 ? decodeURIComponent(segments[index + 1] || "") : "";
    } catch (error) {
        return "";
    }
})();

/* 见到带前缀的节点就说明本插件走的是 AICG3D_H3*；没见到不急着定性。 */
let ownNodesArePrefixed = false;

function ownPrefixedNodesRegistered() {
    const registered = globalThis.LiteGraph?.registered_node_types || {};
    return Object.keys(registered).some((id) => id.startsWith(NODE_ID_PREFIX));
}

function packNameOfModule(moduleName) {
    const parts = String(moduleName ?? "").split(".");
    return parts.length >= 2 && parts[0] === "custom_nodes" ? parts[1] : "";
}

/* 上游那份的节点 ID：本插件已经改用带前缀的 ID 时，MiniMaxH3Easy* 就归对方。 */
export function isUpstreamH3NodeId(nodeId) {
    const text = String(nodeId ?? "");
    if (!text.startsWith(UPSTREAM_NODE_PREFIX)) return false;
    const prefixed = NODE_ID_PREFIX + text.slice(UPSTREAM_NODE_PREFIX.length);
    return Boolean(globalThis.LiteGraph?.registered_node_types?.[prefixed]);
}

/* nodeData 是不是本插件注册的那份节点定义。 */
export function isOwnH3NodeData(nodeData) {
    const name = String(nodeData?.name ?? "");
    if (!name.startsWith(NODE_ID_PREFIX) && !name.startsWith(UPSTREAM_NODE_PREFIX)) return false;
    if (name.startsWith(NODE_ID_PREFIX)) return true;
    const packName = packNameOfModule(nodeData?.python_module);
    if (packName && OWN_PACK_NAME) return packName === OWN_PACK_NAME;
    // 拿不到包名时退回到"注册表里有没有带前缀的节点"：只要见到过就说明
    // MiniMaxH3Easy* 归上游。没见到就先按老行为处理，且不缓存这个中间结论。
    if (!ownNodesArePrefixed && ownPrefixedNodesRegistered()) ownNodesArePrefixed = true;
    return !ownNodesArePrefixed;
}

/* ------------------------------ 主题 ------------------------------ */
export function ensureTheme() {
    if (document.getElementById("aicg3d-theme")) return;
    const link = document.createElement("link");
    link.id = "aicg3d-theme";
    link.rel = "stylesheet";
    link.href = THEME_URL;
    document.head.append(link);
}

/* ------------------------------ 数据 ------------------------------ */
const cache = new Map();

async function fetchJson(path) {
    const response = await api.fetchApi(path);
    if (!response.ok) throw new Error(`${path} -> HTTP ${response.status}`);
    return response.json();
}

function cached(key, loader) {
    if (!cache.has(key)) {
        cache.set(key, loader().catch((error) => {
            cache.delete(key);
            throw error;
        }));
    }
    return cache.get(key);
}

async function presetPayload() {
    return cached("presets", () => fetchJson("/aicg3d/api/presets"));
}

export const library = {
    skills: () => cached("skills", async () => (await fetchJson("/aicg3d/api/skills")).skills || []),
    presets: async () => (await presetPayload()).presets || [],
    presetCategories: async () => (await presetPayload()).categories || [],
    loras: () => cached("loras", async () => (await fetchJson("/aicg3d/api/loras")).loras || []),
    media: (kind = "") => cached(`media:${kind}`, async () => (await fetchJson(`/aicg3d/api/media?kind=${kind}`)).files || []),
    detail: (skillId) => fetchJson(`/aicg3d/api/skills/${encodeURIComponent(skillId)}`),
    clear: () => cache.clear(),
};

/* ------------------------------ 小工具 ------------------------------ */
export function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

export function formatSize(bytes) {
    const value = Number(bytes) || 0;
    if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(2)}G`;
    if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)}M`;
    if (value >= 1024) return `${Math.round(value / 1024)}K`;
    return `${value}B`;
}

export function widgetOf(node, name) {
    return node?.widgets?.find((widget) => widget?.name === name);
}

export function setWidgetValue(node, name, value) {
    const widget = widgetOf(node, name);
    if (!widget) return false;
    widget.value = value;
    widget.callback?.(value, app.canvas, node, [0, 0], null);
    node?.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
    return true;
}

/* 把内联样式挂到 ComfyUI 原生节点上，保证自定义面板与主题一致。 */
export function selectionText(value) {
    const text = String(value ?? "").trim();
    return text && !/^(none|无)$/i.test(text) ? text : "";
}

/* --------------------------- 原生控件隐藏（Nodes 2.0 兼容） ---------------------------
   Canvas 渲染器（LiteGraph）看 widget.hidden / widget.type，
   Vue 渲染器（Nodes 2.0）只看 widget.options.hidden 与 canvasOnly，
   而且它读的是节点创建时克隆的一份 options 快照。于是：每个被隐藏的
   原生控件都会留下一条 22px 的空行，节点底部就是一大块可以点出下拉菜单的空白。
   两步走：① 在 addWidget 阶段就把 options 写好（快照生成之前）；
             ② 已经建好的节点用 refreshVueWidgets() 触发一次重新映射。 */
export function markWidgetHidden(widget) {
    if (!widget) return widget;
    if (!widget.__a3Native) {
        widget.__a3Native = {
            type: widget.type,
            hidden: widget.hidden,
            computeSize: widget.computeSize,
            optionsHidden: widget.options?.hidden,
            optionsCanvasOnly: widget.options?.canvasOnly,
        };
    }
    widget.options = widget.options || {};
    widget.options.hidden = true;
    widget.options.canvasOnly = true;
    if (widget._state?.options) {
        widget._state.options.hidden = true;
        widget._state.options.canvasOnly = true;
    }
    widget.hidden = true;
    widget.type = "hidden";
    widget.computeSize = () => [0, -4];
    return widget;
}

/** markWidgetHidden 的逆操作：把原生控件按原样放回来。
    自定义面板建不起来时（例如与同名节点包撞车）必须走这一步，
    否则节点只剩标题，用户看到的就是一个空白节点。 */
export function markWidgetVisible(widget) {
    if (!widget) return widget;
    const native = widget.__a3Native;
    widget.options = widget.options || {};
    widget.options.hidden = native ? !!native.optionsHidden : false;
    widget.options.canvasOnly = native ? !!native.optionsCanvasOnly : false;
    if (widget._state?.options) {
        widget._state.options.hidden = widget.options.hidden;
        widget._state.options.canvasOnly = widget.options.canvasOnly;
    }
    widget.hidden = native ? !!native.hidden : false;
    widget.type = native ? (native.type ?? "combo") : widget.type;
    if (native?.computeSize) widget.computeSize = native.computeSize;
    return widget;
}

/** 在 addWidget 阶段就把名单里的原生控件标成隐藏（Nodes 2.0 下必须这么做）。
    apply 可以换成自己的隐藏函数，默认用 markWidgetHidden。 */
export function autoHideWidgets(nodeType, names, apply = markWidgetHidden) {
    const proto = nodeType?.prototype;
    if (!proto || proto.__a3AutoHide) return false;
    const list = names instanceof Set ? names : new Set(names || []);
    if (!list.size || typeof proto.addWidget !== "function") return false;
    const original = proto.addWidget;
    proto.__a3AutoHide = true;
    proto.addWidget = function (...args) {
        const widget = original.apply(this, args);
        try {
            const name = widget?.name ?? (typeof args[1] === "string" ? args[1] : "");
            if (name && list.has(name)) apply(widget);
        } catch (error) {
            console.error("[AICG3D]", error);
        }
        return widget;
    };
    return true;
}

/** 让 Vue 渲染器重新读一遍 node.widgets（后加的 hidden 才会生效）。 */
export function refreshVueWidgets(node) {
    if (!globalThis.LiteGraph?.vueNodesMode) return false;
    const list = node?.widgets;
    if (!Array.isArray(list) || list.length === 0) return false;
    try {
        const last = list[list.length - 1];
        list.pop();
        list.push(last);
        return true;
    } catch (error) {
        console.error("[AICG3D]", error);
        return false;
    }
}

/* ------------------------------ 提示条 ------------------------------ */
let toastTimer = null;

export function toast(message, kind = "") {
    let element = document.getElementById("aicg3d-toast");
    if (!element) {
        element = el("div", "a3-toast");
        element.id = "aicg3d-toast";
        element.append(el("span", "a3-toast-dot"), el("span", "a3-toast-text"));
        document.body.append(element);
    }
    element.className = `a3-toast is-on${kind ? ` is-${kind}` : ""}`;
    element.querySelector(".a3-toast-text").textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove("is-on"), 2600);
}

/* ------------------------------ 可搜索下拉 ------------------------------ */
let openMenu = null;

export function closeMenus() {
    if (!openMenu) return;
    openMenu.element.remove();
    openMenu.trigger?.classList.remove("is-open");
    openMenu = null;
}

document.addEventListener("pointerdown", (event) => {
    if (!openMenu) return;
    if (openMenu.element.contains(event.target) || openMenu.trigger?.contains(event.target)) return;
    closeMenus();
}, true);

window.addEventListener("blur", closeMenus);

/**
 * 可搜索下拉。options: [{value, label, meta, preview, keywords}]
 * 返回 { element, setValue, getValue, setOptions }。
 */
export function createSelect({ options = [], value = "", placeholder = "未选择", onChange = null, recentKey = null } = {}) {
    const trigger = el("button", "a3-select");
    trigger.type = "button";
    const text = el("span", "a3-select-text");
    const caret = el("span", "a3-caret", "\u25be");
    trigger.append(text, caret);

    let items = [...options];
    let current = value;

    const RECENT_LIMIT = 6;
    let recents = [];
    if (recentKey) {
        try {
            const raw = JSON.parse(localStorage.getItem(`aicg3d.recent.${recentKey}`) || "[]");
            if (Array.isArray(raw)) recents = raw.map(String);
        } catch { recents = []; }
    }

    const remember = (picked) => {
        if (!recentKey || !picked) return;
        recents = [picked, ...recents.filter((item) => item !== picked)].slice(0, RECENT_LIMIT);
        try { localStorage.setItem(`aicg3d.recent.${recentKey}`, JSON.stringify(recents)); } catch { /* 忽略 */ }
    };

    const renderTrigger = () => {
        const found = items.find((item) => String(item.value) === String(current));
        const label = found?.label || current || "";
        text.textContent = label || placeholder;
        trigger.classList.toggle("is-empty", !label);
        trigger.title = found?.meta ? `${label} · ${found.meta}` : label;
    };

    const pick = (next) => {
        current = next;
        renderTrigger();
        remember(next);
        onChange?.(next);
    };

    trigger.addEventListener("pointerdown", (event) => event.stopPropagation());
    trigger.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (openMenu?.trigger === trigger) { closeMenus(); return; }
        closeMenus();
        openMenu = { trigger, element: buildMenu(), onKey: null };
        trigger.classList.add("is-open");
        position();
    });

    let menu = null;
    let listBox = null;

    function ordered() {
        if (!recents.length) return items;
        const pinned = recents
            .map((recent) => items.find((item) => String(item.value) === recent))
            .filter(Boolean);
        return [...pinned, ...items.filter((item) => !pinned.includes(item))];
    }

    function buildMenu() {
        menu = el("div", "a3-menu");
        const search = el("input", "a3-search a3-menu-search");
        search.placeholder = "搜索…";
        search.spellcheck = false;
        listBox = el("div", "a3-menu-list");
        menu.append(search, listBox);
        document.body.append(menu);
        search.addEventListener("input", () => renderList(search.value));
        search.addEventListener("pointerdown", (event) => event.stopPropagation());
        menu.addEventListener("pointerdown", (event) => event.stopPropagation());
        document.body.append(menu);
        renderList("");
        setTimeout(() => search.focus(), 0);
        return menu;
    }

    function renderList(query) {
        if (!listBox) return;
        const needle = String(query || "").trim().toLowerCase();
        listBox.textContent = "";
        const source = ordered();
        const filtered = needle
            ? source.filter((item) => `${item.label} ${item.value} ${item.keywords || ""}`.toLowerCase().includes(needle))
            : source;
        const shown = filtered.slice(0, 300);
        if (!shown.length) {
            listBox.append(el("div", "a3-empty", "没有匹配项"));
            return;
        }
        for (const item of shown) {
            const row = el("div", "a3-option");
            if (String(item.value) === String(current)) row.classList.add("is-active");
            if (item.preview) {
                const img = el("img", "a3-option-img");
                img.src = item.preview;
                img.alt = "";
                img.loading = "lazy";
                row.append(img);
            }
            const label = el("span", "", item.label || String(item.value));
            label.title = item.title || item.label || "";
            row.append(label);
            if (item.meta) row.append(el("span", "a3-option-meta", item.meta));
            row.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                pick(String(item.value));
                closeMenus();
            });
            listBox.append(row);
        }
    }

    /* 列表宽度跟着下拉框一起变：节点被拉宽之后菜单也要跟着变宽，否则 LoRA 那种
       带目录的长文件名会被省略号截掉。下限 220px，上限留出屏幕边距。 */
    const MENU_MIN_WIDTH = 220;
    const MENU_MAX_WIDTH = 900;

    function position() {
        if (!menu) return;
        const rect = trigger.getBoundingClientRect();
        const available = Math.max(MENU_MIN_WIDTH, window.innerWidth - 16);
        const width = Math.round(Math.max(
            MENU_MIN_WIDTH,
            Math.min(rect.width + 40, MENU_MAX_WIDTH, available),
        ));
        menu.style.width = `${width}px`;
        const height = Math.min(320, menu.scrollHeight || 200);
        let left = rect.left;
        if (left + width > window.innerWidth - 8) left = window.innerWidth - width - 8;
        let top = rect.bottom + 4;
        if (top + height > window.innerHeight - 8) top = Math.max(8, rect.top - height - 4);
        menu.style.left = `${Math.max(8, left)}px`;
        menu.style.top = `${top}px`;
    }

    renderTrigger();

    return {
        element: trigger,
        getValue: () => current,
        setValue: (next) => { current = String(next ?? ""); renderTrigger(); },
        setOptions: (next) => {
            items = [...next];
            if (!items.some((item) => String(item.value) === String(current)) && items.length) {
                current = String(items[0].value);
            }
            renderTrigger();
        },
    };
}

/* ------------------------------ 悬浮面板 ------------------------------ */
function openPalette({ title, subtitle = "", badge = "AICG3D", tabs = [], footer = null, width = 560, anchor = null, initialTab = "" }) {
    const scrim = el("div", "a3-scrim");
    const panel = el("div", "a3-palette");
    panel.style.width = `${Math.min(width, window.innerWidth - 32)}px`;

    const head = el("div", "a3-palette-head");
    head.append(el("span", "a3-logo", "AI"), el("span", "a3-title", title));
    if (subtitle) head.append(el("span", "a3-sub", subtitle));
    head.append(el("span", "a3-spacer"), el("span", "a3-badge", badge));
    const close = el("button", "a3-btn a3-btn--ghost a3-btn--icon", "\u00d7");
    close.title = "关闭";
    head.append(close);

    const body = el("div", "a3-palette-body");
    const side = el("div", "a3-palette-side");
    const main = el("div", "a3-palette-main");
    const searchWrap = el("div", "a3-search-wrap");
    const search = el("input", "a3-search");
    search.placeholder = "搜索…";
    search.spellcheck = false;
    searchWrap.append(search);
    const toolbarWrap = el("div", "a3-toolbar");
    toolbarWrap.hidden = true;
    const content = el("div", "a3-list");
    main.append(searchWrap, toolbarWrap, content);
    body.append(side, main);
    panel.append(head, body);

    const foot = el("div", "a3-palette-foot");
    if (footer) foot.append(footer);
    panel.append(foot);

    if (anchor) scrim.classList.add("a3-scrim--soft");
    document.body.append(scrim, panel);
    place();

    const state = { tab: initialTab || tabs[0]?.id || "", query: "", selected: null };
    let controller = tabs[0]?.render || (() => {});

    /** 锚点位置：优先用触发按钮，其次接受 {x, y} 坐标。 */
    function anchorBox() {
        if (!anchor) return null;
        if (typeof anchor.getBoundingClientRect === "function") {
            const rect = anchor.getBoundingClientRect();
            if (rect && (rect.width || rect.height)) {
                return { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width };
            }
            return null;
        }
        if (typeof anchor === "object" && Number.isFinite(anchor.x) && Number.isFinite(anchor.y)) {
            return { left: anchor.x, top: anchor.y, bottom: anchor.y, width: 0 };
        }
        return null;
    }

    /** 贴着触发点展开：优先落在按钮正下方，空间不足时翻到上方并压缩面板高度。 */
    function place() {
        if (!panel.isConnected) return;
        const box = anchorBox();
        panel.style.maxHeight = "";
        const boxWidth = panel.offsetWidth || Math.min(width, window.innerWidth - 32);
        const naturalHeight = panel.offsetHeight || Math.min(600, window.innerHeight - 60);
        if (!box) {
            panel.style.left = `${Math.max(8, Math.round((window.innerWidth - boxWidth) / 2))}px`;
            panel.style.top = `${Math.max(8, Math.round((window.innerHeight - naturalHeight) / 2))}px`;
            return;
        }
        const margin = 8;
        const gap = 6;
        const below = box.bottom + gap;
        const above = box.top - gap;
        const roomBelow = window.innerHeight - margin - below;
        const roomAbove = above - margin;
        const preferBelow = naturalHeight <= roomBelow || roomBelow >= roomAbove;
        const height = Math.min(naturalHeight, Math.max(180, preferBelow ? roomBelow : roomAbove));
        const top = preferBelow
            ? Math.min(below, window.innerHeight - margin - height)
            : Math.max(margin, above - height);
        if (height < naturalHeight - 1) panel.style.maxHeight = `${Math.round(height)}px`;
        const left = Math.max(margin, Math.min(box.left + box.width / 2 - boxWidth / 2, window.innerWidth - boxWidth - margin));
        panel.style.left = `${Math.round(left)}px`;
        panel.style.top = `${Math.round(top)}px`;
    }

    window.addEventListener("resize", place);

    const api = {
        content,
        state,
        setTab: (id) => {
            state.tab = id;
            renderTabs();
            refresh();
        },
        refresh,
        close: () => {
            scrim.remove();
            panel.remove();
            document.removeEventListener("keydown", onKey, true);
            window.removeEventListener("resize", place);
        },
    };

    function renderTabs() {
        side.textContent = "";
        for (const tab of tabs) {
            const button = el("button", `a3-tab${tab.id === state.tab ? " is-active" : ""}`);
            button.type = "button";
            button.textContent = tab.label;
            button.addEventListener("click", () => api.setTab(tab.id));
            side.append(button);
        }
    }

    async function refresh() {
        content.textContent = "";
        content.scrollTop = 0;
        const tab = tabs.find((entry) => entry.id === state.tab) || tabs[0];
        controller = tab?.render || (() => {});
        toolbarWrap.textContent = "";
        try {
            const bar = tab?.toolbar ? tab.toolbar({ api, state, search }) : null;
            if (bar) toolbarWrap.append(bar);
            toolbarWrap.hidden = !toolbarWrap.childElementCount;
            await controller({ content, query: state.query, api, search });
        } catch (error) {
            content.append(el("div", "a3-empty", `加载失败：${error?.message || error}`));
        }
        place();
    }

    search.addEventListener("input", () => {
        state.query = search.value;
        refresh();
    });

    function onKey(event) {
        if (event.key === "Escape") { event.stopPropagation(); api.close(); }
    }
    document.addEventListener("keydown", onKey, true);
    close.addEventListener("click", api.close);
    scrim.addEventListener("pointerdown", api.close);

    renderTabs();
    refresh();
    setTimeout(() => search.focus(), 0);
    return api;
}

/* ------------------------------ 素材库 ------------------------------ */
function mediaThumb(item) {
    const kind = item.kind || item.type || "image";
    const thumb = el("div", "a3-thumb");
    const kindLabel = { image: "图片", video: "视频", audio: "音频" }[kind] || "";
    thumb.append(el("span", "a3-thumb-tag", kindLabel));
    if (kind === "audio") {
        const wave = el("span", "a3-wave");
        for (const height of [38, 68, 100, 68, 38]) {
            const bar = el("i");
            bar.style.height = `${height}%`;
            wave.append(bar);
        }
        thumb.append(wave);
        return thumb;
    }
    const url = item.previewUrl || item.url || "";
    if (!url) return thumb;
    const media = document.createElement(kind === "video" ? "video" : "img");
    media.src = url;
    media.alt = "";
    media.loading = "lazy";
    if (kind === "video") {
        media.muted = true;
        media.playsInline = true;
        media.preload = "metadata";
    }
    media.addEventListener("error", () => {
        media.remove();
        thumb.append(el("span", "a3-hint", kindLabel));
    }, { once: true });
    thumb.append(media);
    return thumb;
}

/** 当前节点里、可以立刻插入 @ 引用的素材。 */
function referenceableMedia(target, query) {
    const bridge = globalThis.AICG3D_H3;
    const items = bridge?.mentionOptions?.(target) || [];
    const needle = String(query || "").trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => `${item.label} ${item.fullLabel || ""} ${item.type}`.toLowerCase().includes(needle));
}

function mediaCard(item, onPick) {
    const card = el("button", "a3-card");
    card.type = "button";
    card.title = `${item.fullLabel || item.label}\n点击插入 @ 引用`;
    card.append(mediaThumb(item), el("span", "a3-card-name", item.label));
    card.addEventListener("click", () => onPick(item));
    return card;
}

/**
 * 素材库：浏览可引用素材，单击即把 @ 引用写进提示词编辑器。
 * 第二个标签页可直接从 ComfyUI 输入目录挑素材并自动补进素材加载器。
 */
export function openAssetPalette(target, anchor = null) {
    if (!globalThis.AICG3D_H3?.mentionOptions) {
        toast("素材库只能用在 MiniMax H3 Aicg 节点上", "warn");
        return;
    }
    let palette = null;
    const close = () => palette?.close();

    palette = openPalette({
        anchor,
        title: "素材库",
        subtitle: "点选素材即插入 @ 引用",
        badge: "点选引用",
        tabs: [
            {
                id: "linked",
                label: "可引用素材",
                render: ({ content, query }) => {
                    const items = referenceableMedia(target, query);
                    if (!items.length) {
                        content.append(el("div", "a3-empty", "还没有可引用的素材。把素材加载器接到主节点的 Media 口，或在“输入目录”里挑一个。"));
                        return;
                    }
                    const grid = el("div", "a3-grid");
                    for (const item of items) {
                        grid.append(mediaCard(item, (picked) => {
                            if (globalThis.AICG3D_H3.insertMentionOption(target, picked)) {
                                toast(`已引用 ${picked.label}`, "ok");
                                close();
                            } else {
                                toast("插入失败：请回到结构化提示词编辑器", "warn");
                            }
                        }));
                    }
                    content.append(grid);
                },
            },
            {
                id: "library",
                label: "输入目录",
                render: async ({ content, query }) => {
                    const loader = globalThis.AICG3D_H3.linkedMediaLoader?.(target);
                    const hint = el("div", "a3-hint");
                    hint.style.padding = "0 10px 8px";
                    hint.textContent = loader
                        ? "点选后自动加入素材加载器，并插入 @ 引用。"
                        : "当前节点没有连接素材加载器：点选只会插入普通文件名引用。";
                    content.append(hint);
                    const files = (await library.media())
                        .filter((file) => !query
                            || file.path.toLowerCase().includes(query.toLowerCase())
                            || file.kind.includes(query.toLowerCase()));
                    if (!files.length) {
                        content.append(el("div", "a3-empty", "输入目录里没有匹配的素材"));
                        return;
                    }
                    const grid = el("div", "a3-grid");
                    for (const file of files) {
                        const card = el("button", "a3-card");
                        card.type = "button";
                        card.title = `${file.path}\n${formatSize(file.size)}`;
                        card.append(mediaThumb(file), el("span", "a3-card-name", file.filename));
                        card.addEventListener("click", async () => {
                            const ok = await globalThis.AICG3D_H3.attachMediaFromLibrary?.(target, file);
                            if (!ok) { toast("请先给主节点连接一个素材加载器", "warn"); return; }
                            toast(`已引用 ${file.filename}`, "ok");
                            close();
                        });
                        grid.append(card);
                    }
                    content.append(grid);
                },
            },
        ],
        footer: (() => {
            const wrap = document.createDocumentFragment();
            const upload = el("button", "a3-btn a3-btn--accent", "上传并引用");
            upload.type = "button";
            upload.addEventListener("click", () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "image/*,video/*,audio/*";
                input.multiple = true;
                input.addEventListener("change", async () => {
                    const files = Array.from(input.files || []);
                    if (!files.length) return;
                    const added = await globalThis.AICG3D_H3.uploadToTarget?.(target, files);
                    if (!added) { toast("请先给主节点连接一个素材加载器", "warn"); return; }
                    toast(`已上传并引用 ${added} 个素材`, "ok");
                    close();
                }, { once: true });
                input.click();
            });
            wrap.append(upload, el("span", "a3-hint", "缺少素材？上传后会自动加入素材加载器"));
            return wrap;
        })(),
    });
}

/* ---------------------------- 技能库 / 模板库 ---------------------------- */
function widgetValues(widget) {
    if (Array.isArray(widget?.options?.values)) return widget.options.values;
    if (Array.isArray(widget?.options)) return widget.options;
    return [];
}

function charLabel(chars) {
    const value = Number(chars) || 0;
    if (value >= 10000) return `${(value / 10000).toFixed(1)} 万字`;
    return `${value} 字`;
}

function skillCard(skill, onPick) {
    const item = el("button", "a3-item");
    item.type = "button";
    const main = el("div", "a3-item-main");
    main.append(el("div", "a3-item-title", skill.name || skill.id));
    if (skill.summary) main.append(el("div", "a3-item-desc", skill.summary));
    if (skill.kind === "preset") {
        const meta = el("div", "a3-item-meta");
        meta.append(el("span", "a3-tag", skill.category_name || "模板"));
        if (skill.chars) meta.append(el("span", "a3-dim", charLabel(skill.chars)));
        main.append(meta);
    }
    item.append(main);
    if (skill.kind === "preset") item.append(el("span", "a3-badge a3-badge--preset", "模板"));
    else if (skill.guide_id) item.append(el("span", "a3-badge", "H3 方案"));
    item.addEventListener("click", () => onPick(skill));
    return item;
}

/**
 * 技能库：统一浏览 提示词模板 / 技能 / H3 场景方案，点选后应用到当前节点。
 */
export function openSkillPalette(target, anchor = null) {
    const bridge = globalThis.AICG3D_H3;
    let palette = null;
    let presetCategory = "";
    let categories = [];
    const close = () => palette?.close();

    const apply = (item) => {
        if (item.kind === "preset") {
            // 模板节点：写回 preset 下拉，保证工作流可序列化。
            const presetWidget = widgetOf(target, "preset");
            if (presetWidget) {
                const values = widgetValues(presetWidget);
                const match = values.find((value) => String(value) === item.label || String(value) === item.id);
                const chosen = match ?? item.label;
                setWidgetValue(target, "preset", chosen);
                toast(`已选择模板：${item.name}`, "ok");
                target.__a3PaletteSync?.();
                close();
                return;
            }
        } else {
            // 技能下拉节点：直接把选择写回原生 combo，保证工作流可序列化。
            const skillWidget = widgetOf(target, "skill");
            if (skillWidget) {
                const values = widgetValues(skillWidget);
                const match = values.find((value) => String(value) === item.id || String(value).endsWith(`[${item.id}]`));
                setWidgetValue(target, "skill", match ?? item.id);
                toast(`已选择技能：${item.name}`, "ok");
                close();
                return;
            }
        }
        const guideWidget = widgetOf(target, "prompt_optimizer_scene_guide");
        if (item.guide_id && guideWidget) {
            setWidgetValue(target, "prompt_optimizer_scene_guide", item.guide_id);
            toast(`已应用场景方案：${item.name}`, "ok");
            close();
            return;
        }
        if (bridge?.insertSkillText) {
            const ok = bridge.insertSkillText(target, item);
            if (ok) { toast(`已写入：${item.name}`, "ok"); close(); return; }
        }
        toast("该节点无法写入提示词", "warn");
    };

    function buildPresetChips({ api }) {
        const wrap = el("div", "a3-chips");
        const total = categories.reduce((sum, entry) => sum + (Number(entry.count) || 0), 0);
        const entries = [{ id: "", name: "全部", count: total }].concat(categories);
        for (const entry of entries) {
            const chip = el("button", `a3-chip${entry.id === presetCategory ? " is-active" : ""}`);
            chip.type = "button";
            chip.append(el("span", "a3-chip-name", entry.name));
            if (entry.count) chip.append(el("span", "a3-chip-count", String(entry.count)));
            chip.addEventListener("click", () => {
                presetCategory = entry.id;
                api.refresh();
            });
            wrap.append(chip);
        }
        return wrap;
    }

    const skillTab = (id, label, filter) => ({
        id,
        label,
        render: ({ content, query }) => renderSkillList(content, query, filter, apply),
    });

    const tabs = [
        {
            id: "preset",
            label: "提示词模板",
            toolbar: buildPresetChips,
            render: ({ content, query }) => renderPresetList(content, query, presetCategory, apply),
        },
        skillTab("skill", "全部技能", () => true),
        skillTab("guide", "H3 场景方案", (item) => Boolean(item.guide_id)),
    ];

    const hasSkillWidget = Boolean(widgetOf(target, "skill"));
    const hasPresetWidget = Boolean(widgetOf(target, "preset"));

    palette = openPalette({
        anchor,
        title: "技能库",
        subtitle: "点选即应用到当前节点",
        badge: "AICG3D",
        width: 640,
        initialTab: hasSkillWidget && !hasPresetWidget ? "skill" : "preset",
        tabs,
        footer: (() => {
            const wrap = document.createDocumentFragment();
            const refresh = el("button", "a3-btn", "刷新技能库");
            refresh.type = "button";
            refresh.addEventListener("click", () => { library.clear(); palette?.refresh(); });
            wrap.append(refresh, el("span", "a3-hint", "技能 skills/ ｜ 模板 prompt_presets/"));
            return wrap;
        })(),
    });

    library.presetCategories()
        .then((list) => { categories = list; palette?.refresh(); })
        .catch(() => {});

    return palette;
}

async function renderSkillList(content, query, filter, onPick) {
    const needle = String(query || "").trim().toLowerCase();
    let skills = [];
    try {
        skills = await library.skills();
    } catch (error) {
        content.append(el("div", "a3-empty", `技能库加载失败：${error?.message || error}`));
        return;
    }
    const list = skills
        .filter(filter)
        .filter((skill) => !needle
            || `${skill.name} ${skill.id} ${skill.summary} ${skill.tag}`.toLowerCase().includes(needle));
    if (!list.length) {
        content.append(el("div", "a3-empty", "没有匹配的技能"));
        return;
    }
    const wrap = el("div", "a3-list");
    for (const skill of list) wrap.append(skillCard(skill, onPick));
    content.append(wrap);
}

async function renderPresetList(content, query, category, onPick) {
    const needle = String(query || "").trim().toLowerCase();
    let presets = [];
    try {
        presets = await library.presets();
    } catch (error) {
        content.append(el("div", "a3-empty", `模板库加载失败：${error?.message || error}`));
        return;
    }
    const list = presets
        .filter((item) => !category || item.category === category)
        .filter((item) => !needle
            || `${item.name} ${item.label} ${item.summary} ${item.category_name} ${item.source}`.toLowerCase().includes(needle));
    if (!list.length) {
        content.append(el("div", "a3-empty", "没有匹配的提示词模板"));
        return;
    }
    const wrap = el("div", "a3-list");
    for (const item of list) wrap.append(skillCard(item, onPick));
    content.append(wrap);
}

/** 供其他模块复用的技能选择框。 */
export function skillSelectOptions() {
    return library.skills();
}

export { app, api, openPalette };

/* ------------------------------ 全局注册 ------------------------------ */
globalThis.AICG3D = {
    ensureTheme,
    toast,
    library,
    el,
    createSelect,
    openAssetPalette,
    openSkillPalette,
    formatSize,
    widgetOf,
    setWidgetValue,
    markWidgetHidden,
    autoHideWidgets,
    refreshVueWidgets,
};

app.registerExtension({
    name: "AICG3D.Core",
    setup() {
        ensureTheme();
    },
});
