/* Copyright (C) 2026 AICG3D
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Headless runtime UI smoke test. Start Edge/Chrome with:
 *   --headless=new --remote-debugging-port=9223
 * then run:
 *   node tests/manual/ui_runtime_smoke.cjs
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

const CDP_PORT = Number(process.env.AICG3D_CDP_PORT || 9223);
const COMFY_URL = process.env.AICG3D_COMFY_URL || "http://127.0.0.1:8188/";
const TIMEOUT_MS = Number(process.env.AICG3D_UI_TIMEOUT_MS || 45000);
const CDP_TARGET_ID = String(process.env.AICG3D_CDP_TARGET_ID || "").trim();
const FORCE_RELOAD = process.env.AICG3D_UI_FORCE_RELOAD === "1";

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function selectTarget() {
    const response = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`);
    if (!response.ok) throw new Error(`CDP target list failed: ${response.status}`);
    const targets = await response.json();
    const pages = targets.filter((item) => item.type === "page" && item.webSocketDebuggerUrl);
    if (CDP_TARGET_ID) {
        const selected = pages.find((item) => String(item.id || "") === CDP_TARGET_ID);
        if (!selected) throw new Error(`CDP target not found: ${CDP_TARGET_ID}`);
        return selected;
    }
    const page = pages.find((item) =>
        String(item.url || "").startsWith(COMFY_URL) && /ComfyUI/i.test(String(item.title || "")),
    ) || pages.find((item) => String(item.url || "").startsWith(COMFY_URL)) || pages[0];
    if (!page) throw new Error("No inspectable CDP page found");
    return page;
}

async function main() {
    const target = await selectTarget();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    const pending = new Map();
    const runtimeErrors = [];
    let nextId = 1;

    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        if (message.id && pending.has(message.id)) {
            const { resolve, reject } = pending.get(message.id);
            pending.delete(message.id);
            if (message.error) reject(new Error(message.error.message));
            else resolve(message.result);
            return;
        }
        if (message.method === "Runtime.exceptionThrown") {
            runtimeErrors.push(message.params?.exceptionDetails?.text || "Uncaught exception");
        }
        if (message.method === "Runtime.consoleAPICalled" && message.params?.type === "error") {
            runtimeErrors.push(
                (message.params.args || []).map((item) => item.value ?? item.description ?? "").join(" "),
            );
        }
    });

    await new Promise((resolve, reject) => {
        socket.addEventListener("open", resolve, { once: true });
        socket.addEventListener("error", reject, { once: true });
    });

    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const id = nextId++;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
    });

    const evaluate = async (expression) => {
        const result = await send("Runtime.evaluate", {
            expression,
            awaitPromise: true,
            returnByValue: true,
            userGesture: true,
        });
        if (result.exceptionDetails) {
            const details = result.exceptionDetails;
            throw new Error(details.exception?.description || details.text || "Runtime.evaluate failed");
        }
        return result.result?.value;
    };

    await send("Runtime.enable");
    await send("Page.enable");
    await send("Network.enable");
    await send("Network.setCacheDisabled", { cacheDisabled: true });
    await send("Emulation.setDeviceMetricsOverride", {
        width: 1600,
        height: 1100,
        deviceScaleFactor: 1,
        mobile: false,
    });
    let alreadyReady = false;
    try {
        alreadyReady = await evaluate(
            "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && globalThis.LiteGraph?.createNode && globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3SequenceSegment'])",
        );
    } catch { /* page is still loading */ }
    if (!alreadyReady || FORCE_RELOAD) await send("Page.navigate", { url: COMFY_URL });

    const started = Date.now();
    while (Date.now() - started < TIMEOUT_MS) {
        try {
            const ready = await evaluate(
                "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && globalThis.LiteGraph?.createNode && "
                + "globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3SequenceSegment'])",
            );
            if (ready) break;
        } catch {
            // The document is still navigating.
        }
        await sleep(250);
    }

    const ready = await evaluate(
        "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && globalThis.LiteGraph?.createNode && "
        + "globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3SequenceSegment'])",
    );
    if (!ready) throw new Error("ComfyUI frontend did not become ready");
    // ComfyUI restores the previous workflow after its extension registry becomes
    // ready. Wait for that second load to settle before replacing the graph.
    await sleep(4000);

    const report = await evaluate(`(async () => {
        globalThis.__aicg3dSmokeProgress = "start";
        const app = globalThis.app || globalThis.comfyAPI?.app?.app;
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const graph = app.graph;
        const originalNodes = [...(graph?._nodes || [])];
        for (const node of originalNodes) graph.remove?.(node);
        const create = (type, pos) => {
            const node = LiteGraph.createNode(type);
            if (!node) throw new Error("Missing node type: " + type);
            node.pos = pos;
            graph.add(node);
            return node;
        };
        const widget = (node, name) => (node?.widgets || []).find((item) => item.name === name) || null;
        const setWidget = (node, name, value) => {
            const item = widget(node, name);
            if (!item) throw new Error("Missing widget: " + name);
            item.value = value;
            if (item._state) item._state.value = value;
            item.callback?.call(item, value);
        };
        const approx = (a, b, tolerance = 1.5) => Math.abs(Number(a) - Number(b)) <= tolerance;
        const buttonByText = (node, text) => [...(node?.__h3SequenceActionRow?.element?.querySelectorAll?.("button") || [])]
            .find((item) => String(item.textContent || "").includes(text)) || null;
        const isVueNodesMode = Boolean(globalThis.LiteGraph?.vueNodesMode);

        const globalNode = create("AICG3D_H3SequenceGlobal", [40, 40]);
        const combine = create("AICG3D_H3SequenceCombine", [520, 40]);
        const segments = [
            create("AICG3D_H3SequenceSegment", [40, 520]),
            create("AICG3D_H3SequenceSegment", [520, 520]),
            create("AICG3D_H3SequenceSegment", [1000, 520]),
        ];
        await sleep(1800);
        for (const node of segments) {
            node.size = [430, 610];
            node.setSize?.([430, 610]);
        }
        await sleep(300);
        let stagePreviewOrdered = true;
        let stagePreviewSingleCard = true;
        let stagePreviewFullWidth = true;
        let stagePreviewAspect = 0;
        let stagePreviewAspectMatches = true;
        let stagePreviewResizeStable = true;
        let canvasSizeRowStable = true;
        if (isVueNodesMode) {
            const stagePreviewPanel = segments[0].__h3SequenceStagePreviewPanel;
            const actionRowElement = segments[0].__h3SequenceActionRow?.element;
            if (!stagePreviewPanel || !actionRowElement) throw new Error("Sequence stage preview area is missing");
            const stagePreviewRect = stagePreviewPanel.getBoundingClientRect();
            const actionRowRect = actionRowElement.getBoundingClientRect();
            const stageCards = [...stagePreviewPanel.querySelectorAll(".h3-sequence-stage-card")];
            stagePreviewSingleCard = stageCards.length === 1;
            if (!stagePreviewSingleCard) throw new Error("Sequence stage preview must contain exactly one card");
            if (!String(stageCards[0].textContent || "").includes("本段视频")) throw new Error("Final segment preview label is missing");
            if (String(stagePreviewPanel.textContent || "").includes("一采视频")) throw new Error("First-pass preview is still visible");
            const stageCardRect = stageCards[0].getBoundingClientRect();
            stagePreviewFullWidth = approx(stageCardRect.width, stagePreviewRect.width, 2);
            if (!stagePreviewFullWidth) throw new Error("Final segment preview does not fill the preview row");
            stagePreviewAspect = stagePreviewRect.height > 0 ? stagePreviewRect.width / stagePreviewRect.height : 0;
            stagePreviewAspectMatches = approx(stagePreviewAspect, 512 / 296, 0.04);
            if (!stagePreviewAspectMatches) {
                throw new Error("Final segment preview does not use the sampling-preview aspect ratio: " + JSON.stringify({
                    width: stagePreviewRect.width,
                    height: stagePreviewRect.height,
                    aspect: stagePreviewAspect,
                    nodeWidth: segments[0].size?.[0],
                    cssHeight: stagePreviewPanel.style.getPropertyValue("--h3-sequence-stage-preview-height"),
                }));
            }
            const stageSizeBeforeResize = [...segments[0].size];
            globalThis.__aicg3dSmokeProgress = "stage-before-resize";
            segments[0].setSize([520, stageSizeBeforeResize[1]]);
            await sleep(900);
            globalThis.__aicg3dSmokeProgress = "stage-resized";
            const resizedStagePreviewRect = stagePreviewPanel.getBoundingClientRect();
            const resizedStagePreviewAspect = resizedStagePreviewRect.height > 0
                ? resizedStagePreviewRect.width / resizedStagePreviewRect.height
                : 0;
            stagePreviewResizeStable = approx(resizedStagePreviewAspect, 512 / 296, 0.04)
                && approx(segments[0].size[0], 520, 1);
            if (!stagePreviewResizeStable) {
                throw new Error("Sequence stage preview resize did not preserve aspect ratio or node width");
            }
            segments[0].setSize(stageSizeBeforeResize);
            await sleep(500);
            stagePreviewOrdered = actionRowRect.bottom <= stagePreviewRect.top + 2;
            if (!stagePreviewOrdered) throw new Error("Sequence action row overlaps the stage preview area");
            const canvasSizeRow = globalNode.__h3SequenceSizeWidget?.element;
            if (!canvasSizeRow) throw new Error("Smart Drama canvas-size row is missing");
            const canvasSizeWrapper = canvasSizeRow.closest?.(".lg-node-widget")?.parentElement || canvasSizeRow.parentElement;
            const canvasSizeHeightBefore = canvasSizeRow.getBoundingClientRect().height;
            const canvasWrapperHeightBefore = canvasSizeWrapper.getBoundingClientRect().height;
            const globalSizeBeforeStretch = [...globalNode.size];
            globalNode.setSize([globalSizeBeforeStretch[0], globalSizeBeforeStretch[1] + 300]);
            await sleep(900);
            const canvasSizeHeightAfter = canvasSizeRow.getBoundingClientRect().height;
            const canvasWrapperHeightAfter = canvasSizeWrapper.getBoundingClientRect().height;
            canvasSizeRowStable = canvasSizeHeightBefore > 0
                && canvasWrapperHeightBefore > 0
                && approx(canvasWrapperHeightBefore, canvasWrapperHeightAfter, 2.5)
                && approx(canvasSizeHeightBefore, canvasSizeHeightAfter, 2.5);
            globalNode.setSize(globalSizeBeforeStretch);
            await sleep(300);
            if (!canvasSizeRowStable) {
                throw new Error("Smart Drama canvas-size row stretched with the node: " + JSON.stringify({
                    canvasSizeHeightBefore,
                    canvasSizeHeightAfter,
                    canvasWrapperHeightBefore,
                    canvasWrapperHeightAfter,
                }));
            }
        }

        const segmentOutputNames = (segments[0].outputs || []).map((output) => String(output?.name || ""));
        if (segmentOutputNames.join(",") !== "segment") {
            throw new Error("Sequence segment should only expose the segment output: " + segmentOutputNames.join(","));
        }
        if (widget(segments[0], "emit_segment_video") || widget(segments[0], "emit_first_pass_video")) {
            throw new Error("Removed segment video output controls are still visible");
        }

        const parser = create("AICG3D_H3PromptSegmentSplit", [1000, 40]);
        await sleep(500);
        setWidget(parser, "auto_fill", false);
        setWidget(parser, "max_segments", 3);
        setWidget(parser, "text", [
            "第1段（3秒）：女子看向门口并说：你终于来了。",
            "第2段（5秒）：男子走向桌边并说：我带了你要的东西。",
            "第3段（4秒）：两人同时望向窗外，环境声继续。",
        ].join("\\n\\n"));

        const sizesBeforeFill = segments.map((node) => [...node.size]);
        const fillButton = (parser.widgets || []).find((item) => String(item.name || "").startsWith("一键填入全部视频段落"));
        if (!fillButton) throw new Error("Prompt-split fill button is missing");
        fillButton.callback?.call(fillButton);
        await sleep(1200);
        const filled = segments.map((node) => String(widget(node, "prompt")?.value || ""));
        const sizesAfterFill = segments.map((node) => [...node.size]);
        if (!filled.every((value, index) => value.includes("第" + (index + 1) + "段"))) {
            const expected = ["你终于来了", "我带了你要的东西", "两人同时望向窗外"];
            if (!filled.every((value, index) => value.includes(expected[index]))) {
                throw new Error("Batch prompt fill did not reach every segment: " + JSON.stringify(filled));
            }
        }
        const fillSizeStable = sizesBeforeFill.every((size, index) =>
            approx(size[0], sizesAfterFill[index][0]) && approx(size[1], sizesAfterFill[index][1]));
        if (!fillSizeStable) throw new Error("Batch prompt fill resized a segment node");
        globalThis.__aicg3dSmokeProgress = "prompt-filled";

        const resourceNode = segments[0];
        const sizeBeforeResource = [...resourceNode.size];
        resourceNode.__h3SequenceResourceButton?.click?.();
        await sleep(900);
        const resourceOpen = Boolean(resourceNode.__h3InlineMediaPanelWidget && resourceNode.__h3InlineMediaOpen);
        if (!resourceOpen) throw new Error("Inline media library did not open");
        const sizeOpen = [...resourceNode.size];
        const widthStableWhileOpen = approx(sizeBeforeResource[0], sizeOpen[0]);
        if (!widthStableWhileOpen) throw new Error("Opening the media library changed node width");
        if (sizeOpen[1] + 1 < sizeBeforeResource[1]) throw new Error("Opening the media library shrank the node");
        const closeButton = [...(resourceNode.__h3MediaLoaderPanel?.querySelectorAll?.("button") || [])]
            .find((item) => String(item.textContent || "").includes("收起"));
        closeButton?.click?.();
        await sleep(700);
        const sizeClosed = [...resourceNode.size];
        if (resourceOpen && resourceNode.__h3InlineMediaOpen) throw new Error("Media library did not close");
        if (sizeClosed[1] + 1 < sizeBeforeResource[1]) throw new Error("Closing the media library shrank below its original size");
        globalThis.__aicg3dSmokeProgress = "resource-closed";

        const standalone = create("AICG3D_H3SequenceSegment", [40, 1260]);
        await sleep(600);
        standalone.size = [430, 610];
        standalone.setSize?.([430, 610]);
        const countBeforeNext = (graph._nodes || []).length;
        const idsBeforeNext = new Set((graph._nodes || []).map((node) => node.id));
        standalone.__h3SequenceNextButton?.click?.();
        globalThis.__aicg3dSmokeProgress = "add-next";
        await sleep(800);
        const countAfterNext = (graph._nodes || []).length;
        if (countAfterNext !== countBeforeNext + 1) throw new Error("Add-next-segment did not create one node");
        const added = (graph._nodes || []).find((node) => !idsBeforeNext.has(node.id));
        if (!added) throw new Error("Newly added segment could not be located");
        const previousInput = (added.inputs || []).find((input) => input.name === "previous_segment");
        if (!previousInput || previousInput.link == null) throw new Error("Added segment was not linked to its previous segment");
        const deleteButton = buttonByText(added, "删除这一段");
        deleteButton?.click?.();
        await sleep(600);
        if ((graph._nodes || []).includes(added)) throw new Error("Delete-this-segment did not remove the node");
        globalThis.__aicg3dSmokeProgress = "segment-deleted";

        const secondPass = widget(globalNode, "second_pass");
        const globalWidth = Number(globalNode.size?.[0] || 0);
        const hiddenBefore = ["second_pass_model", "second_pass_scale", "second_pass_steps"]
            .map((name) => Boolean(widget(globalNode, name)?.hidden));
        setWidget(globalNode, "second_pass", true);
        await sleep(400);
        const hiddenOn = ["second_pass_model", "second_pass_scale", "second_pass_steps"]
            .map((name) => Boolean(widget(globalNode, name)?.hidden));
        setWidget(globalNode, "second_pass", false);
        await sleep(400);
        const hiddenOff = ["second_pass_model", "second_pass_scale", "second_pass_steps"]
            .map((name) => Boolean(widget(globalNode, name)?.hidden));
        if (!hiddenBefore.every(Boolean) || hiddenOn.some(Boolean) || !hiddenOff.every(Boolean)) {
            throw new Error("Smart Drama second-pass controls are not showing/hiding correctly");
        }
        if (!approx(globalWidth, globalNode.size?.[0])) throw new Error("Second-pass toggle changed node width");

        const repairNode = create("AICG3D_H3RenderPass2", [1480, 40]);
        globalThis.__aicg3dSmokeProgress = "repair-created";
        await sleep(700);
        const repairWidth = Number(repairNode.size?.[0] || 0);
        const repairHidden = (name) => Boolean(widget(repairNode, name)?.hidden);
        const repairOffHidden = ["repair_model", "repair_batch_size", "repair_quality"]
            .map(repairHidden);
        setWidget(repairNode, "repair_engine", "SeedVR2 视频修复");
        await sleep(350);
        const seedVisible = !repairHidden("repair_model") && !repairHidden("repair_batch_size") && repairHidden("repair_quality");
        setWidget(repairNode, "repair_engine", "RTX VSR 超分");
        await sleep(350);
        const rtxVisible = repairHidden("repair_model") && !repairHidden("repair_scale") && !repairHidden("repair_quality");
        setWidget(repairNode, "repair_engine", "VOSR2 单帧修复");
        await sleep(350);
        const vosrVisible = !repairHidden("repair_model") && repairHidden("repair_batch_size") && repairHidden("repair_quality");
        setWidget(repairNode, "repair_engine", "关闭（仅 H3 二采）");
        await sleep(350);
        const repairOffAgain = ["repair_model", "repair_batch_size", "repair_quality"]
            .map(repairHidden);
        if (!repairOffHidden.every(Boolean) || !seedVisible || !rtxVisible || !vosrVisible || !repairOffAgain.every(Boolean)) {
            throw new Error("Pass-2 restoration engine controls are not showing/hiding correctly");
        }
        if (!approx(repairWidth, repairNode.size?.[0])) throw new Error("Restoration engine toggle changed node width");

        globalThis.__aicg3dSmokeProgress = "advanced-render-created";
        const advancedNode = create("AICG3D_H3RenderAdvancedWithModel", [40, 1900]);
        await sleep(800);
        const advancedToggle = widget(advancedNode, "show_advanced_inputs");
        const advancedOptionalNames = [
            "sampler", "sigmas", "guide_image", "guide_audio",
            "digital_human_lowres_model", "digital_human_highres_model",
        ];
        const advancedOptionalInputs = advancedOptionalNames.map((name) =>
            (advancedNode.inputs || []).find((input) => input.name === name));
        if (!advancedToggle || advancedOptionalInputs.some((input) => !input)) {
            throw new Error("Advanced renderer lost its fold toggle or optional input slots");
        }
        const advancedSlotIndexes = advancedOptionalInputs.map((input) => advancedNode.inputs.indexOf(input));
        const advancedCollapsed = Number(advancedToggle.value) === 0
            && advancedOptionalInputs.every((input) => Boolean(input.hidden) && input.visible === false);
        const previewWidgetIsLast = String(advancedNode.widgets?.at(-1)?.name || "") === "sample_preview";
        const advancedSizeBefore = [...advancedNode.size];
        const firstVisibleWidgetY = () => {
            advancedNode.arrange?.();
            return Number((advancedNode.widgets || []).find((item) => !item.hidden)?.y);
        };
        const advancedCollapsedCanvasWidgetY = firstVisibleWidgetY();
        setWidget(advancedNode, "show_advanced_inputs", true);
        await sleep(500);
        const advancedExpanded = advancedOptionalInputs.every((input) => !input.hidden && input.visible !== false);
        const advancedExpandedCanvasWidgetY = firstVisibleWidgetY();
        const advancedOpenSize = [...advancedNode.size];
        setWidget(advancedNode, "show_advanced_inputs", false);
        await sleep(500);
        const advancedClosedAgain = advancedOptionalInputs.every((input) => Boolean(input.hidden) && input.visible === false);
        const advancedClosedCanvasWidgetY = firstVisibleWidgetY();
        const advancedFoldSlotStable = advancedSlotIndexes.every((index, position) =>
            advancedNode.inputs[index] === advancedOptionalInputs[position]);
        const advancedH3SlotY = advancedNode.getInputPos(1)[1] - advancedNode.pos[1];
        const advancedCanvasLayoutStable = isVueNodesMode || (
            Number.isFinite(advancedCollapsedCanvasWidgetY)
            && advancedCollapsedCanvasWidgetY <= advancedH3SlotY + 13
            && advancedExpandedCanvasWidgetY >= advancedCollapsedCanvasWidgetY + 100
            && approx(advancedClosedCanvasWidgetY, advancedCollapsedCanvasWidgetY)
        );
        const advancedFoldSizeStable = approx(advancedSizeBefore[0], advancedOpenSize[0])
            && approx(advancedSizeBefore[0], advancedNode.size?.[0])
            && approx(advancedSizeBefore[1], advancedOpenSize[1])
            && approx(advancedSizeBefore[1], advancedNode.size?.[1]);
        if (!advancedCollapsed || !advancedExpanded || !advancedClosedAgain
            || !previewWidgetIsLast || !advancedFoldSlotStable || !advancedFoldSizeStable) {
            throw new Error("Advanced renderer optional inputs do not fold consistently");
        }
        if (!advancedCanvasLayoutStable) {
            throw new Error("Classic canvas kept a gap for collapsed advanced inputs: " + JSON.stringify({
                collapsedY: advancedCollapsedCanvasWidgetY,
                expandedY: advancedExpandedCanvasWidgetY,
                closedY: advancedClosedCanvasWidgetY,
                h3SlotY: advancedH3SlotY,
            }));
        }

        const advancedDomRows = () => advancedOptionalInputs.map((input) => {
            const inputIndex = advancedNode.inputs.indexOf(input);
            const slotKey = String(advancedNode.id) + "-in-" + inputIndex;
            const slot = [...document.querySelectorAll("[data-slot-key]")]
                .find((element) => element.dataset?.slotKey === slotKey);
            const row = slot?.closest?.(".lg-slot.lg-slot--input") || null;
            const rect = row?.getBoundingClientRect?.();
            return {
                name: input.name,
                found: Boolean(row),
                display: row ? getComputedStyle(row).display : "missing",
                height: rect?.height || 0,
                hidden: Boolean(row?.hidden),
            };
        });
        let domRowsCollapsed = true;
        let domRowsExpanded = true;
        let domRowsClosedAgain = true;
        if (isVueNodesMode) {
            domRowsCollapsed = advancedDomRows().every((row) =>
                row.found && row.display === "none" && row.height < 0.5 && row.hidden);
            setWidget(advancedNode, "show_advanced_inputs", true);
            await sleep(500);
            domRowsExpanded = advancedDomRows().every((row) =>
                row.found && row.display !== "none" && row.height > 15 && !row.hidden);
            setWidget(advancedNode, "show_advanced_inputs", false);
            await sleep(500);
            domRowsClosedAgain = advancedDomRows().every((row) =>
                row.found && row.display === "none" && row.height < 0.5 && row.hidden);
        }
        if (!domRowsCollapsed || !domRowsExpanded || !domRowsClosedAgain) {
            throw new Error("Advanced renderer rows do not fold in Nodes 2.0: " + JSON.stringify({
                collapsed: advancedDomRows(),
                domRowsCollapsed, domRowsExpanded, domRowsClosedAgain,
            }));
        }

        const connectedInput = advancedNode.inputs[advancedSlotIndexes[0]];
        const connectedInputIndex = advancedSlotIndexes[0];
        setWidget(advancedNode, "show_advanced_inputs", true);
        await sleep(300);
        const samplerSource = create("KSamplerSelect", [1480, 1260]);
        const connectedLink = samplerSource.connect?.(0, advancedNode, connectedInputIndex);
        await sleep(150);
        if (!connectedLink) throw new Error("Could not create a real sampler connection for advanced-input test");
        setWidget(advancedNode, "show_advanced_inputs", false);
        await sleep(350);
        const currentAdvancedToggle = widget(advancedNode, "show_advanced_inputs");
        const advancedAutoExpanded = Number(currentAdvancedToggle?.value) === 1
            && advancedOptionalNames.every((name) => {
                const input = (advancedNode.inputs || []).find((slot) => slot.name === name);
                return input && !input.hidden && input.visible !== false;
            });
        graph.remove?.(samplerSource);
        setWidget(advancedNode, "show_advanced_inputs", false);
        await sleep(250);
        if (!advancedAutoExpanded) {
            const currentInput = (advancedNode.inputs || []).find((slot) => slot.name === advancedOptionalNames[0]);
            throw new Error("Connected advanced input did not auto-expand: " + JSON.stringify({
                toggle: currentAdvancedToggle?.value,
                input: currentInput ? { link: currentInput.link, hidden: currentInput.hidden, visible: currentInput.visible } : null,
            }));
        }

        const legacyRefiner = "minimax\\minimax_h3_open_regenerate_2k_refiner_rank_384_bf16.safetensors";
        const legacyAdvancedValues = [
            771204598, "fixed", "er_sde", "beta", 8, 1, "释放缓存", 0, true, 1.5, 1, 4, 0.3,
            "minimax_h3_latent_upscaler_3d_fp16_V2.safetensors", true, legacyRefiner,
        ];
        const legacyAdvancedInfo = {
            id: advancedNode.id, type: "AICG3D_H3RenderAdvancedWithModel",
            pos: [...advancedNode.pos], size: [...advancedNode.size], flags: {}, order: 0, mode: 0,
            inputs: [], outputs: [], properties: {},
            widgets_values: legacyAdvancedValues,
            widgets_values_named: {
                noise_seed: 771204598, control_after_generate: "fixed", sampler_name: "er_sde", scheduler: "beta",
                steps: 8, denoise: 1, cleanup_after_run: "释放缓存", guide_frame_idx: 0,
                digital_human_selflift: true, digital_human_upscale_scale: 1.5, digital_human_cfg: 1,
                digital_human_transition_step: 4, digital_human_lowres_scale: 0.3,
                digital_human_upscaler_model: "minimax_h3_latent_upscaler_3d_fp16_V2.safetensors",
                sample_preview: true, digital_human_refiner_lora: legacyRefiner,
            },
        };
        globalThis.__aicg3dLegacyAdvancedInfo = legacyAdvancedInfo;
        advancedNode.configure?.(legacyAdvancedInfo);
        await sleep(500);
        const migratedRefiner = widget(advancedNode, "digital_human_refiner_lora");
        const migratedPreview = widget(advancedNode, "sample_preview");
        const migratedToggle = widget(advancedNode, "show_advanced_inputs");
        const legacyMigrationStable = String(migratedRefiner?.value || "") === legacyRefiner
            && Number(migratedToggle?.value) === 0
            && Number(migratedPreview?.value) === 1;
        if (!legacyMigrationStable) {
            throw new Error("Legacy advanced renderer widget order migration is incorrect: " + JSON.stringify({
                refiner: migratedRefiner?.value, toggle: migratedToggle?.value, preview: migratedPreview?.value,
                values: legacyAdvancedInfo.widgets_values,
                named: legacyAdvancedInfo.widgets_values_named,
            }));
        }
        globalThis.__aicg3dAdvancedNode = advancedNode;


        globalThis.__aicg3dSmokeProgress = "final-created";
        const finalPacked = Boolean(LiteGraph.registered_node_types?.["AICG3D_H3FinalHighResUpscalePacked"]);
        const finalNode = create(
            finalPacked ? "AICG3D_H3FinalHighResUpscalePacked" : "AICG3D_H3FinalHighResUpscale",
            [1480, 800],
        );
        globalThis.__aicg3dFinalNode = finalNode;
        await sleep(900);
        const finalWidget = (name) => widget(finalNode, name);
        const finalHidden = (name) => Boolean(finalWidget(name)?.hidden);
        const finalNames = [
            "filename_prefix", "second_pass", "latent_upscale_model", "upscale_mode", "upscale_scale",
            "target_width", "target_height", "upscale_device", "upscale_precision", "sampler_name",
            "scheduler", "steps", "second_pass_denoise", "second_pass_seed", "tiled_sampling",
            "tile_width", "tile_height", "tile_overlap", "tile_fade", "repair_engine",
            "repair_model", "repair_scale", "repair_batch_size", "repair_temporal_overlap",
            "repair_color_correction", "repair_quality", "repair_device", "repair_blocks_to_swap",
            "repair_offload_device", "repair_vae_tiling", "lock_source_exposure", "max_window_frames",
            "window_overlap_frames", "sample_preview", "preview_interval", "cleanup_after_run",
        ];
        if (finalPacked) finalNames.push("refiner_lora", "show_advanced_settings");
        const finalInputsPresent = finalNames.every((name) => Boolean(finalWidget(name)));
        if (!finalInputsPresent) throw new Error("Final upscale node lost one or more Python inputs");
        const finalInputSlots = (finalNode.inputs || []).filter((input) => !input?.widget).map((input) => String(input?.name || ""));
        if (finalPacked && (finalInputSlots.length !== 1 || finalInputSlots[0] !== "final_sequence")) {
            throw new Error("Packed final upscale must expose only the final_sequence input slot: " + finalInputSlots.join(","));
        }
        const finalLabels = {
            filename_prefix: "输出文件名前缀",
            second_pass: "H3 潜空间二采",
            latent_upscale_model: "潜空间放大模型",
            upscale_mode: "尺寸模式",
            upscale_scale: "放大倍数",
            upscale_device: "放大设备",
            upscale_precision: "放大精度",
            steps: "采样步数",
            repair_engine: "画质修复引擎",
            repair_quality: "修复质量",
            sample_preview: "采样预览",
            cleanup_after_run: "运行后清理",
        };
        const finalLabelsChinese = Object.entries(finalLabels)
            .every(([name, label]) => String(finalWidget(name)?.label || "") === label);
        const finalDeviceOptions = (finalWidget("upscale_device")?.options?.values || []).join("|");
        const finalPrecisionOptions = (finalWidget("upscale_precision")?.options?.values || []).join("|");
        const finalQualityOptions = (finalWidget("repair_quality")?.options?.values || []).join("|");
        const finalComboLabelsChinese = finalDeviceOptions.includes("GPU（CUDA）")
            && finalPrecisionOptions.includes("BF16 混合精度")
            && finalQualityOptions.includes("超高质量");
        if (!finalLabelsChinese || !finalComboLabelsChinese) {
            throw new Error("Final upscale node still exposes untranslated labels or menu values");
        }
        globalThis.__aicg3dSmokeProgress = "final-labels";
        const finalWidth = Number(finalNode.size?.[0] || 0);
        let finalPackedStartsCollapsed = true;
        if (finalPacked) {
            const packedAdvancedNames = [
                "latent_upscale_model", "upscale_device", "upscale_precision", "tiled_sampling",
                "tile_width", "tile_height", "tile_overlap", "tile_fade", "repair_engine",
                "repair_model", "repair_scale", "repair_batch_size", "repair_temporal_overlap",
                "repair_color_correction", "repair_quality", "repair_device", "repair_blocks_to_swap",
                "repair_offload_device", "repair_vae_tiling", "max_window_frames", "window_overlap_frames",
                "sample_preview", "preview_interval", "cleanup_after_run",
            ];
            finalPackedStartsCollapsed = finalWidget("show_advanced_settings")?.value === false
                && packedAdvancedNames.every(finalHidden)
                && !finalHidden("show_advanced_settings")
                && !finalHidden("upscale_mode")
                && !finalHidden("sampler_name")
                && !finalHidden("lock_source_exposure");
            if (!finalPackedStartsCollapsed) throw new Error("Packed final upscale advanced settings do not start collapsed");
            setWidget(finalNode, "show_advanced_settings", true);
            await sleep(450);
        }
        setWidget(finalNode, "second_pass", false);
        await sleep(450);
        const finalLatentNames = [
            "latent_upscale_model", "upscale_mode", "upscale_scale", "target_width", "target_height",
            "upscale_device", "upscale_precision", "sampler_name", "scheduler", "steps",
            "second_pass_denoise", "second_pass_seed", "tiled_sampling", "tile_width", "tile_height",
            "tile_overlap", "tile_fade", "sample_preview", "preview_interval",
        ];
        if (finalPacked) finalLatentNames.push("refiner_lora");
        const finalSecondPassFolded = finalLatentNames.every(finalHidden) && !finalHidden("second_pass");
        if (!finalSecondPassFolded) throw new Error("Final upscale second-pass settings do not fold when disabled");

        setWidget(finalNode, "repair_engine", "SeedVR2 视频修复");
        await sleep(400);
        const finalSeedVr2Visible = !finalHidden("repair_model")
            && !finalHidden("repair_batch_size")
            && !finalHidden("repair_color_correction")
            && finalHidden("repair_quality");
        setWidget(finalNode, "repair_engine", "RTX VSR 超分");
        await sleep(400);
        const finalRtxVisible = finalHidden("repair_model")
            && finalHidden("repair_batch_size")
            && !finalHidden("repair_quality");
        setWidget(finalNode, "repair_engine", "VOSR2 单帧修复");
        await sleep(400);
        const finalVosrVisible = !finalHidden("repair_model")
            && finalHidden("repair_batch_size")
            && finalHidden("repair_quality");
        setWidget(finalNode, "repair_engine", "关闭（仅 H3 二采）");
        setWidget(finalNode, "second_pass", true);
        setWidget(finalNode, "upscale_mode", "按倍数放大");
        setWidget(finalNode, "tiled_sampling", "关");
        setWidget(finalNode, "sample_preview", "关");
        await sleep(450);
        const finalScaleMode = !finalHidden("upscale_scale")
            && finalHidden("target_width")
            && finalHidden("tile_width")
            && finalHidden("preview_interval");
        setWidget(finalNode, "upscale_mode", "目标分辨率（720P→1080P）");
        await sleep(350);
        const finalTargetMode = finalHidden("upscale_scale")
            && !finalHidden("target_width")
            && !finalHidden("target_height");
        setWidget(finalNode, "upscale_mode", "仅采样修复（不再放大）");
        await sleep(350);
        const finalRepairOnlyMode = finalHidden("upscale_scale")
            && finalHidden("target_width")
            && finalHidden("target_height");
        setWidget(finalNode, "upscale_mode", "按倍数放大");
        setWidget(finalNode, "tiled_sampling", "开");
        setWidget(finalNode, "sample_preview", "开");
        await sleep(450);
        const finalNestedControls = !finalHidden("tile_width")
            && !finalHidden("tile_height")
            && !finalHidden("preview_interval");
        if (!finalSeedVr2Visible || !finalRtxVisible || !finalVosrVisible
            || !finalScaleMode || !finalTargetMode || !finalRepairOnlyMode || !finalNestedControls) {
            throw new Error("Final upscale conditional controls are not showing/hiding correctly");
        }
        if (!approx(finalWidth, finalNode.size?.[0])) throw new Error("Final upscale toggles changed node width");

        setWidget(finalNode, "upscale_device", "GPU（CUDA）");
        setWidget(finalNode, "upscale_precision", "BF16 混合精度");
        setWidget(finalNode, "repair_color_correction", "AdaIN 风格");
        setWidget(finalNode, "repair_quality", "超高质量");
        setWidget(finalNode, "repair_offload_device", "不卸载");
        globalThis.__aicg3dSmokeProgress = "final-prompt";
        const promptData = await Promise.race([
            app.graphToPrompt(),
            sleep(8000).then(() => null),
        ]);
        if (!promptData) throw new Error("graphToPrompt timed out while checking final-upscale enums");
        globalThis.__aicg3dSmokeProgress = "final-prompt-done";
        const finalPromptInputs = promptData?.output?.[String(finalNode.id)]?.inputs || {};
        const finalChineseValuesSerialize = finalPromptInputs.upscale_device === "cuda"
            && finalPromptInputs.upscale_precision === "bf16"
            && finalPromptInputs.repair_color_correction === "adain"
            && finalPromptInputs.repair_quality === "ULTRA"
            && finalPromptInputs.repair_offload_device === "none";
        if (!finalChineseValuesSerialize) {
            throw new Error("Final upscale Chinese menu values did not serialize back to backend enums: " + JSON.stringify({
                upscale_device: finalPromptInputs.upscale_device,
                upscale_precision: finalPromptInputs.upscale_precision,
                repair_color_correction: finalPromptInputs.repair_color_correction,
                repair_quality: finalPromptInputs.repair_quality,
                repair_offload_device: finalPromptInputs.repair_offload_device,
            }));
        }
        setWidget(finalNode, "second_pass", false);
        await sleep(350);
        globalThis.__aicg3dSmokeProgress = "summary";
        const summary = {
            nodes: (graph._nodes || []).length,
            promptFillCount: filled.length,
            promptFillSizeStable: fillSizeStable,
            mediaLibraryWidthStable: widthStableWhileOpen,
            mediaLibraryOpenHeight: sizeOpen[1],
            mediaLibraryClosedHeight: sizeClosed[1],
            smartDramaCanvasRowStable: canvasSizeRowStable,
            sequenceStagePreviewOrdered: stagePreviewOrdered,
            sequenceStagePreviewSingleCard: stagePreviewSingleCard,
            sequenceStagePreviewFullWidth: stagePreviewFullWidth,
            sequenceStagePreviewAspect: stagePreviewAspect,
            sequenceStagePreviewAspectMatches: stagePreviewAspectMatches,
            sequenceStagePreviewResizeStable: stagePreviewResizeStable,
            segmentOnlyOutput: true,
            addNextWorked: countAfterNext === countBeforeNext + 1,
            deleteSegmentWorked: !(graph._nodes || []).includes(added),
            secondPassConditionalUi: true,
            repairEngineConditionalUi: true,
            advancedInputFold: advancedCollapsed && advancedExpanded && advancedClosedAgain,
            advancedInputAutoExpand: advancedAutoExpanded,
            advancedInputSlotOrderStable: advancedFoldSlotStable,
            advancedInputSizeStable: advancedFoldSizeStable,
            advancedCanvasLayoutStable,
            advancedCanvasWidgetY: {
                collapsed: advancedCollapsedCanvasWidgetY,
                expanded: advancedExpandedCanvasWidgetY,
                closed: advancedClosedCanvasWidgetY,
                h3Slot: advancedH3SlotY,
            },
            advancedSamplePreviewLast: previewWidgetIsLast,
            advancedLegacyMigration: legacyMigrationStable,
            finalUpscaleInputsPresent: finalInputsPresent,
            finalUpscaleLabelsChinese: finalLabelsChinese && finalComboLabelsChinese,
            finalUpscaleFoldStable: finalSecondPassFolded,
            finalUpscaleConditionalUi: finalSeedVr2Visible && finalRtxVisible && finalVosrVisible
                && finalScaleMode && finalTargetMode && finalRepairOnlyMode && finalNestedControls,
            finalUpscaleChineseValuesSerialize: finalChineseValuesSerialize,
            finalUpscalePacked: finalPacked,
            finalUpscalePackedStartsCollapsed: finalPackedStartsCollapsed,
            finalUpscaleLinkedInputs: finalInputSlots,
            vueNodesMode: Boolean(document.querySelector(".lg-node") || document.body.className.includes("vue")),
        };
        await sleep(100);
        return summary;
    })()`);

    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const screenshotPath = path.join(os.tmpdir(), "aicg3d-ui-runtime-smoke.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));

    await evaluate(`(async () => {
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const node = (app.graph?._nodes || []).find((item) => String(item.type || "").includes("SequenceSegment"));
        if (!node) throw new Error("No sequence segment available for resource screenshot");
        node.__h3SequenceResourceButton?.click?.();
        await sleep(700);
        app.canvas?.setZoom?.(0.72);
        app.canvas?.centerOnNode?.(node);
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
        await sleep(350);
        return Boolean(node.__h3InlineMediaPanelWidget && node.__h3InlineMediaOpen);
    })()`);
    const resourceScreenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const resourceScreenshotPath = path.join(os.tmpdir(), "aicg3d-ui-runtime-resource.png");
    fs.writeFileSync(resourceScreenshotPath, Buffer.from(resourceScreenshot.data, "base64"));
    await evaluate(`(async () => {
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const node = (app.graph?._nodes || []).find((item) => item.__h3InlineMediaOpen);
        node?.__h3SequenceResourceButton?.click?.();
        await sleep(250);
    })()`);

    await evaluate(`(async () => {
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const node = globalThis.__aicg3dFinalNode;
        if (!node) throw new Error("No final upscale node available for screenshot");
        const toggle = (node.widgets || []).find((item) => item.name === "second_pass");
        if (toggle) {
            toggle.value = false;
            if (toggle._state) toggle._state.value = false;
            toggle.callback?.call(toggle, false);
        }
        await sleep(500);
        app.canvas?.setZoom?.(0.82);
        app.canvas?.centerOnNode?.(node);
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
        await sleep(350);
        return true;
    })()`);
    const finalUpscaleScreenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const finalUpscaleScreenshotPath = path.join(os.tmpdir(), "aicg3d-ui-runtime-final-upscale.png");
    fs.writeFileSync(finalUpscaleScreenshotPath, Buffer.from(finalUpscaleScreenshot.data, "base64"));

    socket.close();
    // Desktop startup can emit unrelated Vite preload and asset-service
    // messages before this plugin runs. Fail only on AICG3D-related errors.
    const relevantErrors = runtimeErrors.filter((message) =>
        /AICG3D|MiniMaxH3|H3Easy|comfyui-AICG3D/i.test(String(message || "")),
    );
    if (relevantErrors.length) {
        throw new Error("AICG3D frontend runtime errors:\n" + relevantErrors.join("\n"));
    }
    report.ignoredUnrelatedConsoleErrors = runtimeErrors.length;
    console.log("PASS AICG3D runtime UI smoke");
    console.log(JSON.stringify(report, null, 2));
    console.log("Screenshot: " + screenshotPath);
    console.log("Resource screenshot: " + resourceScreenshotPath);
    console.log("Final upscale screenshot: " + finalUpscaleScreenshotPath);
    process.exit(0);
}

main().catch((error) => {
    console.error("FAIL AICG3D runtime UI smoke");
    console.error(error?.stack || error);
    process.exit(1);
});
