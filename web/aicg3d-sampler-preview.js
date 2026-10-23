import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { isOwnH3NodeData } from "./aicg3d-core.js";

const SEGMENT_SAMPLER = "MiniMaxH3EasySegmentSampler";

function isSegmentSampler(nodeData) {
    const name = String(nodeData?.name ?? "");
    const normalized = name.startsWith("AICG3D_H3")
        ? `MiniMaxH3Easy${name.slice("AICG3D_H3".length)}`
        : name;
    return normalized === SEGMENT_SAMPLER;
}

function findNode(nodeId) {
    const graph = app.graph;
    return graph?.getNodeById?.(Number(nodeId)) || null;
}

function mountPreview(node) {
    if (node.__a3SamplerPreviewMounted || typeof node.addDOMWidget !== "function") return;
    node.__a3SamplerPreviewMounted = true;

    const root = document.createElement("div");
    root.style.cssText = [
        "position:relative",
        "display:flex",
        "flex-direction:column",
        "gap:6px",
        "padding:8px",
        "min-height:210px",
        "box-sizing:border-box",
        "background:#181818",
        "border:1px solid #3a3a3a",
        "border-radius:6px",
        "overflow:hidden",
    ].join(";");

    const head = document.createElement("div");
    head.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:8px;font:12px sans-serif;color:#ddd;";
    const title = document.createElement("span");
    title.textContent = "模型实时预览";
    title.style.fontWeight = "600";
    const status = document.createElement("span");
    status.textContent = "等待采样";
    status.style.cssText = "color:#999;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
    head.append(title, status);

    const image = document.createElement("img");
    image.alt = "";
    image.style.cssText = "display:none;width:100%;height:170px;object-fit:contain;background:#080808;";
    const video = document.createElement("video");
    video.muted = true;
    video.loop = true;
    video.autoplay = true;
    video.playsInline = true;
    video.style.cssText = "display:none;width:100%;height:170px;object-fit:contain;background:#080808;";
    root.append(head, image, video);

    const domWidget = node.addDOMWidget("a3_model_preview", "preview", root, { serialize: false });
    if (domWidget) {
        domWidget.serialize = false;
        domWidget.type = "aicg3d_model_preview";
    }

    const initialEnabledWidget = node.widgets?.find((widget) => widget?.name === "preview_enabled");
    const syncEnabled = () => {
        const enabledWidget = node.widgets?.find((widget) => widget?.name === "preview_enabled");
        const enabled = enabledWidget ? Boolean(enabledWidget.value) : true;
        root.style.display = enabled ? "flex" : "none";
        node.__a3SamplerPreviewEnabled = enabled;
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
    };

    const wrapEnabledWidget = (enabledWidget) => {
        if (!enabledWidget || enabledWidget.__a3PreviewCallbackWrapped) return;
        const original = enabledWidget.callback;
        enabledWidget.callback = function (...args) {
            const result = original?.apply(this, args);
            syncEnabled();
            return result;
        };
        enabledWidget.__a3PreviewCallbackWrapped = true;
    };
    wrapEnabledWidget(initialEnabledWidget);

    node._a3SamplerPreviewHandler = (data) => {
        if (!node.__a3SamplerPreviewEnabled || !data || typeof data.image !== "string") return;
        const mime = String(data.mime || "image/jpeg");
        const source = `data:${mime};base64,${data.image}`;
        if (mime.startsWith("video/")) {
            image.style.display = "none";
            video.style.display = "block";
            video.src = source;
            video.play().catch(() => {});
        } else {
            video.pause();
            video.style.display = "none";
            image.style.display = "block";
            image.src = source;
        }
        const step = data.step != null ? `${data.step}/${data.total ?? "?"}` : "";
        const size = data.w && data.h ? `${data.w}x${data.h}` : "";
        status.textContent = [step, size].filter(Boolean).join(" · ") || "预览中";
    };

    node.__a3SamplerPreviewWrapToggle = () => wrapEnabledWidget(
        node.widgets?.find((widget) => widget?.name === "preview_enabled")
    );
    node.__a3SamplerPreviewSync = syncEnabled;
    syncEnabled();
}

const pending = new Map();
api.addEventListener("kj_preview_override", (event) => {
    const data = event?.detail;
    if (!data) return;
    const node = findNode(data.node_id);
    if (node?._a3SamplerPreviewHandler) {
        node._a3SamplerPreviewHandler(data);
        return;
    }
    const key = String(data.node_id);
    const queue = pending.get(key) || [];
    queue.push(data);
    if (queue.length > 3) queue.shift();
    pending.set(key, queue);
});

app.registerExtension({
    name: "AICG3D.SegmentSamplerPreview",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!isSegmentSampler(nodeData) || !isOwnH3NodeData(nodeData)) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = originalCreated?.apply(this, args);
            mountPreview(this);
            this.__a3SamplerPreviewWrapToggle?.();
            const queued = pending.get(String(this.id));
            if (queued?.length) {
                for (const item of queued.splice(0)) this._a3SamplerPreviewHandler?.(item);
                pending.delete(String(this.id));
            }
            return result;
        };
        const originalConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = originalConfigure?.apply(this, args);
            mountPreview(this);
            this.__a3SamplerPreviewWrapToggle?.();
            this.__a3SamplerPreviewSync?.();
            return result;
        };
    },
});
