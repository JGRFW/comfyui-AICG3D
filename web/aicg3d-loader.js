/* ==========================================================================
    Copyright (C) 2026 AICG3D
    SPDX-License-Identifier: GPL-3.0-or-later
    本模块为新增代码（整合三个来源插件）
    ========================================================================== */

/* ==========================================================================
    AICG3D · MiniMax H3 加载器面板
   一个模型 + 4 个 LoRA 槽位 + 文本编码器 + 双 VAE。
   原生 combo 被隐藏，改由本面板统一驱动。
   ========================================================================== */
import { app } from "../../scripts/app.js";
import {
    ensureTheme, el, toast, createSelect, widgetOf, setWidgetValue,
    library, formatSize, selectionText,
    markWidgetHidden, markWidgetVisible, autoHideWidgets, refreshVueWidgets,
} from "./aicg3d-core.js";

const LOADER_CLASS = "MiniMaxH3EasyLoader";
const SLOT_COUNT = 4;
const NONE_VALUES = new Set(["", "none", "无"]);

// ref2va_model 面板上已移除，但仍保留在此列表中隐藏，以维持旧工作流的 widget 顺序。
const MODEL_WIDGETS = ["fl2va_model", "ref2va_model", "text_encoder", "video_vae", "audio_vae"];

// 面板建不起来时必须让节点退回原生控件，所以只有这 4 个控件算硬要求。
const REQUIRED_WIDGETS = ["fl2va_model", "text_encoder", "video_vae", "audio_vae"];

function isNone(value) {
    return NONE_VALUES.has(String(value ?? "").trim().toLowerCase());
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

    function syncRow() {
        row.classList.toggle("is-on", enabled);
        const current = String(nameWidget?.value ?? "none");
        select.setValue(current);
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
    if (nodeData?.name !== LOADER_CLASS) return;
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
    chain("onConfigure", (node) => {
        setup(node);
        node.__a3LoaderSync?.();
        setTimeout(() => resize(node), 0);
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
