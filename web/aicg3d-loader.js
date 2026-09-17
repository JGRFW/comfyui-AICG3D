/* ==========================================================================
    Copyright (C) 2026 AICG3D
    SPDX-License-Identifier: GPL-3.0-or-later
    本模块为新增代码（整合三个来源插件）
    ========================================================================== */

/* ==========================================================================
    AICG3D · MiniMax H3 加载器面板
   一个模型 + LoRA 槽位（面板上 1 条起，最多 9 条）+ 文本编码器 + 双 VAE。
   原生 combo 被隐藏，改由本面板统一驱动。
   ========================================================================== */
import { app } from "../../scripts/app.js";
import {
    ensureTheme, el, toast, createSelect, widgetOf, setWidgetValue,
    library, formatSize, selectionText,
    markWidgetHidden, markWidgetVisible, autoHideWidgets, refreshVueWidgets,
    isOwnH3NodeData,
} from "./aicg3d-core.js";

const LOADER_CLASS = "MiniMaxH3EasyLoader";

/* 本插件的节点 ID 带 AICG3D_H3 前缀（上游 ComfyUI-MiniMaxH3-Easy 同名时两边必须分开），
   这里换算回上游那套类名，按名字匹配节点的逻辑就不用逐个改。 */
function h3ClassName(name) {
    const text = String(name ?? "");
    return text.startsWith("AICG3D_H3") ? `MiniMaxH3Easy${text.slice("AICG3D_H3".length)}` : text;
}
// 与 h3easy/nodes.py 的 LORA_SLOT_COUNT 保持一致，改后端必须同步改这里。
const SLOT_COUNT = 9;
const NONE_VALUES = new Set(["", "none", "无"]);

// ref2va_model 面板上已移除，但仍保留在此列表中隐藏，以维持旧工作流的 widget 顺序。
const MODEL_WIDGETS = ["fl2va_model", "ref2va_model", "text_encoder", "video_vae", "audio_vae"];

// 面板建不起来时必须让节点退回原生控件，所以只有这 4 个控件算硬要求。
const REQUIRED_WIDGETS = ["fl2va_model", "text_encoder", "video_vae", "audio_vae"];

function isNone(value) {
    return NONE_VALUES.has(String(value ?? "").trim().toLowerCase());
}

// 与 h3easy/nodes.py 的 LORA_SLOT_COUNT_LEGACY 保持一致。
const LEGACY_SLOT_COUNT = 4;

/** LoRA 槽位在 widgets_values 里的下标（顺序由 h3easy/nodes.py 的 INPUT_TYPES 决定）。 */
function savedLoraIndex(index) {
    const base = MODEL_WIDGETS.length;
    if (index <= LEGACY_SLOT_COUNT) return base + (index - 1) * 2;
    return base + LEGACY_SLOT_COUNT * 2 + 1 + (index - LEGACY_SLOT_COUNT - 1) * 2;
}

/** 载入工作流后槽位若被前端还原成空值，就按存档把 LoRA 补回去。
    只补后端仍然提供的权重，避免把一个不存在的文件写进节点。 */
function repairLoraFromArchive(node, values) {
    if (!Array.isArray(values)) return;
    for (let index = 1; index <= SLOT_COUNT; index += 1) {
        const slot = savedLoraIndex(index);
        const saved = values[slot];
        if (saved === undefined || saved === null || isNone(saved)) continue;
        const widget = widgetOf(node, `lora_${index}`);
        if (!widget || !isNone(widget.value)) continue;
        const options = Array.isArray(widget.options?.values) ? widget.options.values : null;
        if (options && !options.some((item) => String(item) === String(saved))) continue;
        setWidgetValue(node, `lora_${index}`, saved);
        const strength = Number(values[slot + 1]);
        if (Number.isFinite(strength)) setWidgetValue(node, `lora_${index}_strength`, strength);
    }
}

function hideWidget(widget) {
    if (!widget) return;
    widget.__a3Hidden = true;
    markWidgetHidden(widget);
}

function showWidget(widget) {
    if (!widget) return;
    widget.__a3Hidden = false;
    markWidgetVisible(widget);
}

/** 把 autoHideWidgets 在 addWidget 阶段藏掉的原生控件全部放回来。
    面板没建起来却把原生控件藏了，节点就是一片空白 —— 这是最坏的结果，必须兜住。 */
function restoreNativeWidgets(node) {
    let restored = 0;
    for (const widget of node?.widgets || []) {
        if (!widget?.__a3Hidden) continue;
        showWidget(widget);
        restored += 1;
    }
    if (restored) refreshVueWidgets(node);
    refreshLayout(node);
    return restored;
}

function refreshLayout(node) {
    node._widgetSlotsDirty = true;
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
}

function comboOptions(widget, { noneLabel = "不使用" } = {}) {
    const values = Array.isArray(widget?.options?.values) ? widget.options.values
        : Array.isArray(widget?.options) ? widget.options : [];
    return values.map((value) => {
        const text = String(value);
        return {
            value: text,
            label: isNone(text) ? noneLabel : text,
            keywords: text,
            title: text,
        };
    });
}

/** 把 LoRA 元信息并进下拉选项：显示体积、底模、触发词，并带缩略图。 */
function withLoraMeta(options, metas) {
    const index = new Map(metas.map((item) => [item.name, item]));
    return options.map((option) => {
        const meta = index.get(option.value);
        if (!meta) return option;
        return {
            ...option,
            label: meta.label || option.label,
            meta: formatSize(meta.size),
            preview: meta.preview || "",
            keywords: `${option.value} ${meta.base_model || ""} ${meta.trigger || ""} ${meta.title || ""}`,
            title: [meta.title || meta.label, meta.base_model && `底模 ${meta.base_model}`, meta.trigger && `触发词 ${meta.trigger}`]
                .filter(Boolean).join("\n"),
        };
    });
}

function buildLoraRow(node, index, loraMeta) {
    const nameWidget = widgetOf(node, `lora_${index}`);
    const strengthWidget = widgetOf(node, `lora_${index}_strength`);
    const row = el("div", "a3-lora-row");
    const badge = el("span", "a3-lora-index", String(index));
    const body = el("div", "a3-lora-body");
    const nameLine = el("div", "a3-lora-name");
    const strengthLine = el("div", "a3-lora-strength");

    let enabled = !isNone(nameWidget?.value);

    const preview = el("img", "a3-lora-preview");
    preview.alt = "";

    const select = createSelect({
        options: withLoraMeta(comboOptions(nameWidget), loraMeta),
        value: String(nameWidget?.value ?? "none"),
        placeholder: "不使用",
        recentKey: "lora",
        onChange: (value) => {
            if (nameWidget) {
                nameWidget.value = value;
                nameWidget.callback?.(value, app.canvas, node, [0, 0], null);
            }
            enabled = !isNone(value);
            syncRow();
            refreshLayout(node);
        },
    });

    const slider = el("input", "a3-slider");
    slider.type = "range";
    slider.min = String(strengthWidget?.options?.min ?? -4);
    slider.max = String(strengthWidget?.options?.max ?? 4);
    slider.step = String(strengthWidget?.options?.step ?? 0.05);
    slider.value = String(strengthWidget?.value ?? 1);

    const number = el("input", "a3-number");
    number.type = "text";
    number.value = Number(slider.value).toFixed(2);

    const writeStrength = (value) => {
        const next = Math.max(Number(slider.min), Math.min(Number(slider.max), Number(value) || 0));
        slider.value = String(next);
        number.value = next.toFixed(2);
        if (strengthWidget) {
            strengthWidget.value = next;
            strengthWidget.callback?.(next, app.canvas, node, [0, 0], null);
        }
        refreshLayout(node);
    };

    slider.addEventListener("input", () => writeStrength(slider.value));
    slider.addEventListener("pointerdown", (event) => event.stopPropagation());
    number.addEventListener("change", () => writeStrength(number.value));
    number.addEventListener("pointerdown", (event) => event.stopPropagation());

    /* 启用状态与权重都要按控件当前值重算：载入工作流是在面板建好之后
       才把存档写进控件的，用构造时的快照会让重启后的槽位显示成未启用。 */
    function syncStrength() {
        if (!strengthWidget) return;
        if (slider === document.activeElement || number === document.activeElement) return;
        const raw = Number(strengthWidget.value);
        const weight = Number.isFinite(raw) ? raw : 1;
        if (Math.abs(Number(slider.value) - weight) < 1e-6) return;
        slider.value = String(weight);
        number.value = weight.toFixed(2);
    }

    function syncRow() {
        const current = String(nameWidget?.value ?? "none");
        enabled = !isNone(current);
        row.classList.toggle("is-on", enabled);
        select.setValue(current);
        syncStrength();
        const meta = loraMeta.find((item) => item.name === current);
        if (meta?.preview) {
            preview.src = meta.preview;
            preview.hidden = false;
            preview.title = meta.title || meta.label || "";
        } else {
            preview.removeAttribute("src");
            preview.hidden = true;
        }
    }

    nameLine.append(select.element, preview);
    strengthLine.append(slider, number);
    body.append(nameLine, strengthLine);
    row.append(badge, body);
    syncRow();

    return { row, sync: () => { select.setOptions(withLoraMeta(comboOptions(nameWidget), loraMeta)); syncRow(); } };
}

function buildPanel(node) {
    const panel = el("div", "a3-panel");
    panel.addEventListener("pointerdown", (event) => event.stopPropagation());
    panel.addEventListener("wheel", (event) => {
        if (event.target?.closest?.(".a3-menu")) return;
        event.stopPropagation();
    }, { passive: true });

    const head = el("div", "a3-head");
    head.append(el("span", "a3-logo", "AI"), el("span", "a3-title", "MiniMax H3 Aicg 加载器"));
    const summary = el("span", "a3-badge", "");
    head.append(el("span", "a3-spacer"), summary);
    panel.append(head);

    /* ---- 模型 / 编码器 / VAE ---- */
    const ioSection = el("div", "a3-section");
    const ioSelects = [];

    const modelWidget = widgetOf(node, "fl2va_model");
    const modelHint = el("span", "a3-hint");

    const modelRow = el("div", "a3-row a3-row--wide");
    modelRow.append(el("span", "a3-label", "模型"));
    const modelField = el("div", "a3-field");
    const modelSelect = createSelect({
        options: comboOptions(modelWidget, { noneLabel: "未选择" }),
        value: String(modelWidget?.value ?? ""),
        placeholder: "选择 H3 模型",
        recentKey: "h3-model",
        onChange: (value) => {
            if (modelWidget) {
                modelWidget.value = value;
                modelWidget.callback?.(value, app.canvas, node, [0, 0], null);
            }
            modelHint.textContent = isNone(value) ? "必须选择一个 H3 transformer" : "";
            refreshLayout(node);
        },
    });
    modelField.append(modelSelect.element);
    modelRow.append(modelField);
    ioSection.append(modelRow, modelHint);

    for (const [name, label, placeholder] of [
        ["text_encoder", "文本编码器", "选择文本编码器"],
        ["video_vae", "视频 VAE", "选择视频 VAE"],
        ["audio_vae", "音频 VAE", "选择音频 VAE"],
    ]) {
        const widget = widgetOf(node, name);
        const row = el("div", "a3-row a3-row--wide");
        row.append(el("span", "a3-label", label));
        const field = el("div", "a3-field");
        const select = createSelect({
            options: comboOptions(widget, { noneLabel: "未选择" }),
            value: String(widget?.value ?? ""),
            placeholder,
            recentKey: name,
            onChange: (value) => {
                if (widget) {
                    widget.value = value;
                    widget.callback?.(value, app.canvas, node, [0, 0], null);
                }
                refreshLayout(node);
            },
        });
        field.append(select.element);
        row.append(field);
        ioSection.append(row);
        ioSelects.push({ widget, select });
    }
    panel.append(ioSection);

    /* ---- LoRA ---- */
    const loraSection = el("div", "a3-section");
    const loraHead = el("div", "a3-section-head");
    const loraTitle = el("span", "a3-section-title");
    loraTitle.append(el("span", "a3-dot"), document.createTextNode("LoRA"));
    const clearLora = el("button", "a3-btn a3-btn--ghost", "清空");
    clearLora.type = "button";
    clearLora.addEventListener("click", () => {
        for (let index = 1; index <= SLOT_COUNT; index += 1) {
            setWidgetValue(node, `lora_${index}`, "none");
            setWidgetValue(node, `lora_${index}_strength`, 1);
        }
        setCount(1);
    });
    loraHead.append(loraTitle, el("span", "a3-spacer"), clearLora);
    loraSection.append(loraHead);

    const loraRows = [];
    const rowsWrap = el("div", "a3-lora-rows");
    loraSection.append(rowsWrap);

    const loraRemove = el("button", "a3-btn a3-btn--icon", "−");
    const loraAdd = el("button", "a3-btn a3-btn--icon", "+");
    const loraCountText = el("span", "a3-lora-count", "");
    for (const button of [loraRemove, loraAdd]) button.type = "button";
    loraRemove.title = "减少一个 LoRA 槽位";
    loraAdd.title = "增加一个 LoRA 槽位";
    loraRemove.addEventListener("click", () => setCount(loraCount - 1));
    loraAdd.addEventListener("click", () => setCount(loraCount + 1));
    const loraFoot = el("div", "a3-lora-foot");
    loraFoot.append(el("span", "a3-spacer"), loraRemove, loraCountText, loraAdd);
    loraSection.append(loraFoot);
    panel.append(loraSection);

    // 没有 LoRA 控件就别留一块点不动的 LoRA 区域。
    const missingLora = [];
    for (let index = 1; index <= SLOT_COUNT; index += 1) {
        if (!widgetOf(node, `lora_${index}`) || !widgetOf(node, `lora_${index}_strength`)) missingLora.push(index);
    }
    if (missingLora.length) loraSection.style.display = "none";

    /* ---- LoRA 槽位状态 ---- */
    let loraMeta = [];
    let loraCount = 1;
    let loraBooted = false;

    /** 已启用槽位中最靠后的一位，最少为 1；用于载入工作流后展开需要的行。 */
    function requiredLoraCount() {
        for (let index = SLOT_COUNT; index >= 1; index -= 1) {
            if (!isNone(widgetOf(node, `lora_${index}`)?.value)) return index;
        }
        return 1;
    }

    function applyRows() {
        while (loraRows.length < loraCount) {
            const entry = buildLoraRow(node, loraRows.length + 1, loraMeta);
            loraRows.push(entry);
            rowsWrap.append(entry.row);
        }
        while (loraRows.length > loraCount) {
            loraRows.pop().row.remove();
        }
        for (const entry of loraRows) entry.sync();
    }

    function updateFoot() {
        loraCountText.textContent = `${loraCount} / ${SLOT_COUNT}`;
        loraRemove.disabled = loraCount <= 1;
        loraAdd.disabled = loraCount >= SLOT_COUNT;
    }

    function setCount(next) {
        const clamped = Math.max(1, Math.min(SLOT_COUNT, next));
        if (clamped < loraCount) {
            for (let index = clamped + 1; index <= loraCount; index += 1) {
                setWidgetValue(node, `lora_${index}`, "none");
                setWidgetValue(node, `lora_${index}_strength`, 1);
            }
        }
        loraCount = clamped;
        applyRows();
        updateFoot();
        updateSummary();
        refreshLayout(node);
        resize(node);
    }

    /* ---- 汇总 ---- */
    function updateSummary() {
        const active = [];
        for (let index = 1; index <= loraCount; index += 1) {
            const value = widgetOf(node, `lora_${index}`)?.value;
            if (!isNone(value)) active.push(`${selectionText(value)?.split(/[\\/]/).pop() || value} @ ${Number(widgetOf(node, `lora_${index}_strength`)?.value ?? 1).toFixed(2)}`);
        }
        summary.textContent = active.length ? `LoRA ${active.length}` : "纯模型";
        summary.title = active.join("\n");
        clearLora.disabled = !active.length;
    }

    function syncAll() {
        for (const { widget, select } of ioSelects) select.setValue(String(widget?.value ?? ""));
        modelSelect.setOptions(comboOptions(modelWidget, { noneLabel: "未选择" }));
        modelSelect.setValue(String(modelWidget?.value ?? ""));
        // 载入工作流时展开已写入的槽位，避免把已启用的 LoRA 藏在面板外。
        loraCount = Math.max(loraCount, requiredLoraCount());
        applyRows();
        updateFoot();
        updateSummary();
    }

    return {
        panel,
        syncAll,
        syncLoRA: (metas) => {
            loraMeta = Array.isArray(metas) ? metas : [];
            if (!loraBooted) {
                loraBooted = true;
                loraCount = requiredLoraCount();
            } else {
                loraCount = Math.max(loraCount, requiredLoraCount());
            }
            applyRows();
            updateFoot();
            updateSummary();
            resize(node);
        },
        updateSummary,
    };
}

function resize(node) {
    const widget = node.__a3LoaderWidget;
    const panel = node.__a3LoaderPanel;
    if (!widget || !panel) return;
    panel.style.height = "auto";
    const contentHeight = Math.max(1, Math.ceil(panel.scrollHeight || 0));
    node.__a3LoaderMinHeight = contentHeight + 8;
    widget.computeLayoutSize = () => ({ minHeight: node.__a3LoaderMinHeight, maxHeight: undefined, minWidth: 0 });
    widget.options ||= {};
    widget.options.getMinHeight = () => node.__a3LoaderMinHeight;
    const width = Math.max(Number(node.size?.[0]) || 300, 330);
    const height = Math.max(Number(node.size?.[1]) || 0, contentHeight + 60);
    if (height > (Number(node.size?.[1]) || 0) + 1) node.setSize?.([width, height]);
    refreshLayout(node);
}

/** 上游 UI 会整表重排 node.widgets，可能把本面板摘掉，这里补回来。 */
function keepLoaderWidget(node) {
    const widget = node?.__a3LoaderWidget;
    const list = node?.widgets;
    if (!widget || !Array.isArray(list) || list.includes(widget)) return false;
    list.push(widget);
    if (Array.isArray(node._widgets)) node._widgets = list;
    refreshVueWidgets(node);
    refreshLayout(node);
    return true;
}

function installLoaderNode(nodeType, nodeData) {
    if (h3ClassName(nodeData?.name) !== LOADER_CLASS) return;
    // 上游同名插件（ComfyUI-MiniMaxH3-Easy）注册的那份加载器不要装本插件的面板。
    if (!isOwnH3NodeData(nodeData)) return;
    if (nodeType.prototype.__a3LoaderInstalled) return;
    nodeType.prototype.__a3LoaderInstalled = true;

    const hiddenNames = [...MODEL_WIDGETS];
    for (let index = 1; index <= SLOT_COUNT; index += 1) {
        hiddenNames.push(`lora_${index}`, `lora_${index}_strength`);
    }
    autoHideWidgets(nodeType, hiddenNames);

    const setup = (node) => {
        if (!node || node.__a3LoaderSetup || typeof node.addDOMWidget !== "function") return;

        /* 节点类被另一个同名插件（ComfyUI-MiniMaxH3-Easy）抢走注册时，节点上没有 LoRA 槽位。
           这时硬堆面板只会做出一个半残界面，而原生控件已经被 autoHideWidgets 藏了，
           结果是节点全空 —— 直接放弃面板，把原生控件放回来。 */
        const missing = REQUIRED_WIDGETS.filter((name) => !widgetOf(node, name));
        if (missing.length) {
            node.__a3LoaderSetup = true;
            if (!node.__a3LoaderSkipped) {
                node.__a3LoaderSkipped = true;
                console.warn(
                    `[AICG3D] 加载器面板已跳过：节点缺少控件 ${missing.join("、")}。`
                    + "通常是同时启用了 ComfyUI-MiniMaxH3-Easy（与本插件节点同名），已自动退回原生控件。",
                );
            }
            restoreNativeWidgets(node);
            return;
        }

        node.__a3LoaderSetup = true;
        ensureTheme();

        const hidden = [];
        for (const name of MODEL_WIDGETS) hidden.push(widgetOf(node, name));
        for (let index = 1; index <= SLOT_COUNT; index += 1) {
            hidden.push(widgetOf(node, `lora_${index}`), widgetOf(node, `lora_${index}_strength`));
        }

        let built;
        try {
            built = buildPanel(node);
        } catch (error) {
            console.error("[AICG3D] 加载器面板初始化失败，保留原生控件", error);
            node.__a3LoaderSetup = false;
            restoreNativeWidgets(node);
            return;
        }

        let domWidget = null;
        try {
            domWidget = node.addDOMWidget("aicg3d_loader", "aicg3d_loader", built.panel, {
                serialize: false,
                getMinHeight: () => Math.max(1, Number(node.__a3LoaderMinHeight) || 320),
                afterResize: () => resize(node),
            });
        } catch (error) {
            console.error("[AICG3D] 加载器面板挂载失败，保留原生控件", error);
        }
        if (!domWidget) {
            node.__a3LoaderSetup = false;
            restoreNativeWidgets(node);
            return;
        }
        domWidget.serialize = false;
        node.__a3LoaderWidget = domWidget;
        node.__a3LoaderPanel = built.panel;

        // 原生 combo 一律隐藏，节点只显示 AICG3D 面板。
        for (const widget of hidden) hideWidget(widget);
        refreshVueWidgets(node);
        domWidget.hidden = false;
        domWidget.type = "aicg3d_loader";
        refreshLayout(node);
        setTimeout(() => resize(node), 0);

        built.syncAll();

        const applyMeta = (metas) => {
            built.syncLoRA(metas || []);
            resize(node);
        };
        applyMeta(node.__a3LoraMeta || []);
        library.loras()
            .then((metas) => { node.__a3LoraMeta = metas; applyMeta(metas); })
            .catch(() => applyMeta([]));

        node.__a3LoaderSync = () => { built.syncAll(); built.syncLoRA(node.__a3LoraMeta || []); };

        // 上游 UI 重排 node.widgets 后补几次保险，面板被摘掉就装回去。
        for (const delay of [0, 300, 1200]) {
            setTimeout(() => { keepLoaderWidget(node); resize(node); }, delay);
        }
    };

    const chain = (name, after) => {
        const original = nodeType.prototype[name];
        nodeType.prototype[name] = function (...args) {
            const result = original?.apply(this, args);
            try { after(this, args); } catch (error) { console.error("[AICG3D]", error); }
            return result;
        };
    };

    chain("onNodeCreated", (node) => setup(node));
    chain("onAdded", (node) => setup(node));
    chain("onConfigure", (node, args) => {
        setup(node);
        const saved = args?.[0]?.widgets_values;
        node.__a3LoaderSync?.();
        // 载入工作流后再补几次：Nodes 2.0 的响应式控件表挂载时可能把值推回默认，
        // 补回存档里的 LoRA 并刷新面板，避免「保存好了、重启后又得重新选」。
        for (const delay of [0, 200, 800]) {
            setTimeout(() => {
                try {
                    repairLoraFromArchive(node, saved);
                    node.__a3LoaderSync?.();
                    resize(node);
                } catch (error) {
                    console.error("[AICG3D]", error);
                }
            }, delay);
        }
    });
}

app.registerExtension({
    name: "AICG3D.Loader",
    setup() {
        ensureTheme();
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        installLoaderNode(nodeType, nodeData);
    },
});

export { toast };
