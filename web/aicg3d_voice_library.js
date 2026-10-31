/* ==========================================================================
   AICG3D H3 Character Voice Library
   Six stable role voices for the infinite sequence workflow.
   ========================================================================== */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const VOICE_LIBRARY_CLASS = "MiniMaxH3EasyCharacterVoiceLibrary";
const SEQUENCE_SEGMENT_CLASS = "MiniMaxH3EasySequenceSegment";
const PANEL_HEIGHT = 560;

const DEFAULTS = [
    { id: "girl", name: "女孩", description: "稚嫩清亮的少女童声，音色柔和细腻，吐字清楚，情绪自然，保留轻微呼吸和童声尾音。", language: "Chinese", age: "child", gender: "female", pitch: "high", pace: "natural" },
    { id: "boy", name: "男孩", description: "稚嫩清脆的少年童声，音色明亮有精神，语调自然，情绪变化真实，不做成年人低音。", language: "Chinese", age: "child", gender: "male", pitch: "medium_high", pace: "natural" },
    { id: "heroine", name: "女主角", description: "年轻成年女性声音，清澈温柔，音色细腻稳定，古风台词自然端庄，情绪表达克制而清楚。", language: "Chinese", age: "young_adult", gender: "female", pitch: "medium", pace: "natural" },
    { id: "hero", name: "男主角", description: "年轻成年男性声音，低稳温厚，咬字清晰有力量，情绪推进自然，不夸张吼叫。", language: "Chinese", age: "young_adult", gender: "male", pitch: "low", pace: "natural" },
    { id: "old_woman", name: "老太太", description: "年长女性声音，略带岁月沙哑和轻微气声，语速偏慢，咬字仍然清楚，情绪自然不夸张。", language: "Chinese", age: "elder", gender: "female", pitch: "low", pace: "slow" },
    { id: "old_man", name: "老爷子", description: "年长男性声音，低沉宽厚，带轻微沙哑和岁月感，语速偏慢，威严但自然。", language: "Chinese", age: "elder", gender: "male", pitch: "low", pace: "slow" },
];

const VOICE_DESCRIPTION_PRESETS = [
    { id: "child_female", label: "儿童女声（3～8岁）", age: "child", gender: "female", pitch: "very_high", pace: "natural", text: "幼童女声，年龄约3～8岁，声线稚嫩清脆，音调很高，奶声自然，吐字清楚但不过度成人化，保留孩子呼吸和尾音。" },
    { id: "child_male", label: "儿童男声（3～8岁）", age: "child", gender: "male", pitch: "very_high", pace: "natural", text: "幼童男声，年龄约3～8岁，声音清亮稚嫩，音调高而有活力，不做成年男性低音，保留自然童声语气。" },
    { id: "teen_female", label: "少年女声（13～17岁）", age: "teenager", gender: "female", pitch: "high", pace: "natural", text: "少年女声，年龄约13～17岁，声线清亮轻盈，带青春期少女的自然气息，吐字清楚，情绪真实，不做成熟成年女声。" },
    { id: "teen_male", label: "少年男声（13～17岁）", age: "teenager", gender: "male", pitch: "high", pace: "natural", text: "少年男声，年龄约13～17岁，声音清亮有朝气，音色尚未完全变低，保留少年感和自然呼吸，不做中年男声。" },
    { id: "young_female", label: "青年女声（20～30岁）", age: "young_adult", gender: "female", pitch: "medium", pace: "natural", text: "青年女声，年龄约20～30岁，声音清澈柔和，音色稳定自然，情绪表达细腻，不做童声或老年声。" },
    { id: "young_male", label: "青年男声（20～30岁）", age: "young_adult", gender: "male", pitch: "medium_low", pace: "natural", text: "青年男声，年龄约20～30岁，声音清朗温和，咬字自然有力量，不做低哑老年男声。" },
    { id: "adult_female", label: "成年女声（30～40岁）", age: "adult", gender: "female", pitch: "medium", pace: "natural", text: "成年女声，年龄约30～40岁，音色成熟稳定，清晰温柔，气息自然，具备成年人的沉稳感。" },
    { id: "adult_male", label: "成年男声（30～40岁）", age: "adult", gender: "male", pitch: "low", pace: "natural", text: "成年男声，年龄约30～40岁，声音沉稳厚实，咬字清晰有力量，情绪克制自然，不做少年音。" },
    { id: "middle_female", label: "中年女声（40～55岁）", age: "middle_age", gender: "female", pitch: "low", pace: "slow", text: "中年女声，年龄约40～55岁，声音成熟、略带岁月质感，语速适中，吐字清楚，保留自然中气。" },
    { id: "middle_male", label: "中年男声（40～55岁）", age: "middle_age", gender: "male", pitch: "low", pace: "slow", text: "中年男声，年龄约40～55岁，声音低沉厚实，略带沧桑，语速适中，咬字清楚，不做年轻化处理。" },
    { id: "elder_female", label: "老年女声（60岁以上）", age: "elder", gender: "female", pitch: "very_low", pace: "slow", text: "老年女声，年龄约60岁以上，声音年长、略带沙哑和岁月感，语速偏慢，气息自然，吐字仍清楚。" },
    { id: "elder_male", label: "老年男声（60岁以上）", age: "elder", gender: "male", pitch: "very_low", pace: "slow", text: "老年男声，年龄约60岁以上，声音低沉宽厚，略带沙哑和苍老感，语速偏慢，威严自然。" },
];
const VOICE_DESCRIPTION_TAGS = [
    "稚嫩", "清亮", "奶声", "活泼", "温柔", "清澈", "成熟", "低沉",
    "宽厚", "沙哑", "沧桑", "威严", "语速偏慢", "气息自然", "情绪克制",
    "不做成年人低音", "保留童声", "不夸张",
];
let audioFilesCache = null;
let lastPromptNode = null;
let lastPromptRange = null;

function className(node) {
    return String(node?.comfyClass || node?.type || node?.constructor?.comfyClass || node?.constructor?.type || "");
}

function isVoiceLibraryNode(node) {
    return className(node).includes("CharacterVoiceLibrary");
}

function isSequenceSegmentNode(node) {
    return className(node).includes("SequenceSegment");
}

function isMainH3Node(node) {
    const name = className(node);
    return name === "MiniMaxH3Easy" || name === "AICG3D_H3";
}

function getWidget(node, name) {
    return (node?.widgets || []).find((widget) => widget?.name === name) || null;
}

function promptWidget(node) {
    return getWidget(node, "prompt")
        || getWidget(node, "h3_prompt_mentions")
        || (node?.widgets || []).find((widget) => widget?.type === "customtext" && typeof widget?.options?.getValue === "function")
        || null;
}

function setHiddenWidget(widget) {
    if (!widget) return;
    widget.type = "hidden";
    widget.hidden = true;
    widget.options ||= {};
    widget.options.hidden = true;
    widget.options.canvasOnly = false;
    if (widget._state) {
        widget._state.type = "hidden";
        widget._state.hidden = true;
        widget._state.options ||= {};
        widget._state.options.hidden = true;
        widget._state.options.canvasOnly = false;
    }
}

function defaultState() {
    return {
        version: 1,
        roles: DEFAULTS.map((role, index) => ({
            ...role,
            seat: index + 1,
            mode: "described",
            reference: "",
            reference_start: 0,
            reference_duration: 8,
            picture_index: 0,
            rights_confirmed: false,
        })),
    };
}

function normalizeState(value) {
    if (typeof value === "string") {
        try { value = JSON.parse(value || "{}"); } catch { value = {}; }
    }
    const map = new Map((Array.isArray(value?.roles) ? value.roles : []).map((role) => [String(role?.id || ""), role]));
    return {
        version: 1,
        roles: DEFAULTS.map((fallback, index) => {
            const raw = map.get(fallback.id) || {};
            return {
                ...fallback,
                ...raw,
                id: fallback.id,
                seat: index + 1,
                name: String(raw.name || fallback.name).trim() || fallback.name,
                mode: ["reference", "clone", "cloned"].includes(String(raw.mode || "").toLowerCase()) ? "reference" : "described",
                description: String(raw.description || fallback.description).trim() || fallback.description,
                language: String(raw.language || fallback.language),
                age: String(raw.age || fallback.age),
                gender: String(raw.gender || fallback.gender),
                pitch: String(raw.pitch || fallback.pitch),
                pace: String(raw.pace || fallback.pace),
                reference: String(raw.reference || "").replaceAll("\\", "/"),
                reference_start: Math.max(0, Number(raw.reference_start) || 0),
                reference_duration: Math.max(0, Number(raw.reference_duration) || 0),
                picture_index: Math.max(0, Math.min(9, Math.trunc(Number(raw.picture_index) || 0))),
                rights_confirmed: raw.rights_confirmed === true,
            };
        }),
    };
}

function readState(node) {
    return normalizeState(getWidget(node, "voice_state")?.value || node?.properties?.minimax_h3_character_voice_state || "");
}

function writeState(node, state, notify = true) {
    const value = JSON.stringify(normalizeState(state));
    const widget = getWidget(node, "voice_state");
    if (widget) {
        widget.value = value;
        if (widget._state) widget._state.value = value;
    }
    node.properties ||= {};
    node.properties.minimax_h3_character_voice_state = value;
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
    if (notify) app.graph?.change?.();
}

async function loadAudioFiles(force = false) {
    if (audioFilesCache && !force) return audioFilesCache;
    const response = await api.fetchApi("/aicg3d/api/media?kind=audio");
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload?.error || `HTTP ${response.status}`);
    audioFilesCache = Array.isArray(payload.files) ? payload.files : [];
    return audioFilesCache;
}

function sequenceTargets() {
    return (app.graph?._nodes || []).filter((node) => isSequenceSegmentNode(node) || isMainH3Node(node));
}

function preferredTarget() {
    const targets = sequenceTargets();
    if (lastPromptNode && targets.includes(lastPromptNode)) return lastPromptNode;
    const selected = app.canvas?.selected_nodes || {};
    return targets.find((node) => selected[node.id] || selected[String(node.id)]) || targets[0] || null;
}

function insertToken(node, role) {
    if (!node || !role) return false;
    const token = role.picture_index ? `@角色${role.seat} <Picture ${role.picture_index}>` : `@角色${role.seat}`;
    const editor = node.__h3Editor;
    const widget = promptWidget(node);
    if (!editor) {
        if (!widget) return false;
        const current = String(widget.value || "");
        const nextValue = `${current}${current && !/\s$/.test(current) ? " " : ""}${token} `;
        if (typeof widget?.options?.setValue === "function") widget.options.setValue.call(widget, nextValue);
        else widget.value = nextValue;
        if (widget._state) widget._state.value = widget.value || nextValue;
    } else {
        editor.focus({ preventScroll: true });
        let range = lastPromptNode === node && lastPromptRange && editor.contains(lastPromptRange.startContainer)
            ? lastPromptRange
            : null;
        if (!range) {
            range = document.createRange();
            range.selectNodeContents(editor);
            range.collapse(false);
        }
        range.deleteContents();
        const textNode = document.createTextNode(`${token} `);
        range.insertNode(textNode);
        range.setStartAfter(textNode);
        range.collapse(true);
        const selection = window.getSelection?.();
        selection?.removeAllRanges();
        selection?.addRange(range);
        lastPromptNode = node;
        lastPromptRange = range.cloneRange();
        editor.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: `${token} ` }));
    }
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
    app.graph?.change?.();
    return true;
}

function rememberPromptEditor(event) {
    const editor = event.target?.closest?.(".h3-prompt-editor");
    if (!editor) return;
    const node = (app.graph?._nodes || []).find((candidate) => candidate.__h3Editor === editor);
    if (!node || (!isSequenceSegmentNode(node) && !isMainH3Node(node))) return;
    lastPromptNode = node;
    const selection = window.getSelection?.();
    if (selection?.rangeCount) lastPromptRange = selection.getRangeAt(0).cloneRange();
}

function field(labelText, control) {
    const label = document.createElement("label");
    label.className = "h3-voice-field";
    const caption = document.createElement("span");
    caption.textContent = labelText;
    label.append(caption, control);
    return label;
}

function selectControl(values, labels, selected) {
    const select = document.createElement("select");
    select.innerHTML = values.map((value) => `<option value="${value}" ${String(value) === String(selected) ? "selected" : ""}>${labels[value] || value}</option>`).join("");
    return select;
}

function roleRow(node, state, role, selected) {
    const row = document.createElement("div");
    row.className = `h3-voice-row${selected ? " is-selected" : ""}`;
    const seat = document.createElement("span");
    seat.className = "h3-voice-seat";
    seat.textContent = String(role.seat);
    const name = document.createElement("button");
    name.type = "button";
    name.className = "h3-voice-name";
    name.textContent = role.name;
    name.addEventListener("click", () => {
        node.__h3VoiceSelected = role.id;
        render(node);
    });
    const token = document.createElement("span");
    token.className = "h3-voice-token";
    token.textContent = role.picture_index ? `@角色${role.seat} ← 图${role.picture_index}` : `@角色${role.seat}`;
    const mode = document.createElement("span");
    mode.className = `h3-voice-mode is-${role.mode}`;
    mode.textContent = role.mode === "reference" ? "克隆" : "描述";
    const insert = document.createElement("button");
    insert.type = "button";
    insert.className = "h3-voice-insert";
    insert.textContent = "插入本段";
    insert.addEventListener("pointerdown", (event) => event.stopPropagation());
    insert.addEventListener("click", () => {
        const target = preferredTarget();
        if (!target) {
            globalThis.alert?.("画布上还没有 MiniMax H3 Aicg 视频段落节点");
            return;
        }
        insertToken(target, role);
    });
    row.append(seat, name, token, mode, insert);
    return row;
}

function openUpload(node, state, role) {
    let input = document.querySelector("input.h3-voice-file-input");
    if (!input) {
        input = document.createElement("input");
        input.type = "file";
        input.accept = "audio/*";
        input.className = "h3-voice-file-input";
        input.style.cssText = "position:fixed;left:-10000px;top:0;width:1px;height:1px;opacity:0;pointer-events:none;";
        document.body.append(input);
    }
    input.value = "";
    input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) return;
        try {
            const form = new FormData();
            form.append("image", file, file.name || `voice-${Date.now()}.wav`);
            form.append("type", "input");
            const response = await api.fetchApi("/upload/image", { method: "POST", body: form });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload?.error || `HTTP ${response.status}`);
            const uploadedName = String(payload.name || payload.filename || "").trim();
            const uploadedSubfolder = String(payload.subfolder || "").replaceAll("\\", "/").replace(/^\/+|\/+$/g, "");
            role.reference = uploadedSubfolder ? `${uploadedSubfolder}/${uploadedName}` : uploadedName;
            writeState(node, state);
            await loadAudioFiles(true);
            render(node);
        } catch (error) {
            globalThis.alert?.(`参考音频上传失败：${error?.message || error}`);
        } finally {
            input.value = "";
        }
    };
    input.click();
}

function editorPanel(node, state, role) {
    const panel = document.createElement("div");
    panel.className = "h3-voice-editor";
    const title = document.createElement("div");
    title.className = "h3-voice-editor-title";
    title.textContent = `${role.seat}. ${role.name} · ${role.mode === "reference" ? "克隆音色" : "描述音色"}`;
    panel.append(title);

    const update = (patch, rerender = false) => {
        Object.assign(role, patch);
        writeState(node, state);
        if (rerender) render(node);
    };

    const name = document.createElement("input");
    name.type = "text";
    name.value = role.name;
    name.addEventListener("change", () => update({ name: name.value.trim() || role.name }, true));
    const mode = selectControl(["described", "reference"], { described: "描述音色（可生成固定参考）", reference: "克隆音色（推荐锁定）" }, role.mode);
    mode.addEventListener("change", () => update({ mode: mode.value }, true));
    const pictureValues = Array.from({ length: 10 }, (_, index) => String(index));
    const pictureLabels = Object.fromEntries(pictureValues.map((value) => [value, Number(value) === 0 ? "不绑定画面" : `图像${value}`]));
    const picture = selectControl(pictureValues, pictureLabels, String(role.picture_index || 0));
    picture.addEventListener("change", () => {
        const next = Math.max(0, Math.min(9, Math.trunc(Number(picture.value) || 0)));
        const conflict = next > 0 && state.roles.find((item) => item.id !== role.id && Number(item.picture_index) === next);
        if (conflict) {
            globalThis.alert?.(`图像${next} 已经绑定到 @角色${conflict.seat}，同一张图像不能绑定两个音色。`);
            picture.value = String(role.picture_index || 0);
            return;
        }
        update({ picture_index: next }, true);
    });
    const top = document.createElement("div");
    top.className = "h3-voice-grid is-three";
    top.append(field("角色名", name), field("音色方式", mode), field("绑定画面参考", picture));
    panel.append(top);

    const description = document.createElement("textarea");
    description.rows = 3;
    description.value = role.description;
    description.addEventListener("change", () => update({ description: description.value.trim() || role.description }));

    const descriptionBox = document.createElement("div");
    descriptionBox.className = "h3-voice-description-box";
    const descriptionHeader = document.createElement("div");
    descriptionHeader.className = "h3-voice-description-header";
    const descriptionTitle = document.createElement("span");
    descriptionTitle.textContent = "固定声线描述";
    const templateValues = ["", ...VOICE_DESCRIPTION_PRESETS.map((preset) => preset.id)];
    const templateLabels = Object.fromEntries([
        ["", "选择声线模板…"],
        ...VOICE_DESCRIPTION_PRESETS.map((preset) => [preset.id, preset.label]),
    ]);
    const template = selectControl(templateValues, templateLabels, "");
    template.className = "h3-voice-template-select";
    template.addEventListener("change", () => {
        const preset = VOICE_DESCRIPTION_PRESETS.find((item) => item.id === template.value);
        if (!preset) return;
        description.value = preset.text;
        update({
            description: preset.text,
            age: preset.age,
            gender: preset.gender,
            pitch: preset.pitch,
            pace: preset.pace,
        }, true);
    });
    descriptionHeader.append(descriptionTitle, template);

    const tags = document.createElement("div");
    tags.className = "h3-voice-keyword-tags";
    for (const keyword of VOICE_DESCRIPTION_TAGS) {
        const tag = document.createElement("button");
        tag.type = "button";
        tag.className = "h3-voice-keyword-tag";
        tag.textContent = keyword;
        tag.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const current = description.value.trim();
            const separator = current && !/[，,。；;\s]$/.test(current) ? "，" : "";
            description.value = `${current}${separator}${keyword}`;
            update({ description: description.value });
        });
        tags.append(tag);
    }
    descriptionBox.append(descriptionHeader, description, tags);
    const language = selectControl(["Chinese", "English", "Japanese", "Korean"], { Chinese: "中文", English: "英文", Japanese: "日文", Korean: "韩文" }, role.language);
    language.addEventListener("change", () => update({ language: language.value }));
    const age = selectControl(["auto", "child", "teenager", "young_adult", "adult", "middle_age", "elder"], { auto: "自动识别（按描述）", child: "儿童", teenager: "少年", young_adult: "青年", adult: "成年", middle_age: "中年", elder: "老年" }, role.age);
    age.addEventListener("change", () => {
        const nextAge = age.value;
        const effectivePitch = nextAge === "child" ? "very_high"
            : nextAge === "teenager" ? "high"
            : nextAge === "middle_age" ? "low"
            : nextAge === "elder" ? "very_low"
            : role.pitch;
        update({ age: nextAge, pitch: effectivePitch }, true);
    });
    const gender = selectControl(["female", "male", "neutral"], { female: "女性", male: "男性", neutral: "中性" }, role.gender);
    gender.addEventListener("change", () => update({ gender: gender.value }));
    const pitch = selectControl(["very_low", "low", "medium_low", "medium", "medium_high", "high", "very_high"], { very_low: "很低", low: "偏低", medium_low: "中低", medium: "适中", medium_high: "中高", high: "偏高", very_high: "很高" }, role.pitch);
    pitch.addEventListener("change", () => update({ pitch: pitch.value }));
    const pace = selectControl(["very_slow", "slow", "natural", "fast", "very_fast"], { very_slow: "很慢", slow: "偏慢", natural: "自然", fast: "偏快", very_fast: "很快" }, role.pace);
    pace.addEventListener("change", () => update({ pace: pace.value }));
    const attrs = document.createElement("div");
    attrs.className = "h3-voice-grid is-five";
    attrs.append(field("语言", language), field("年龄", age), field("性别", gender), field("音高", pitch), field("语速", pace));
    if (role.mode !== "reference") {
        panel.append(descriptionBox);
        panel.append(attrs);
    }

    if (role.mode === "reference") {
        const box = document.createElement("div");
        box.className = "h3-voice-reference";
        const audio = document.createElement("select");
        const appendAudioOption = (value, label, selected = false) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = label;
            option.selected = selected;
            audio.append(option);
        };
        appendAudioOption("", "选择 ComfyUI input 音频");
        let foundReference = false;
        for (const file of audioFilesCache || []) {
            const filename = String(file.filename || file.path || "");
            if (!filename) continue;
            const selected = filename === role.reference;
            foundReference ||= selected;
            appendAudioOption(filename, filename, selected);
        }
        if (role.reference && !foundReference) appendAudioOption(role.reference, role.reference, true);
        audio.addEventListener("change", () => update({ reference: audio.value }, true));
        const upload = document.createElement("button");
        upload.type = "button";
        upload.className = "h3-voice-upload";
        upload.textContent = "上传参考音频";
        upload.addEventListener("click", () => openUpload(node, state, role));
        const audioRow = document.createElement("div");
        audioRow.className = "h3-voice-audio-row";
        audioRow.append(audio, upload);
        const start = document.createElement("input");
        start.type = "number"; start.min = "0"; start.step = "0.1"; start.value = String(role.reference_start || 0);
        start.addEventListener("change", () => update({ reference_start: Math.max(0, Number(start.value) || 0) }));
        const duration = document.createElement("input");
        duration.type = "number"; duration.min = "1"; duration.max = "15"; duration.step = "0.1"; duration.value = String(role.reference_duration || 8);
        duration.addEventListener("change", () => update({ reference_duration: Math.max(1, Math.min(15, Number(duration.value) || 8)) }));
        const trim = document.createElement("div");
        trim.className = "h3-voice-grid";
        trim.append(field("从第几秒开始", start), field("截取时长（秒）", duration));
        const rights = document.createElement("label");
        rights.className = "h3-voice-rights";
        const check = document.createElement("input");
        check.type = "checkbox";
        check.checked = Boolean(role.rights_confirmed);
        check.addEventListener("change", () => update({ rights_confirmed: check.checked }));
        rights.append(check, document.createTextNode(" 我确认拥有这段声音的使用权或已获得授权"));
        box.append(field("参考音频（5～15 秒最佳）", audioRow), trim, rights);
        panel.append(box);
    }

    const hint = document.createElement("div");
    hint.className = "h3-voice-hint";
    hint.textContent = role.mode === "reference"
        ? "克隆音色会把参考音频作为 H3 音色锚点；本段仍需至少 1 张图片或视频，单段最多同时使用 3 个克隆角色。"
        : "描述音色会朗读当前“固定声线描述”的原文并生成试听，随后自动保存为 H3 克隆参考。绑定图像后，插入提示词会写成 @角色N <Picture X>。";
    panel.append(hint);
    return panel;
}

function render(node) {
    const panel = node?.__h3VoicePanel;
    if (!panel) return;
    const state = readState(node);
    const selected = state.roles.find((role) => role.id === node.__h3VoiceSelected) || state.roles[0];
    node.__h3VoiceSelected = selected?.id || "";
    panel.textContent = "";
    const header = document.createElement("div");
    header.className = "h3-voice-header";
    const title = document.createElement("div");
    title.className = "h3-voice-title";
    title.textContent = "固定角色音色库";
    const summary = document.createElement("div");
    summary.className = "h3-voice-summary";
    summary.textContent = `6 个角色 · ${state.roles.filter((role) => role.mode === "reference").length} 个克隆`;
    header.append(title, summary);
    const rows = document.createElement("div");
    rows.className = "h3-voice-rows";
    for (const role of state.roles) rows.append(roleRow(node, state, role, role.id === selected?.id));
    panel.append(header, rows, editorPanel(node, state, selected));
    const target = preferredTarget();
    const status = document.createElement("div");
    status.className = "h3-voice-target";
    const targetLabel = target ? (isSequenceSegmentNode(target) ? `视频段落 ${target.id}` : `AICG3D H3 节点 ${target.id}`) : "";
    status.textContent = target ? `插入目标：${targetLabel}` : "画布上还没有可写入提示词的 H3 节点";
    panel.append(status);
}

function installStyles() {
    let style = document.getElementById("h3-character-voice-library-styles");
    if (!style) {
        style = document.createElement("style");
        style.id = "h3-character-voice-library-styles";
        document.head.append(style);
    }
    style.textContent = `
      .h3-voice-panel { display:flex; flex-direction:column; gap:7px; width:100%; height:100%; min-height:0; box-sizing:border-box; padding:9px; border:1px solid #303840; border-radius:6px; background:#20262c; color:#dce5eb; overflow:hidden; }
      .h3-voice-header { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
      .h3-voice-title { font-size:14px; font-weight:700; color:#f2f6f8; }
      .h3-voice-summary,.h3-voice-hint,.h3-voice-target { color:#8ea0ad; font-size:10px; line-height:1.35; }
      .h3-voice-rows { display:flex; flex-direction:column; gap:4px; flex:0 0 auto; }
      .h3-voice-row { display:grid; grid-template-columns:24px minmax(90px,.8fr) minmax(90px,1fr) 44px 76px; align-items:center; gap:6px; min-height:28px; padding:3px 5px; border:1px solid #34414b; border-radius:4px; background:#171d22; }
      .h3-voice-row.is-selected { border-color:#4c9eff; box-shadow:inset 0 0 0 1px rgba(76,158,255,.18); background:#1b2632; }
      .h3-voice-seat { display:grid; place-items:center; width:22px; height:22px; border-radius:50%; background:#2d4f77; color:#cfe8ff; font-weight:700; font-size:10px; }
      .h3-voice-name,.h3-voice-insert,.h3-voice-upload { min-width:0; border:1px solid #40515e; border-radius:4px; background:#26323b; color:#e5edf2; padding:4px 6px; font-size:11px; cursor:pointer; }
      .h3-voice-name { text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .h3-voice-token { color:#6eb7ff; font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .h3-voice-mode { text-align:center; padding:2px 4px; border-radius:9px; font-size:9px; background:#4a3b22; color:#f0c877; }
      .h3-voice-mode.is-reference { background:#1f4b43; color:#8fe2ce; }
      .h3-voice-editor { display:flex; flex:1 1 auto; flex-direction:column; gap:7px; min-height:0; overflow:auto; padding:8px; border-top:1px solid #34414b; background:#181e23; }
      .h3-voice-editor-title { font-weight:700; color:#e9f2f7; font-size:12px; }
      .h3-voice-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px; }
      .h3-voice-grid.is-three { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .h3-voice-grid.is-five { grid-template-columns:repeat(5,minmax(0,1fr)); }
      .h3-voice-field { display:flex; flex-direction:column; gap:3px; min-width:0; color:#9fb0bb; font-size:10px; }
      .h3-voice-field input,.h3-voice-field select,.h3-voice-field textarea { width:100%; box-sizing:border-box; border:1px solid #3b4b57; border-radius:4px; background:#11171b; color:#e4edf2; padding:4px 6px; font-size:11px; }
      .h3-voice-field textarea { resize:vertical; min-height:54px; }
      .h3-voice-description-box { display:flex; flex-direction:column; gap:5px; min-width:0; color:#9fb0bb; font-size:10px; }
      .h3-voice-description-header { display:flex; align-items:center; justify-content:space-between; gap:8px; }
      .h3-voice-description-box textarea { width:100%; box-sizing:border-box; resize:vertical; min-height:54px; border:1px solid #3b4b57; border-radius:4px; background:#11171b; color:#e4edf2; padding:4px 6px; font-size:11px; }
      .h3-voice-template-select { max-width:260px; border:1px solid #4d6580; border-radius:4px; background:#172231; color:#cfe2f7; padding:3px 6px; font-size:10px; }
      .h3-voice-keyword-tags { display:flex; flex-wrap:wrap; gap:4px; max-height:52px; overflow:auto; padding:2px 0; }
      .h3-voice-keyword-tag { border:1px solid #40515e; border-radius:10px; background:#222d35; color:#b9c8d2; padding:2px 6px; font-size:9px; cursor:pointer; }
      .h3-voice-keyword-tag:hover { border-color:#5c86b5; background:#26394b; color:#dcecff; }
      .h3-voice-reference { display:flex; flex-direction:column; gap:7px; padding:7px; border:1px solid #325147; border-radius:5px; background:#17231f; }
      .h3-voice-audio-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:6px; }
      .h3-voice-rights { display:flex; align-items:center; gap:6px; color:#a8bbb2; font-size:10px; }
      .h3-voice-hint { border-left:2px solid #496271; padding-left:7px; }
    `;
}

function setup(node) {
    if (!node || node.__h3VoiceSetup || typeof node.addDOMWidget !== "function") return;
    node.__h3VoiceSetup = true;
    installStyles();
    setHiddenWidget(getWidget(node, "voice_state"));
    const panel = document.createElement("div");
    panel.className = "h3-voice-panel";
    panel.addEventListener("pointerdown", (event) => event.stopPropagation());
    const widget = node.addDOMWidget("h3_character_voice_library", "h3_character_voice_library", panel, {
        serialize: false,
        getMinHeight: () => PANEL_HEIGHT,
    });
    if (!widget) return;
    widget.serialize = false;
    widget.computedHeight = PANEL_HEIGHT;
    widget.options ||= {};
    widget.options.serialize = false;
    widget.options.getMinHeight = () => PANEL_HEIGHT;
    widget.computeLayoutSize = () => ({ minHeight: PANEL_HEIGHT, minWidth: 0 });
    node.__h3VoicePanel = panel;
    if (!String(getWidget(node, "voice_state")?.value || "").trim()) writeState(node, defaultState(), false);
    render(node);
    loadAudioFiles().then(() => render(node)).catch((error) => console.warn("Voice library audio list failed", error));
    if (!node.__h3VoiceInitialSized) {
        node.__h3VoiceInitialSized = true;
        const width = Math.max(620, Number(node.size?.[0]) || 0);
        const height = Math.max(700, Number(node.size?.[1]) || 0);
        if (node.size?.[0] !== width || node.size?.[1] !== height) node.setSize?.([width, height]);
    }
}

app.registerExtension({
    name: "AICG3D.CharacterVoiceLibrary",
    setup() {
        document.addEventListener("focusin", rememberPromptEditor, true);
        document.addEventListener("selectionchange", () => {
            const selection = window.getSelection?.();
            if (!lastPromptNode?.__h3Editor || !selection?.rangeCount) return;
            const range = selection.getRangeAt(0);
            if (lastPromptNode.__h3Editor.contains(range.startContainer)) lastPromptRange = range.cloneRange();
        });
    },
    nodeCreated(node) {
        if (isVoiceLibraryNode(node)) setup(node);
    },
    loadedGraphNode(node) {
        if (isVoiceLibraryNode(node)) setup(node);
    },
});

globalThis.AICG3D_VOICE_LIBRARY = {
    defaultState,
    isMainH3Node,
    normalizeState,
    readState,
    writeState,
    render,
    insertToken,
    preferredTarget,
};
