import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const VOICE_LIBRARY_FRAGMENT = "CharacterVoiceLibrary";
let activeAudio = null;
let activeButton = null;
let activeStopTimer = null;
const observers = new WeakMap();
let sparkStatus = null;
let sparkStatusPromise = null;

function className(node) {
    return String(
        node?.comfyClass
        || node?.type
        || node?.constructor?.comfyClass
        || node?.constructor?.type
        || "",
    );
}

function isVoiceLibraryNode(node) {
    return className(node).includes(VOICE_LIBRARY_FRAGMENT);
}

function voiceState(node) {
    const sharedReader = globalThis.AICG3D_VOICE_LIBRARY?.readState;
    if (typeof sharedReader === "function") return sharedReader(node);
    const widget = (node?.widgets || []).find((item) => item?.name === "voice_state");
    const raw = widget?.value || node?.properties?.minimax_h3_character_voice_state || "{}";
    try {
        return JSON.parse(String(raw));
    } catch {
        return { roles: [] };
    }
}

function selectedRole(node, state) {
    const roles = Array.isArray(state?.roles) ? state.roles : [];
    return roles.find((role) => role?.id === node?.__h3VoiceSelected) || roles[0] || null;
}

function currentRoleState(node, roleId) {
    const state = voiceState(node);
    const role = (state.roles || []).find((item) => item.id === roleId) || state.roles?.[0] || null;
    return { state, role };
}

function clearStopTimer() {
    if (activeStopTimer) clearTimeout(activeStopTimer);
    activeStopTimer = null;
}

function stopPreview() {
    clearStopTimer();
    if (activeAudio) {
        try { activeAudio.pause(); } catch {}
        activeAudio = null;
    }
    if (activeButton) {
        activeButton.textContent = activeButton.dataset.defaultLabel || "试听";
        activeButton = null;
    }
}

function startButton(button, playingLabel) {
    stopPreview();
    activeButton = button;
    button.dataset.defaultLabel ||= button.textContent || "试听";
    button.textContent = playingLabel;
}

function notifyVoice(detail, severity = "success") {
    try {
        const toast = app.extensionManager?.toast;
        if (toast?.add) {
            toast.add({ severity, summary: "AICG3D 角色音色", detail, life: 4500 });
            return;
        }
    } catch {}
    console.info("[AICG3D 角色音色] " + detail);
}

function finishButton(button) {
    clearStopTimer();
    if (activeAudio) {
        const audio = activeAudio;
        activeAudio = null;
        try { audio.pause(); } catch {}
    }
    if (!button) return;
    button.textContent = button.dataset.defaultLabel || "试听";
    if (activeButton === button) activeButton = null;
}

// Spark model status is shared by all voice nodes.
async function getSparkStatus(force = false) {
    if (!force && sparkStatus) return sparkStatus;
    if (!force && sparkStatusPromise) return sparkStatusPromise;
    sparkStatusPromise = api.fetchApi("/aicg3d/api/sparktts/status")
        .then((response) => response.json())
        .then((payload) => {
            sparkStatus = payload;
            return payload;
        })
        .catch((error) => {
            sparkStatus = { installed: false, message: `无法读取 Spark-TTS 状态：${error?.message || error}` };
            return sparkStatus;
        })
        .finally(() => { sparkStatusPromise = null; });
    return sparkStatusPromise;
}

async function generateDescribedVoice(role, button, node, state) {

    startButton(button, "生成中");
    try {
        const modelStatus = await getSparkStatus(true);
        if (!modelStatus.installed) throw new Error(modelStatus.message || "Spark-TTS 模型未安装");
        const response = await api.fetchApi("/aicg3d/api/voice-preview-spark", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(role),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.ok || !payload.url) {
            throw new Error(payload.error || `HTTP ${response.status}`);
        }
        role.mode = "reference";
        role.reference = payload.reference;
        role.reference_start = 0;
        role.reference_duration = 15;
        role.rights_confirmed = true;
        role.reference_source = payload.source || "spark-tts";
        role.preview_voice = payload.voice;
        role.preview_text = payload.text;
        role.preview_rate = payload.rate;
        role.preview_pitch = payload.pitch;
        globalThis.AICG3D_VOICE_LIBRARY?.writeState?.(node, state, true);
        notifyVoice(`已生成 ${payload.voice}，试听文件已固定为 @角色${role.seat} 的 H3 克隆参考。`);

        const audio = new globalThis.Audio(api.apiURL(payload.url));
        activeAudio = audio;
        button.textContent = "停止试听";
        clearStopTimer();
        activeStopTimer = setTimeout(() => finishButton(button), 15000);
        audio.addEventListener("ended", () => finishButton(button), { once: true });
        audio.addEventListener("error", () => finishButton(button), { once: true });
        setTimeout(() => globalThis.AICG3D_VOICE_LIBRARY?.render?.(node), 120);
        await audio.play();
    } catch (error) {
        finishButton(button);
        notifyVoice(`多声线试听生成失败：${error?.message || error}`, "error");
    }
}
function referenceAudioUrl(role) {
    const normalized = String(role?.reference || "").replaceAll("\\", "/").replace(/^\/+/, "");
    if (!normalized) return "";
    const slash = normalized.lastIndexOf("/");
    const filename = slash >= 0 ? normalized.slice(slash + 1) : normalized;
    const subfolder = slash >= 0 ? normalized.slice(0, slash) : "";
    const query = new URLSearchParams({ filename, type: "input", subfolder });
    const path = `/view?${query.toString()}`;
    return typeof api?.apiURL === "function" ? api.apiURL(path) : path;
}

function previewReferenceVoice(role, button) {
    if (activeAudio && activeButton === button) {
        stopPreview();
        return;
    }
    const url = referenceAudioUrl(role);
    if (!url) {
        globalThis.alert?.("请先选择或上传参考音频，再点击试听。");
        return;
    }
    startButton(button, "停止试听");
    const audio = new globalThis.Audio(url);
    activeAudio = audio;
    const start = Math.max(0, Number(role.reference_start) || 0);
    const duration = Math.max(0, Number(role.reference_duration) || 0);
    let end = Number.POSITIVE_INFINITY;
    audio.addEventListener("loadedmetadata", () => {
        const total = Number(audio.duration) || 0;
        const safeStart = total > 0 ? Math.min(start, Math.max(0, total - 0.05)) : start;
        end = duration > 0 ? safeStart + duration : total || Number.POSITIVE_INFINITY;
        clearStopTimer();
        activeStopTimer = setTimeout(() => finishButton(button), Math.max(1200, (end - safeStart) * 1000 + 600));
        try { audio.currentTime = safeStart; } catch {}
        audio.play().catch((error) => {
            console.warn("Reference voice preview failed", error);
            finishButton(button);
        });
    }, { once: true });
    audio.addEventListener("timeupdate", () => {
        if (Number.isFinite(end) && audio.currentTime >= end) {
            finishButton(button);
        }
    });
    audio.addEventListener("ended", () => finishButton(button), { once: true });
    audio.addEventListener("pause", () => {
        if (activeAudio === audio) finishButton(button);
    }, { once: true });
    audio.addEventListener("error", () => finishButton(button), { once: true });
}

function previewRole(role, button, node, state) {
    if (!role) return;
    if (role.mode === "reference") previewReferenceVoice(role, button);
    else generateDescribedVoice(role, button, node, state);
}

function makePreviewButton(label, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "h3-voice-preview";
    if (String(label).includes("清除")) button.classList.add("is-danger");
    if (String(label).includes("应用")) button.classList.add("is-apply");
    button.textContent = label;
    button.addEventListener("pointerdown", (event) => event.stopPropagation());
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        handler(button);
    });
    return button;
}

function isGeneratedVoice(role) {
    return ["spark-tts", "edge-tts"].includes(role?.reference_source)
        || String(role?.reference || "").startsWith("aicg3d_voice_previews/");
}

function applyRoleToPrompt(role, node, state) {
    const target = globalThis.AICG3D_VOICE_LIBRARY?.preferredTarget?.();
    if (!target) {
        notifyVoice("画布上还没有可写入提示词的 AICG3D H3 节点。", "error");
        return;
    }
    const inserted = globalThis.AICG3D_VOICE_LIBRARY?.insertToken?.(target, role);
    if (!inserted) {
        notifyVoice("无法写入提示词，请先打开 11 号主节点或视频段落节点。", "error");
        return;
    }
    const label = String(target.type || target.comfyClass || "").includes("SequenceSegment")
        ? `视频段落 ${target.id}`
        : `AICG3D H3 节点 ${target.id}`;
    notifyVoice(`已将 @角色${role.seat} 应用到 ${label} 的提示词。`);
}

function clearGeneratedVoice(role, node, state) {
    const reference = String(role.reference || "");
    role.mode = "described";
    role.reference = "";
    role.reference_start = 0;
    role.reference_duration = 8;
    role.rights_confirmed = false;
    delete role.reference_source;
    delete role.preview_voice;
    delete role.preview_text;
    delete role.preview_rate;
    delete role.preview_pitch;
    globalThis.AICG3D_VOICE_LIBRARY?.writeState?.(node, state, true);
    globalThis.AICG3D_VOICE_LIBRARY?.render?.(node);
    notifyVoice(`已清除 @角色${role.seat} 的生成音色，可重新调整描述并生成。`);
    if (reference.startsWith("aicg3d_voice_previews/")) {
        api.fetchApi("/aicg3d/api/voice-preview/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reference }),
        }).catch(() => {});
    }
}
function decorateRows(node, panel, state) {
    const rows = [...panel.querySelectorAll(".h3-voice-row")];
    rows.forEach((row, index) => {
        if (row.querySelector(".h3-voice-preview")) return;
        const role = state.roles[index];
        const button = makePreviewButton(role.mode === "reference" ? "试听" : "生成", (target) => {
            const current = currentRoleState(node, role.id);
            previewRole(current.role, target, node, current.state);
        });
        const insert = row.querySelector(".h3-voice-insert");
        row.insertBefore(button, insert || null);
    });
}

function decorateEditor(node, panel, state) {
    const editor = panel.querySelector(".h3-voice-editor");
    if (!editor || editor.querySelector(".h3-voice-preview-actions")) return;
    const role = selectedRole(node, state);
    if (!role) return;
    const generated = isGeneratedVoice(role);
    const actions = document.createElement("div");
    actions.className = "h3-voice-preview-actions";

    if (role.mode === "reference") {
        actions.append(makePreviewButton("试听克隆参考", (target) => {
            const current = currentRoleState(node, role.id);
            previewReferenceVoice(current.role, target);
        }));
    } else {
        actions.append(makePreviewButton("生成 Spark 音色", (target) => {
            const current = currentRoleState(node, role.id);
            generateDescribedVoice(current.role, target, node, current.state);
        }));
    }
    if (generated) {
        actions.append(makePreviewButton("重新生成", (target) => {
            const current = currentRoleState(node, role.id);
            generateDescribedVoice(current.role, target, node, current.state);
        }));
        actions.append(makePreviewButton("清除生成音色", () => {
            const current = currentRoleState(node, role.id);
            clearGeneratedVoice(current.role, node, current.state);
        }));
    }
    actions.append(makePreviewButton("应用到提示词", () => {
        const current = currentRoleState(node, role.id);
        applyRoleToPrompt(current.role, node, current.state);
    }));

    const hint = document.createElement("span");
    if (sparkStatus && !sparkStatus.installed) {
        const missing = document.createElement(sparkStatus.model_dir ? "span" : "a");
        missing.className = "h3-voice-spark-status is-missing";
        missing.textContent = "缺少 Spark-TTS-0.5B 模型 · 点击下载";
        missing.href = sparkStatus.download_url || "https://huggingface.co/SparkAudio/Spark-TTS-0.5B";
        missing.target = "_blank";
        missing.rel = "noopener noreferrer";
        if (sparkStatus.model_dir) missing.textContent = "Spark-TTS 运行依赖缺失 · 查看提示";
        missing.title = sparkStatus.message || "";
        actions.append(missing);
    }
    hint.textContent = generated
        ? `已固定 ${role.preview_voice || "生成音色"}；试听文件就是 H3 参考`
        : role.mode === "reference"
            ? "当前使用手动参考音频；可试听或应用到提示词"
            : "优先用本地 Spark-TTS 朗读固定声线描述，试听后自动固定为 H3 克隆参考";
    actions.append(hint);
    editor.append(actions);
}
function decorate(node) {
    const panel = node?.__h3VoicePanel;
    if (!panel) return;
    const state = voiceState(node);
    if (!Array.isArray(state.roles) || !state.roles.length) return;
    decorateRows(node, panel, state);
    decorateEditor(node, panel, state);
}

function observe(node) {
    const panel = node?.__h3VoicePanel;
    if (!panel || observers.has(panel)) return;
    const observer = new MutationObserver(() => {
        requestAnimationFrame(() => decorate(node));
    });
    observer.observe(panel, { childList: true, subtree: true });
    observers.set(panel, observer);
    decorate(node);
}

function installStyles() {
    let style = document.getElementById("h3-character-voice-preview-styles");
    if (!style) {
        style = document.createElement("style");
        style.id = "h3-character-voice-preview-styles";
        document.head.append(style);
    }
    style.textContent = `
      .h3-voice-row { grid-template-columns:24px minmax(72px,.8fr) minmax(84px,1fr) 42px 50px 72px !important; }
      .h3-voice-preview { min-width:0; border:1px solid #456052; border-radius:4px; background:#20352d; color:#bfe8d6; padding:4px 5px; font-size:10px; cursor:pointer; }
      .h3-voice-preview:hover { background:#29483c; }
      .h3-voice-preview.is-danger { border-color:#8a4d4d; background:#3d2424; color:#efc0c0; }
      .h3-voice-preview.is-apply { border-color:#4b73a7; background:#22344a; color:#cce2ff; }
      .h3-voice-preview-actions { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding-top:2px; }
      .h3-voice-preview-actions > span { color:#8ea0ad; font-size:10px; line-height:1.35; }
      .h3-voice-preview-actions > button { flex:0 0 auto; }
      .h3-voice-spark-status { flex:0 0 auto; font-size:10px; text-decoration:none; padding:3px 6px; border-radius:4px; border:1px solid #765c33; background:#3a2d1d; color:#ffd28a; }
      .h3-voice-spark-status:hover { border-color:#b58a48; background:#493821; }
    `;
}

function watchNode(node, attempts = 40) {
    if (!isVoiceLibraryNode(node)) return;
    if (node.__h3VoicePanel) {
        observe(node);
        return;
    }
    if (attempts <= 0) return;
    setTimeout(() => watchNode(node, attempts - 1), 250);
}

app.registerExtension({
    name: "AICG3D.CharacterVoicePreview",
    setup() {
        installStyles();
        getSparkStatus().then(() => {
            for (const node of app.graph?._nodes || []) decorate(node);
        });
        setTimeout(() => {
            for (const node of app.graph?._nodes || []) {
                watchNode(node);
            }
        }, 800);
    },
    nodeCreated(node) {
        watchNode(node);
    },
    loadedGraphNode(node) {
        watchNode(node);
    },
});

globalThis.AICG3D_VOICE_PREVIEW = {
    decorate,
    previewRole,
    generateDescribedVoice,
    applyRoleToPrompt,
    clearGeneratedVoice,
    referenceAudioUrl,
    previewReferenceVoice,
    stopPreview,
};
