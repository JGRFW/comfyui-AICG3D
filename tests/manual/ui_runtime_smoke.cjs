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

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function selectTarget() {
    const response = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`);
    if (!response.ok) throw new Error(`CDP target list failed: ${response.status}`);
    const targets = await response.json();
    const pages = targets.filter((item) => item.type === "page" && item.webSocketDebuggerUrl);
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
            throw new Error(result.exceptionDetails.text || "Runtime.evaluate failed");
        }
        return result.result?.value;
    };

    await send("Runtime.enable");
    await send("Page.enable");
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
    if (!alreadyReady) await send("Page.navigate", { url: COMFY_URL });

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

    const report = await evaluate(`(async () => {
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

        const standalone = create("AICG3D_H3SequenceSegment", [40, 1260]);
        await sleep(600);
        standalone.size = [430, 610];
        standalone.setSize?.([430, 610]);
        const countBeforeNext = (graph._nodes || []).length;
        const idsBeforeNext = new Set((graph._nodes || []).map((node) => node.id));
        standalone.__h3SequenceNextButton?.click?.();
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

        const summary = {
            nodes: (graph._nodes || []).length,
            promptFillCount: filled.length,
            promptFillSizeStable: fillSizeStable,
            mediaLibraryWidthStable: widthStableWhileOpen,
            mediaLibraryOpenHeight: sizeOpen[1],
            mediaLibraryClosedHeight: sizeClosed[1],
            addNextWorked: countAfterNext === countBeforeNext + 1,
            deleteSegmentWorked: !(graph._nodes || []).includes(added),
            secondPassConditionalUi: true,
            repairEngineConditionalUi: true,
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
    process.exit(0);
}

main().catch((error) => {
    console.error("FAIL AICG3D runtime UI smoke");
    console.error(error?.stack || error);
    process.exit(1);
});
