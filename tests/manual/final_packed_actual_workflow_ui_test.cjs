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
    || "H:\\Comfy-Desktop\\ComfyUI-Installs\\ComfyUI\\ComfyUI\\user\\default\\workflows\\13.AICG3D_MiniMax H3 无限长视频短剧工作流.json";
const SCREENSHOT_FILE = process.env.AICG3D_UI_SCREENSHOT
    || path.join(os.tmpdir(), "aicg3d-final-packed-actual-workflow.png");
const TIMEOUT_MS = Number(process.env.AICG3D_UI_TIMEOUT_MS || 45000);

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
        + "globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3FinalHighResUpscalePacked'])";
    let ready = false;
    try {
        ready = await evaluate(readyExpression);
    } catch {
        // The page may still be loading.
    }
    if (!ready) await send("Page.navigate", { url: COMFY_URL });
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
    if (!ready) throw new Error("ComfyUI frontend did not register the packed final-upscale node");
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
        const combine = byId(60);
        const upscale = byId(1127);
        if (!combine) throw new Error("Node 60 was not loaded");
        if (!upscale) throw new Error("Node 1127 was not loaded");
        if (combine.type !== "AICG3D_H3FinalSequenceCombine") {
            throw new Error("Node 60 has the wrong class: " + combine.type);
        }
        if (upscale.type !== "AICG3D_H3FinalHighResUpscalePacked") {
            throw new Error("Node 1127 has the wrong class: " + upscale.type);
        }

        const dataInputs = (upscale.inputs || [])
            .filter((input) => input && !input.widget)
            .map((input) => String(input.name || ""));
        if (dataInputs.length !== 1 || dataInputs[0] !== "final_sequence") {
            throw new Error("Packed node does not expose exactly one data input: " + dataInputs.join(","));
        }
        const finalInput = (upscale.inputs || []).find((input) => input?.name === "final_sequence");
        if (!finalInput || finalInput.link == null) throw new Error("Final-sequence data wire is missing");

        const combineOutput = [...(combine.outputs || [])]
            .find((output) => output?.name === "final_sequence");
        if (!combineOutput || !Array.isArray(combineOutput.links) || !combineOutput.links.includes(663)) {
            throw new Error("Final combine is missing the final_sequence output wire");
        }
        if ((graph._nodes || []).some((node) => Number(node.id) === 1128)) {
            throw new Error("The old standalone LoRA node is still present");
        }

        const widthBefore = Number(upscale.size?.[0] || 0);
        const hiddenAdvanced = ["upscale_device", "upscale_precision", "tiled_sampling", "repair_engine", "sample_preview"]
            .every((name) => Boolean(findWidget(upscale, name)?.hidden));
        const advancedToggle = findWidget(upscale, "show_advanced_settings");
        const folded = !advancedToggle || Number(advancedToggle.value) === 0;
        if (!folded || !hiddenAdvanced) {
            throw new Error("Advanced final-upscale controls are not folded by default");
        }
        if (Number(widgetValue(upscale, "steps", 0)) !== 4
            || Number(widgetValue(upscale, "upscale_scale", 0)) !== 1.5
            || Number(widgetValue(upscale, "second_pass_denoise", 0)) !== 0.3
            || widgetValue(upscale, "lock_source_exposure") !== true) {
            throw new Error("Core 720P -> 1.5x final-upscale settings were not preserved");
        }

        app.canvas.ds.scale = 1.15;
        app.canvas.centerOnNode(upscale);
        app.canvas.selectNode?.(upscale, false);
        app.canvas.setDirty?.(true, true);
        app.canvas.draw?.(true, true);
        document.querySelector("#graph-canvas")?.scrollIntoView?.({ block: "center" });
        await sleep(1400);

        advancedToggle.value = true;
        if (advancedToggle._state) advancedToggle._state.value = true;
        advancedToggle.callback?.call(advancedToggle, true);
        await sleep(700);
        const widthExpanded = Number(upscale.size?.[0] || 0);
        if (Math.abs(widthExpanded - 420) > 2 || Math.abs(widthBefore - 420) > 2) {
            throw new Error("Packed node width changed while unfolding settings: " + JSON.stringify({
                widthBefore,
                widthExpanded,
            }));
        }
        const expandedAdvancedVisible = !Boolean(findWidget(upscale, "upscale_device")?.hidden)
            && !Boolean(findWidget(upscale, "repair_engine")?.hidden);

        advancedToggle.value = false;
        if (advancedToggle._state) advancedToggle._state.value = false;
        advancedToggle.callback?.call(advancedToggle, false);
        await sleep(700);
        const collapsedAgain = ["upscale_device", "repair_engine", "sample_preview"]
            .every((name) => Boolean(findWidget(upscale, name)?.hidden));
        if (!expandedAdvancedVisible || !collapsedAgain) {
            throw new Error("Advanced settings did not open and fold cleanly");
        }

        app.canvas.centerOnNode(upscale);
        app.canvas.setDirty?.(true, true);
        app.canvas.draw?.(true, true);
        await sleep(800);
        return {
            vueNodesMode: Boolean(globalThis.LiteGraph?.vueNodesMode),
            nodeType: upscale.type,
            title: upscale.title,
            dataInputs,
            inputLink: finalInput.link,
            widthBefore,
            widthExpanded,
            folded,
            hiddenAdvanced,
            expandedAdvancedVisible,
            collapsedAgain,
            steps: widgetValue(upscale, "steps"),
            upscaleScale: widgetValue(upscale, "upscale_scale"),
            denoise: widgetValue(upscale, "second_pass_denoise"),
            exposureLock: widgetValue(upscale, "lock_source_exposure"),
            size: [...upscale.size],
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
