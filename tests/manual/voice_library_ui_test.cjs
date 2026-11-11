/* Copyright (C) 2026 AICG3D
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Inspect the Character Voice Library DOM widget at desktop and narrow widths.
 * Start Edge with --remote-debugging-port=9223 before running this test.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const CDP_PORT = Number(process.env.AICG3D_CDP_PORT || 9223);
const COMFY_URL = process.env.AICG3D_COMFY_URL || "http://127.0.0.1:8188/";
const CDP_TARGET_ID = String(process.env.AICG3D_CDP_TARGET_ID || "").trim();
const FORCE_RELOAD = process.env.AICG3D_UI_FORCE_RELOAD === "1";

async function main() {
    const list = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`).then((r) => r.json());
    const pages = list.filter((item) => item.type === "page" && item.webSocketDebuggerUrl);
    const target = CDP_TARGET_ID
        ? pages.find((item) => String(item.id || "") === CDP_TARGET_ID)
        : pages.find((item) => String(item.url || "").startsWith(COMFY_URL)) || pages[0];
    if (!target) throw new Error("No CDP page found");

    const socket = new WebSocket(target.webSocketDebuggerUrl);
    const pending = new Map();
    let nextId = 1;
    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        const item = pending.get(message.id);
        if (!item) return;
        pending.delete(message.id);
        if (message.error) item.reject(new Error(message.error.message));
        else item.resolve(message.result);
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
        if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "Evaluation failed");
        return result.result?.value;
    };

    await send("Runtime.enable");
    await send("Page.enable");
    await send("Page.bringToFront");
    await send("Emulation.setDeviceMetricsOverride", {
        width: 1600,
        height: 1100,
        deviceScaleFactor: 1,
        mobile: false,
    });
    let alreadyReady = false;
    try {
        alreadyReady = await evaluate(
            "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && (globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3CharacterVoiceLibrary'] || globalThis.LiteGraph?.registered_node_types?.['MiniMaxH3EasyCharacterVoiceLibrary']))",
        );
    } catch { /* page is not ready yet */ }
    if (!alreadyReady || FORCE_RELOAD) await send("Page.navigate", { url: COMFY_URL });
    for (let attempt = 0; attempt < 100; attempt++) {
        try {
            const ready = await evaluate(
                "Boolean((globalThis.app || globalThis.comfyAPI?.app?.app)?.graph && (globalThis.LiteGraph?.registered_node_types?.['AICG3D_H3CharacterVoiceLibrary'] || globalThis.LiteGraph?.registered_node_types?.['MiniMaxH3EasyCharacterVoiceLibrary']))",
            );
            if (ready) break;
        } catch { /* still loading */ }
        await sleep(250);
    }

    const report = await evaluate(`(async () => {

        const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const app = globalThis.app || globalThis.comfyAPI?.app?.app;
        const graph = app.graph;
        for (const node of [...(graph?._nodes || [])]) graph.remove?.(node);
        await app.loadGraphData({
            last_node_id: 1,
            last_link_id: 0,
            nodes: [{
                id: 1,
                type: "AICG3D_H3CharacterVoiceLibrary",
                pos: [80, 80],
                size: [230, 320],
                flags: {},
                order: 0,
                mode: 0,
                inputs: [],
                outputs: [
                    { name: "voice_cast", type: "AICG3D_CHARACTER_VOICE_CAST", links: [] },
                    { name: "report_json", type: "STRING", links: [] },
                ],
                properties: {},
                widgets_values: [""],
            }],
            links: [],
            groups: [],
            config: {},
            extra: {},
            version: 0.4,
        });
        const node = graph._nodes[0];
        if (!node) throw new Error("Character Voice Library node did not load");
        app.canvas.ds.scale = 1;
        app.canvas.ds.offset = [20, 20];
        app.canvas.setDirty?.(true, true);
        app.canvas.resize?.(1600, 1000);
        const graphCanvas = document.querySelector("#graph-canvas");
        if (graphCanvas?.parentElement) graphCanvas.parentElement.style.height = "1000px";
        if (graphCanvas) graphCanvas.style.height = "1000px";
        const settleNode = async () => {
            app.canvas.centerOnNode?.(node);
            app.canvas.selectNode?.(node, false);
            app.canvas.setDirty?.(true, true);
            app.canvas.draw?.(true, true);
            await sleep(350);
        };
        await settleNode();
        await sleep(1800);

        const inspect = () => {
            const panel = node.__h3VoicePanel;
            const widget = (node.widgets || []).find((item) => item?.name === "h3_character_voice_library");
            const rect = (element) => {
                const box = element?.getBoundingClientRect?.();
                return box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null;
            };
            const ancestors = [];
            let current = panel?.parentElement;
            for (let depth = 0; current && depth < 6; depth++, current = current.parentElement) {
                ancestors.push({
                    tag: current.tagName,
                    className: String(current.className || ""),
                    rect: rect(current),
                    styleWidth: current.style?.width || "",
                    styleHeight: current.style?.height || "",
                });
            }
            const panelCandidates = [...document.querySelectorAll('.h3-voice-panel')].map((candidate) => ({
                connected: candidate.isConnected,
                rect: rect(candidate),
                scrollWidth: candidate.scrollWidth,
                clientWidth: candidate.clientWidth,
            }));
            const visiblePanel = panelCandidates.find((candidate) => (candidate.rect?.width || 0) > 1 && (candidate.rect?.height || 0) > 1) || null;
            return {
                panelCandidates,
                visiblePanel,
                nodeSize: [...(node.size || [])],
                nodeRect: rect(node.htmlElements?.root || node.htmlElements?.dom || node.htmlElements?.element || node.htmlElements?.body),
                widgetType: widget?.type,
                widgetComputedHeight: widget?.computedHeight,
                widgetRect: rect(widget?.element || widget?.inputEl),
                hostWidth: parseFloat(ancestors[0]?.styleWidth || "0") || 0,
                panelRect: visiblePanel?.rect || rect(panel),
                panelScrollWidth: visiblePanel?.scrollWidth ?? panel?.scrollWidth,
                panelClientWidth: visiblePanel?.clientWidth ?? panel?.clientWidth,
                ancestors,
            };
        };

        const desktop = inspect();
        node.setSize?.([820, 900]);
        await settleNode();
        await sleep(900);
        const wide = inspect();
        node.setSize?.([360, 430]);
        await settleNode();
        await sleep(900);
        const narrow = inspect();
        node.setSize?.([120, 160]);
        await settleNode();
        await sleep(900);
        const minimum = inspect();
        node.setSize?.([360, 430]);
        await settleNode();
        await sleep(500);
        const voicePanel = node.__h3VoicePanel;
        const firstSwitch = voicePanel.querySelector('.h3-voice-enable-switch');
        if (!firstSwitch) throw new Error("Voice library enable switch is missing");
        firstSwitch.checked = false;
        firstSwitch.dispatchEvent(new Event("change", { bubbles: true }));
        await sleep(250);
        const enabledWidget = (node.widgets || []).find((item) => item?.name === "enabled");
        const disabledState = {
            widgetValue: enabledWidget?.value,
            panelDisabled: voicePanel.classList.contains("is-disabled"),
            summary: voicePanel.querySelector(".h3-voice-summary")?.textContent || "",
            insertDisabled: voicePanel.querySelector(".h3-voice-insert")?.disabled === true,
        };
        const secondSwitch = voicePanel.querySelector('.h3-voice-enable-switch');
        secondSwitch.checked = true;
        secondSwitch.dispatchEvent(new Event("change", { bubbles: true }));
        await sleep(250);
        const reenabledState = {
            widgetValue: enabledWidget?.value,
            panelDisabled: voicePanel.classList.contains("is-disabled"),
            switchChecked: voicePanel.querySelector('.h3-voice-enable-switch')?.checked === true,
        };
        return {
            desktop,
            wide,
            narrow,
            minimum,
            disabledState,
            reenabledState,
            settingsApi: {
                hasExtensionManager: Boolean(app.extensionManager),
                hasSetting: Boolean(app.extensionManager?.setting),
                hasSet: typeof app.extensionManager?.setting?.set === "function",
                keys: Object.keys(app.extensionManager?.setting || {}),
            },
            vueNodesMode: Boolean(document.querySelector(".lg-node")),
        };
    })()`);

    console.log(JSON.stringify(report, null, 2));
    const diagnosticScreenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const diagnosticPath = path.join(os.tmpdir(), "aicg3d-voice-library-diagnostic.png");
    fs.writeFileSync(diagnosticPath, Buffer.from(diagnosticScreenshot.data, "base64"));
    console.log(`Diagnostic screenshot: ${diagnosticPath}`);
    for (const [name, state] of Object.entries({ desktop: report.desktop, wide: report.wide, narrow: report.narrow })) {
        const expectedWidth = Math.max(280, Number(state.nodeSize?.[0] || 0) - 20);
        if (Number(state.nodeSize?.[0] || 0) < 300 || Number(state.nodeSize?.[1] || 0) < 340) {
            throw new Error(`${name}: voice node collapsed below its usable minimum`);
        }
        if (state.hostWidth > 0 && Math.abs(state.hostWidth - expectedWidth) > 2) {
            throw new Error(`${name}: voice host did not follow the resized node`);
        }
        if (!state.panelRect || state.panelRect.height < 220) {
            throw new Error(`${name}: voice panel lost its usable height`);
        }
        if (Number(state.panelScrollWidth) > Number(state.panelClientWidth) + 2) {
            throw new Error(`${name}: voice panel still has horizontal clipping`);
        }
    }
    if (Math.abs(Number(report.wide.nodeSize?.[0]) - 820) > 1 || Math.abs(Number(report.wide.nodeSize?.[1]) - 900) > 1) {
        throw new Error("Voice node could not be enlarged freely");
    }
    if (Math.abs(Number(report.narrow.nodeSize?.[0]) - 360) > 1 || Math.abs(Number(report.narrow.nodeSize?.[1]) - 430) > 1) {
        throw new Error("Voice node could not be shrunk freely: " + JSON.stringify(report.narrow.nodeSize));
    }
    if (Math.abs(Number(report.minimum.nodeSize?.[0]) - 300) > 1 || Math.abs(Number(report.minimum.nodeSize?.[1]) - 340) > 1) {
        throw new Error("Voice node minimum-size clamp is incorrect: " + JSON.stringify(report.minimum.nodeSize));
    }
    if (report.disabledState.widgetValue !== false
        || !report.disabledState.panelDisabled
        || !String(report.disabledState.summary).includes("已关闭")
        || !report.disabledState.insertDisabled) {
        throw new Error("Voice library switch did not disable the library cleanly");
    }
    if (report.reenabledState.widgetValue !== true
        || report.reenabledState.panelDisabled
        || !report.reenabledState.switchChecked) {
        throw new Error("Voice library switch did not restore the library");
    }
    const expectedHeights = {
        wide: Math.max(230, report.wide.nodeSize[1] - 110),
        narrow: Math.max(230, report.narrow.nodeSize[1] - 110),
        minimum: Math.max(230, report.minimum.nodeSize[1] - 110),
    };
    for (const [name, expectedHeight] of Object.entries(expectedHeights)) {
        if (Math.abs(Number(report[name].widgetComputedHeight) - expectedHeight) > 1) {
            throw new Error(`${name}: voice widget height is ${report[name].widgetComputedHeight}, expected ${expectedHeight}`);
        }
    }
    console.log("PASS Character Voice Library resize and enable switch");
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const screenshotPath = path.join(os.tmpdir(), "aicg3d-voice-library-layout.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    console.log(`Screenshot: ${screenshotPath}`);
    socket.close();
}

main().catch((error) => {
    console.error("FAIL voice library UI", error);
    process.exitCode = 1;
});
