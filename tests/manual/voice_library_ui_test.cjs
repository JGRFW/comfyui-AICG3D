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

async function main() {
    const list = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`).then((r) => r.json());
    const target = list.find((item) => item.type === "page" && String(item.url || "").startsWith(COMFY_URL))
        || list.find((item) => item.type === "page");
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
    if (!alreadyReady) await send("Page.navigate", { url: COMFY_URL });
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
            return {
                nodeSize: [...(node.size || [])],
                nodeRect: rect(node.htmlElements?.root || node.htmlElements?.dom || node.htmlElements?.element || node.htmlElements?.body),
                widgetType: widget?.type,
                widgetComputedHeight: widget?.computedHeight,
                widgetRect: rect(widget?.element || widget?.inputEl),
                panelRect: rect(panel),
                panelScrollWidth: panel?.scrollWidth,
                panelClientWidth: panel?.clientWidth,
                ancestors,
            };
        };

        const desktop = inspect();
        node.setSize?.([820, 900]);
        await sleep(900);
        const wide = inspect();
        node.setSize?.([430, 900]);
        await sleep(900);
        const narrow = inspect();
        return {
            desktop,
            wide,
            narrow,
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
    for (const [name, state] of Object.entries({ desktop: report.desktop, wide: report.wide, narrow: report.narrow })) {
        const expectedWidth = Math.max(620, Number(state.nodeSize?.[0] || 0) - 20);
        if (Number(state.nodeSize?.[0] || 0) < 640 || Number(state.nodeSize?.[1] || 0) < 740) {
            throw new Error(`${name}: legacy node size was restored without the minimum size`);
        }
        if (!state.panelRect || state.panelRect.width + 2 < expectedWidth || state.panelRect.height < 600) {
            throw new Error(`${name}: voice panel was not laid out across the node width`);
        }
        if (Number(state.panelScrollWidth) > Number(state.panelClientWidth) + 2) {
            throw new Error(`${name}: voice panel still has horizontal clipping`);
        }
    }
    console.log("PASS Character Voice Library layout");
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
