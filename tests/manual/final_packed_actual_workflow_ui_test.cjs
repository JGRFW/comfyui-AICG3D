/* Copyright (C) 2026 AICG3D
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Load the real 13 workflow in a running ComfyUI page and verify the packed
 * final-upscale node stays compact with one linked input.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

const CDP_PORT = Number(process.env.AICG3D_CDP_PORT || 9223);
const COMFY_URL = process.env.AICG3D_COMFY_URL || "http://127.0.0.1:8188/";
const WORKFLOW_FILE = process.env.AICG3D_WORKFLOW_FILE
    || path.resolve(__dirname, "..", "..", "workflows", "13.AICG3D_MiniMax H3 无限长视频生成工作流1.2.json");
const SCREENSHOT_FILE = process.env.AICG3D_UI_SCREENSHOT
    || path.join(os.tmpdir(), "aicg3d-final-packed-actual-workflow.png");
const TIMEOUT_MS = Number(process.env.AICG3D_UI_TIMEOUT_MS || 45000);
const FORCE_RELOAD = process.env.AICG3D_UI_FORCE_RELOAD === "1";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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
    const workflow = JSON.parse(fs.readFileSync(WORKFLOW_FILE, "utf8"));
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
    await send("Page.bringToFront");
    await send("Network.setCacheDisabled", { cacheDisabled: true });
    await send("Emulation.setDeviceMetricsOverride", {
        width: 1600,
        height: 1100,
        deviceScaleFactor: 1,
        mobile: false,
    });

    const readyExpression =
        "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && globalThis.LiteGraph?.createNode && "
        + "globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3FinalSequenceUpscale'])";
    let ready = false;
    try {
        ready = await evaluate(readyExpression);
    } catch {
        // The page may still be loading.
    }
    if (!ready || FORCE_RELOAD) await send("Page.navigate", { url: COMFY_URL });
    const started = Date.now();
    while (Date.now() - started < TIMEOUT_MS) {
        try {
            if (await evaluate(readyExpression)) {
                ready = true;
                break;
            }
        } catch {
            // The document is still navigating.
        }
        await sleep(250);
    }
    if (!ready) throw new Error("ComfyUI frontend did not register the combined final-upscale node");
    await sleep(1500);

    const workflowExpression = JSON.stringify(workflow);
    const report = await evaluate(`(async () => {
        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const app = globalThis.app || globalThis.comfyAPI?.app?.app;
        const graph = app.graph;
        await app.loadGraphData(${workflowExpression}, true, false);
        await sleep(2200);

        const byId = (id) => (graph._nodes || []).find((node) => Number(node.id) === Number(id));
        const findWidget = (node, name) => (node?.widgets || []).find((item) => item?.name === name);
        const widgetValue = (node, name, fallback = null) => findWidget(node, name)?.value ?? fallback;
        const combined = byId(60);
        if (!combined) throw new Error("Node 60 was not loaded");
        if (combined.type !== "AICG3D_H3FinalSequenceUpscale") {
            throw new Error("Node 60 has the wrong class: " + combined.type);
        }
        if (byId(196)?.type === "AICG3D_H3FinalHighResUpscalePacked") {
            throw new Error("The old standalone final-upscale node is still present");
        }

        const globalNode = (graph._nodes || []).find(
            (node) => node?.type === "AICG3D_H3SequenceGlobal",
        );
        if (!globalNode || globalNode.type !== "AICG3D_H3SequenceGlobal") {
            throw new Error("Smart Drama global node was not loaded");
        }
        const storageDirectory = findWidget(globalNode, "segment_output_directory");
        const cleanupPolicy = findWidget(globalNode, "segment_cleanup_policy");
        if (!storageDirectory || storageDirectory.hidden || !cleanupPolicy || cleanupPolicy.hidden) {
            throw new Error("Smart Drama segment storage controls are missing or hidden");
        }
        if (String(storageDirectory.value || "") !== ""
            || String(cleanupPolicy.value || "") !== "合成后提示删除") {
            throw new Error("Smart Drama segment storage defaults were not preserved");
        }
        const globalSizeBefore = [...(globalNode.size || [])];

        const dataInputs = (combined.inputs || [])
            .filter((input) => input && !input.widget)
            .map((input) => String(input.name || ""));
        if (dataInputs.length !== 1 || dataInputs[0] !== "final_segment") {
            throw new Error("Combined node does not expose exactly one data input: " + dataInputs.join(","));
        }
        const finalInput = (combined.inputs || []).find((input) => input?.name === "final_segment");
        if (!finalInput || finalInput.link == null) throw new Error("Final segment wire is missing");

        const widthBefore = Number(combined.size?.[0] || 0);
        const heightBefore = Number(combined.size?.[1] || 0);
        const composeControls = combined.__h3FinalSequenceComposeControls;
        if (!composeControls?.row || !composeControls?.fullAuto || !composeControls?.manual || !composeControls?.confirm) {
            throw new Error("Final sequence auto/manual compose controls are missing");
        }
        if (combined.properties?.aicg3d_h3_final_sequence_manual_draw === true
            || composeControls.fullAuto.getAttribute("aria-pressed") !== "true"
            || composeControls.manual.getAttribute("aria-pressed") !== "false"
            || composeControls.confirm.hidden !== true) {
            throw new Error("Final sequence mode did not start in automatic mode");
        }

        composeControls.manual.click();
        await sleep(250);
        const manualWidth = Number(combined.size?.[0] || 0);
        const manualHeight = Number(combined.size?.[1] || 0);
        if (combined.properties?.aicg3d_h3_final_sequence_manual_draw !== true
            || composeControls.fullAuto.getAttribute("aria-pressed") !== "false"
            || composeControls.manual.getAttribute("aria-pressed") !== "true"
            || composeControls.confirm.hidden !== false
            || composeControls.confirm.textContent !== "确认合成"
            || Math.abs(manualWidth - widthBefore) > 2
            || Math.abs(manualHeight - heightBefore) > 2) {
            throw new Error("Manual draw mode did not switch cleanly");
        }

        composeControls.fullAuto.click();
        await sleep(250);
        const autoWidth = Number(combined.size?.[0] || 0);
        const autoHeight = Number(combined.size?.[1] || 0);
        if (combined.properties?.aicg3d_h3_final_sequence_manual_draw !== false
            || composeControls.fullAuto.getAttribute("aria-pressed") !== "true"
            || composeControls.manual.getAttribute("aria-pressed") !== "false"
            || composeControls.confirm.hidden !== true
            || Math.abs(autoWidth - widthBefore) > 2
            || Math.abs(autoHeight - heightBefore) > 2) {
            throw new Error("Automatic mode did not restore cleanly");
        }

        const hiddenAdvanced = ["upscale_device", "upscale_precision", "tiled_sampling", "repair_engine", "sample_preview"]
            .every((name) => Boolean(findWidget(combined, name)?.hidden));
        const advancedToggle = findWidget(combined, "show_advanced_settings");
        const folded = !advancedToggle || Number(advancedToggle.value) === 0;
        if (!folded || !hiddenAdvanced) {
            throw new Error("Advanced final-upscale controls are not folded by default");
        }
        if (Number(widgetValue(combined, "steps", 0)) !== 4
            || Number(widgetValue(combined, "upscale_scale", 0)) !== 1.5
            || Number(widgetValue(combined, "second_pass_denoise", 0)) !== 0.3
            || widgetValue(combined, "lock_source_exposure") !== true) {
            throw new Error("Core 720P -> 1.5x final-upscale settings were not preserved");
        }

        app.canvas.ds.scale = 1.15;
        app.canvas.centerOnNode(combined);
        app.canvas.selectNode?.(combined, false);
        app.canvas.setDirty?.(true, true);
        app.canvas.draw?.(true, true);
        document.querySelector("#graph-canvas")?.scrollIntoView?.({ block: "center" });
        await sleep(1400);

        advancedToggle.value = true;
        if (advancedToggle._state) advancedToggle._state.value = true;
        advancedToggle.callback?.call(advancedToggle, true);
        await sleep(700);
        const widthExpanded = Number(combined.size?.[0] || 0);
        if (Math.abs(widthExpanded - widthBefore) > 2) {
            throw new Error("Packed node width changed while unfolding settings: " + JSON.stringify({
                widthBefore,
                widthExpanded,
            }));
        }
        const expandedAdvancedVisible = [
            "upscale_device",
            "upscale_precision",
            "tiled_sampling",
            "repair_engine",
            "sample_preview",
        ].some((name) => !Boolean(findWidget(combined, name)?.hidden));
        const advancedStateAfterOpen = {
            toggleValue: advancedToggle.value,
            upscaleDeviceHidden: Boolean(findWidget(combined, "upscale_device")?.hidden),
            repairEngineHidden: Boolean(findWidget(combined, "repair_engine")?.hidden),
            samplePreviewHidden: Boolean(findWidget(combined, "sample_preview")?.hidden),
        };

        advancedToggle.value = false;
        if (advancedToggle._state) advancedToggle._state.value = false;
        advancedToggle.callback?.call(advancedToggle, false);
        await sleep(700);
        const collapsedAgain = ["upscale_device", "repair_engine", "sample_preview"]
            .every((name) => Boolean(findWidget(combined, name)?.hidden));
        if (!expandedAdvancedVisible || !collapsedAgain) {
            throw new Error(
                "Advanced settings did not open and fold cleanly: "
                + JSON.stringify({ advancedStateAfterOpen, expandedAdvancedVisible, collapsedAgain }),
            );
        }

        composeControls.manual.click();
        await sleep(250);
        app.canvas.centerOnNode(combined);
        app.canvas.setDirty?.(true, true);
        app.canvas.draw?.(true, true);
        await sleep(800);
        const globalSizeAfter = [...(globalNode.size || [])];
        if (Math.abs(Number(globalSizeAfter[0]) - Number(globalSizeBefore[0])) > 2
            || Math.abs(Number(globalSizeAfter[1]) - Number(globalSizeBefore[1])) > 2) {
            throw new Error("Smart Drama global node changed size during the workflow checks");
        }
        return {
            vueNodesMode: Boolean(globalThis.LiteGraph?.vueNodesMode),
            globalNode: {
                type: globalNode.type,
                storageDirectory: storageDirectory.value,
                cleanupPolicy: cleanupPolicy.value,
                sizeBefore: globalSizeBefore,
                sizeAfter: globalSizeAfter,
            },
            nodeType: combined.type,
            title: combined.title,
            dataInputs,
            inputLink: finalInput.link,
            widthBefore,
            heightBefore,
            widthExpanded,
            folded,
            hiddenAdvanced,
            expandedAdvancedVisible,
            collapsedAgain,
            composeMode: {
                automaticDefault: true,
                manualProperty: combined.properties?.aicg3d_h3_final_sequence_manual_draw,
                manualConfirmVisible: composeControls.confirm.hidden === false,
                confirmText: composeControls.confirm.textContent,
                dimensionsStable: Math.abs(manualWidth - widthBefore) <= 2
                    && Math.abs(manualHeight - heightBefore) <= 2
                    && Math.abs(autoWidth - widthBefore) <= 2
                    && Math.abs(autoHeight - heightBefore) <= 2,
            },
            steps: widgetValue(combined, "steps"),
            upscaleScale: widgetValue(combined, "upscale_scale"),
            denoise: widgetValue(combined, "second_pass_denoise"),
            exposureLock: widgetValue(combined, "lock_source_exposure"),
            size: [...combined.size],
        };
    })()`);

    await sleep(500);
    const shot = await send("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: false,
        fromSurface: true,
    });
    fs.writeFileSync(SCREENSHOT_FILE, Buffer.from(shot.data, "base64"));
    if (runtimeErrors.length) {
        const relevantErrors = runtimeErrors.filter((message) =>
            /AICG3D|final_sequence|FinalHighRes|FinalSequence/i.test(String(message)),
        );
        if (relevantErrors.length) {
            throw new Error("AICG3D runtime errors while loading the workflow:\n" + relevantErrors.join("\n"));
        }
    }
    if (!report.expandedAdvancedVisible || !report.collapsedAgain) {
        throw new Error("Advanced settings visibility check failed");
    }
    report.ignoredUnrelatedRuntimeErrors = runtimeErrors.length;
    console.log(JSON.stringify({ ...report, screenshot: SCREENSHOT_FILE }, null, 2));
    socket.close();
}

main().then(
    () => process.exit(0),
    (error) => {
        console.error(error.stack || error.message || String(error));
        process.exit(1);
    },
);
