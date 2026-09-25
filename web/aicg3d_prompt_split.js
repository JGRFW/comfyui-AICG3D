/* ==========================================================================
   AICG3D 分段提示词解析 —— 前端交互

   给「AICG3D 分段提示词解析」节点加两件事：
     1. 一个按钮：一键把解析结果填进画布上每个「视频段落」节点。
     2. 自动填入：改了剧本文本，就自动重填一次（可在节点上关掉）。

   解析规则与 prompt_split.py 保持一致。
   ========================================================================== */

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AICG3DPromptSegmentSplit";
/* 一次最多解析并填入多少段。段落节点够多就能一直往后加，这里只留个安全上限。 */
const MAX_SEGMENTS = 64;
const AUTOFILL_DELAY = 400;
const BUTTON_PREFIX = "一键填入全部视频段落";

const MODE_HEADER = "第N段标记";
const MODE_BLANK = "空行分段";
const MODE_DIVIDER = "分隔线 ---";
const MODE_LINE = "每行一段";
const MODE_REGEX = "自定义正则";

const SECONDS_FROM_TEXT = "跟随文本标注";
const SECONDS_FIXED = "固定值";
const SECONDS_KEEP = "不改动";

const HEADER_RE = /^[\s>*#\-—•·]*(?<marker>第\s*(?:[0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*[段幕镜场景节]|(?:镜头|分镜|场景|画面|shot|Shot|SHOT)\s*[0-9]{1,3}|[0-9]{1,3}\s*[.、)）](?=\s|$))(?<tail>.*)$/;
/* 标题后面紧跟空、空白、分隔符、括号时长才算标题；「第一段正文。」这类正文开头不吃字。 */
const LABEL_TAIL_CHARS = " \t：:、,。.-—–)）]】";
const LABEL_TAIL_PREFIXES = ["（", "(", "【", "["];
const SEC_BRACKET_RE = /[（(\[【]\s*(?<sec>[0-9]+(?:\.[0-9]+)?)\s*(?:秒|s|S|sec|Sec|SEC)\s*[)）\]】]/;
const SEC_BARE_RE = /(?<![0-9.])(?<sec>[0-9]+(?:\.[0-9]+)?)\s*秒/;
const SEC_LEADING_RE = /^\s*[（(\[【]\s*[0-9]+(?:\.[0-9]+)?\s*(?:秒|s|S|sec|Sec|SEC)\s*[)）\]】]\s*[：:、,，.。\-—–]?\s*/;
const DIVIDER_RE = /^[ \t]*[-=_*~—]{3,}[ \t]*$/m;
const BLANK_RE = /\n[ \t]*\n+/;

/* 整块标签式段标题：【第1段｜5秒】 / [第2段|6秒] / 【镜头3｜4秒】
   方括号里必须带段标记，所以 【人物说明】 这种普通标注不会被当段标题。 */
const BRACKET_HEADER_RE = /^[\s>*#\-—•·]*(?<label>[【\[［][^】\]］]*[】\]］])(?<rest>.*)$/;
const SEGMENT_MARK_RE = /第\s*(?:[0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*[段幕镜场景节]|(?:镜头|分镜|场景|画面|shot|Shot|SHOT)\s*[0-9]{1,3}/;
/* 标签内的时长：5秒 / 5s / 5 sec。只在这个标签里用，避免正文里的 1920s 被误判。 */
const SEC_LABEL_RE = /(?<![0-9.])(?<sec>[0-9]+(?:\.[0-9]+)?)\s*(?:秒|s|S|sec|Sec|SEC)(?![0-9A-Za-z])/;

/* ---------------------------------------------------------------- 解析工具 */

function normalizeText(text) {
    return String(text ?? "")
        .replace(/[\ufeff\u200b\u200c\u200d\u2060\u00a0\u202a-\u202e]/g, "")
        .replace(/[\u2028\u2029]/g, "\n")
        .replace(/\r\n?/g, "\n");
}

function readSeconds(line) {
    const text = String(line ?? "");
    const match = SEC_BRACKET_RE.exec(text) || SEC_BARE_RE.exec(text);
    if (!match) return null;
    const value = Number(match.groups?.sec);
    return Number.isFinite(value) ? value : null;
}

function cleanBody(text, keepHeader) {
    let value = String(text ?? "").trim();
    if (!keepHeader) {
        let previous = null;
        while (previous !== value) {
            previous = value;
            value = value.replace(SEC_LEADING_RE, "");
        }
    }
    value = value
        .split("\n")
        .map((line) => line.replace(/[ \t]+$/, ""))
        .join("\n")
        .replace(/^\n+|\n+$/g, "")
        .replace(/\n{3,}/g, "\n\n");
    return value.trim();
}

function splitPlain(text, pattern) {
    return String(text ?? "").split(pattern).filter((part) => part && part.trim());
}

function plainBlock(chunk) {
    const lines = String(chunk ?? "").replace(/^\n+|\n+$/g, "").split("\n");
    return { header: "", rest: "", body: lines, seconds: readSeconds(lines[0] ?? "") };
}

function headerMatch(line) {
    const match = HEADER_RE.exec(String(line ?? ""));
    if (!match) return null;
    const tail = match.groups?.tail ?? "";
    if (!tail) return match;
    if (LABEL_TAIL_CHARS.includes(tail[0])) return match;
    if (LABEL_TAIL_PREFIXES.some((prefix) => tail.startsWith(prefix))) return match;
    return null;
}

function headerRest(match) {
    return stripLeadingSeparators(match?.groups?.tail ?? "");
}

function stripLeadingSeparators(text) {
    return String(text ?? "").replace(/^[\s：:、,，.。\-—–)）|\]】]+/, "").trim();
}

/* 是「【第1段｜5秒】」这种整块标签就返回 {label, rest}，否则 null。 */
function bracketedHeader(line) {
    const match = BRACKET_HEADER_RE.exec(String(line ?? ""));
    if (!match || !SEGMENT_MARK_RE.test(match.groups?.label ?? "")) return null;
    return { label: match.groups?.label ?? "", rest: stripLeadingSeparators(match.groups?.rest ?? "") };
}

/* {isHeader, rest, seconds}：整块标签式与「第1段（5秒）」式两种写法都认。 */
function lineHeader(line) {
    const text = String(line ?? "");
    const bracket = bracketedHeader(text);
    if (bracket) {
        const found = SEC_BRACKET_RE.exec(bracket.label) || SEC_LABEL_RE.exec(bracket.label);
        const value = found ? Number(found.groups?.sec) : NaN;
        return { isHeader: true, rest: bracket.rest, seconds: Number.isFinite(value) ? value : null };
    }
    const match = headerMatch(text);
    if (!match) return { isHeader: false, rest: "", seconds: null };
    return { isHeader: true, rest: headerRest(match), seconds: readSeconds(text) };
}

function blocksFromHeaders(text) {
    const lines = String(text).split("\n");
    const marks = [];
    lines.forEach((line, index) => {
        if (lineHeader(line).isHeader) marks.push(index);
    });
    if (!marks.length) return [];
    return marks.map((start, position) => {
        const end = position + 1 < marks.length ? marks[position + 1] : lines.length;
        const header = lines[start];
        const entry = lineHeader(header);
        return {
            header,
            rest: entry.rest,
            body: lines.slice(start + 1, end),
            seconds: entry.seconds,
        };
    });
}

function parsePromptText(text, mode, customRegex, keepHeader, defaultSeconds) {
    const raw = normalizeText(text);
    if (!raw.trim()) return { prompts: [], seconds: [] };

    let blocks = [];
    if (mode === MODE_REGEX && String(customRegex || "").trim()) {
        blocks = splitPlain(raw, new RegExp(customRegex, "m")).map(plainBlock);
    } else if (mode === MODE_HEADER) {
        blocks = blocksFromHeaders(raw);
    } else if (mode === MODE_BLANK) {
        blocks = splitPlain(raw, BLANK_RE).map(plainBlock);
    } else if (mode === MODE_DIVIDER) {
        blocks = splitPlain(raw, DIVIDER_RE).map(plainBlock);
    } else if (mode === MODE_LINE) {
        blocks = raw.split("\n").filter((line) => line.trim()).map(plainBlock);
    } else {
        const headerBlocks = blocksFromHeaders(raw);
        const dividerBlocks = splitPlain(raw, DIVIDER_RE).map(plainBlock);
        // 【第1段｜5秒】这种整块标签本身就够明确，只有一段时也直接采信。
        const singleBracketHeader = headerBlocks.length === 1 && bracketedHeader(headerBlocks[0].header) !== null;
        if (headerBlocks.length >= 2 && headerBlocks.length > dividerBlocks.length) {
            // 段标题比 --- 分得更细，信段标题
            blocks = headerBlocks;
        } else if (dividerBlocks.length >= 2) {
            // --- 是显式分隔线，段数相当或更多时以它为准
            blocks = dividerBlocks;
        } else if (headerBlocks.length >= 2 || singleBracketHeader) {
            blocks = headerBlocks;
        } else {
            const blankBlocks = splitPlain(raw, BLANK_RE).map(plainBlock);
            blocks = blankBlocks.length >= 2 ? blankBlocks : (raw.trim() ? [plainBlock(raw)] : []);
        }
    }

    const prompts = [];
    const seconds = [];
    const fallback = Number(defaultSeconds) || 5;
    let pendingSeconds = null;
    for (const block of blocks) {
        const source = keepHeader && block.header
            ? [block.header, ...block.body].join("\n")
            : [block.rest, ...block.body].join("\n");
        const body = cleanBody(source, keepHeader);
        let value = block.seconds;
        if (!body) {
            // 整块只剩一个标题（下一行本身又是标题），把它标注的时长留给下一块用
            if (value !== null) pendingSeconds = value;
            continue;
        }
        if (value === null) value = pendingSeconds;
        if (value === null) value = readSeconds(body);
        pendingSeconds = null;
        prompts.push(body);
        seconds.push(value === null ? fallback : value);
    }
    return { prompts, seconds };
}

/* ------------------------------------------------------------ 小工具 */

function findWidget(node, name) {
    return (node?.widgets || []).find((widget) => widget?.name === name) || null;
}

function readWidget(node, name, fallback) {
    const widget = findWidget(node, name);
    return widget ? widget.value : fallback;
}

function writeWidget(node, name, value) {
    const widget = findWidget(node, name);
    if (!widget) return false;
    if (widget.value === value) return true;
    widget.value = value;
    try {
        node.onWidgetChanged?.(name, value, undefined, widget);
    } catch (err) {
        /* 节点自己的回调出错不该影响整批填入 */
    }
    return true;
}

/* AICG3D 的提示词框不是普通部件，是节点包自己的 contentEditable 编辑器：
   只写 prompt 部件的值，框里不会刷新；保存时编辑器还会把自己的内容反向覆盖回部件，
   填进去的文字就白填了。包在 domWidget 上留了 setValue（写值 + 重渲染编辑器），
   所以优先走它，没有才退回写部件值。 */
const H3_PROMPT_DOC_PROP = "minimax_h3_prompt_reference_doc";

function writePrompt(node, text) {
    const value = String(text ?? "");
    const domWidget = node?.__h3DomWidget;
    const setter = domWidget?.setValue || domWidget?.options?.setValue;
    if (typeof setter === "function") {
        try {
            setter.call(domWidget, value);
            // 这一段以前用过 @素材 引用时，编辑器会优先按引用文档渲染，忽略刚写的文字；
            // 清掉引用文档再刷一遍，框里才是这次填的内容。
            const doc = node.properties?.[H3_PROMPT_DOC_PROP];
            if (doc && Array.isArray(doc.parts)) {
                delete node.properties[H3_PROMPT_DOC_PROP];
                setter.call(domWidget, value);
            }
            return true;
        } catch (err) {
            /* 退回普通部件写入 */
        }
    }
    return writeWidget(node, "prompt", value);
}

function notify(message, severity = "success") {
    try {
        const toast = app.extensionManager?.toast;
        if (toast?.add) {
            toast.add({ severity, summary: "AICG3D 分段提示词", detail: message, life: 4000 });
            return;
        }
    } catch (err) {
        /* 老前端没有 toast，退回控制台 */
    }
    if (severity === "error") console.warn("[AICG3D 分段提示词] " + message);
    else console.info("[AICG3D 分段提示词] " + message);
}

function buttonOf(node) {
    return (node?.widgets || []).find(
        (widget) => typeof widget?.name === "string" && widget.name.startsWith(BUTTON_PREFIX),
    ) || null;
}

function setButtonLabel(node, count) {
    const button = buttonOf(node);
    if (!button) return;
    button.name = count > 0 ? `${BUTTON_PREFIX}（已填 ${count} 段）` : BUTTON_PREFIX;
}

/* -------------------------------------------------- 找「视频段落」并排好序 */

function isSequenceSegment(node) {
    const className = String(node?.comfyClass || node?.type || "");
    return className.endsWith("SequenceSegment");
}

function getLink(graph, id) {
    const links = graph?.links;
    if (!links) return null;
    if (typeof links.get === "function") return links.get(id) ?? null;
    return links[id] ?? null;
}

function linkField(link, id, index) {
    if (Array.isArray(link)) return link[index];
    if (index === 3) return link.target_id;
    if (index === 4) return link.target_slot;
    return link.id ?? id;
}

/* 本节点唯一那根输出线接到的「视频段落」＝ 从这一段开始往下填。 */
function anchorSegmentNode(node, graph) {
    const out = node?.outputs?.[0];
    if (!out || !out.links) return null;
    for (const linkId of out.links) {
        const link = getLink(graph, linkId);
        if (!link) continue;
        const targetId = linkField(link, linkId, 3);
        const target = graph.getNodeById?.(targetId)
            || (graph._nodes || []).find((item) => item.id === targetId);
        if (isSequenceSegment(target)) return target;
    }
    return null;
}

/* 按 previous_segment 串起来的顺序排段落；断链的、没接线的按画布左右位置兜底。 */
function orderSegmentNodes(graph, anchor) {
    const pool = (graph?._nodes || []).filter(isSequenceSegment);
    const byId = new Map(pool.map((node) => [node.id, node]));
    const next = new Map();
    const prev = new Map();
    const hasPrev = new Set();

    for (const node of pool) {
        const outputs = node.outputs || [];
        const out = outputs.find((slot) => slot?.name === "segment") || outputs[0];
        if (!out || !out.links) continue;
        for (const linkId of out.links) {
            const link = getLink(graph, linkId);
            if (!link) continue;
            const target = byId.get(linkField(link, linkId, 3));
            if (!target || target === node) continue;
            const slot = (target.inputs || [])[linkField(link, linkId, 4)];
            if (!slot || slot.name !== "previous_segment") continue;
            next.set(node.id, target);
            prev.set(target.id, node);
            hasPrev.add(target.id);
        }
    }

    const posX = (node) => Number(node?.pos?.[0] ?? 0);
    const ordered = [];
    const seen = new Set();
    const push = (node) => {
        if (node && !seen.has(node.id)) {
            seen.add(node.id);
            ordered.push(node);
        }
    };

    const heads = pool.filter((node) => !hasPrev.has(node.id)).sort((a, b) => posX(a) - posX(b));

    // 输出线指到了某一段：把它所在那条链的头一段提到最前面，从那里开始填。
    if (anchor) {
        let head = anchor;
        const walked = new Set([anchor.id]);
        while (prev.has(head.id) && !walked.has(prev.get(head.id).id)) {
            head = prev.get(head.id);
            walked.add(head.id);
        }
        const at = heads.indexOf(head);
        if (at > 0) {
            heads.splice(at, 1);
            heads.unshift(head);
        }
    }

    for (const head of heads) {
        let cursor = head;
        while (cursor) {
            push(cursor);
            cursor = next.get(cursor.id);
        }
    }
    pool.slice().sort((a, b) => posX(a) - posX(b)).forEach(push);
    return ordered;
}

/* ------------------------------------------------------------------ 填入 */

function roundSeconds(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 5;
    return Math.round(number * 10) / 10;
}

function randomSeed() {
    return 1 + Math.floor(Math.random() * 4294967294);
}

function fillSegments(node, options = {}) {
    const graph = node?.graph || app.graph;
    if (!graph) return 0;

    const text = readWidget(node, "text", "");
    const mode = readWidget(node, "mode", "自动识别");
    const customRegex = readWidget(node, "custom_regex", "");
    const keepHeader = Boolean(readWidget(node, "keep_header", false));
    const secondsMode = readWidget(node, "seconds_mode", SECONDS_FROM_TEXT);
    const defaultSeconds = Number(readWidget(node, "default_seconds", 5)) || 5;
    const randomizeSeed = Boolean(readWidget(node, "randomize_seed", true));
    const limitRaw = Number(readWidget(node, "max_segments", MAX_SEGMENTS)) || MAX_SEGMENTS;
    const limit = Math.max(1, Math.min(limitRaw, MAX_SEGMENTS));

    let parsed;
    try {
        parsed = parsePromptText(text, mode, customRegex, keepHeader, defaultSeconds);
    } catch (err) {
        notify("解析失败：" + (err?.message || err), "error");
        return 0;
    }
    const prompts = parsed.prompts.slice(0, limit);
    const seconds = parsed.seconds.slice(0, limit);
    if (!prompts.length) {
        notify("没解析出段落，检查「解析方式」或文本里的段标题。", "error");
        return 0;
    }

    const targets = orderSegmentNodes(graph, anchorSegmentNode(node, graph));
    if (!targets.length) {
        notify("画布上没找到「视频段落」节点。", "error");
        return 0;
    }

    const used = Math.min(prompts.length, targets.length);
    for (let index = 0; index < used; index += 1) {
        const target = targets[index];
        writePrompt(target, prompts[index]);
        if (secondsMode !== SECONDS_KEEP) {
            const value = secondsMode === SECONDS_FIXED ? defaultSeconds : seconds[index];
            writeWidget(target, "seconds", roundSeconds(value));
        }
        if (randomizeSeed) writeWidget(target, "seed", randomSeed());
        try {
            target.setSize?.(target.computeSize?.() ?? target.size);
        } catch (err) {
            /* 有些节点自己管尺寸，失败就保持原样 */
        }
        target.setDirtyCanvas?.(true, true);
    }

    graph.setDirtyCanvas?.(true, true);
    try {
        graph.change?.();
    } catch (err) {
        /* 标记工作流已修改失败不影响结果 */
    }

    if (options.silent !== true) {
        const linked = targets.filter((target) => promptTakenByLink(node, target, graph)).length;
        const notes = [`已把 ${used} 段写进「视频段落」节点`];
        if (parsed.prompts.length > prompts.length) {
            notes.push(`解析出 ${parsed.prompts.length} 段，但「解析上限」只有 ${limit}，多的没填（把上限调大就行）`);
        }
        if (prompts.length > targets.length) {
            notes.push(`解析出 ${prompts.length} 段，画布上只有 ${targets.length} 个段落节点，多的没填`);
        }
        if (prompts.length < targets.length) {
            notes.push(`还剩 ${targets.length - prompts.length} 个段落节点没轮到`);
        }
        if (linked) {
            notes.push(`有 ${linked} 段的提示词被别的线接管了（把线删掉就会露出框里的文字）`);
        }
        notify(notes.join("；"), prompts.length === used ? "success" : "warn");
    }
    return used;
}

/* 这一段的提示词框是不是被别人的连线接管了（自己那根线不算）。 */
function promptTakenByLink(parserNode, target, graph) {
    const slot = (target.inputs || []).find((input) => input?.name === "prompt");
    if (!slot || slot.link == null) return false;
    const link = getLink(graph, slot.link);
    if (!link) return false;
    const originId = Array.isArray(link) ? link[1] : (link.origin_id ?? link.source_id);
    return originId !== parserNode.id;
}

function scheduleAutoFill(node) {
    if (!Boolean(readWidget(node, "auto_fill", true))) return;
    if (node.__aicg3dAutoFillTimer) clearTimeout(node.__aicg3dAutoFillTimer);
    node.__aicg3dAutoFillTimer = setTimeout(() => {
        node.__aicg3dAutoFillTimer = null;
        setButtonLabel(node, fillSegments(node, { silent: true }));
    }, AUTOFILL_DELAY);
}

/* ------------------------------------------------------------- 装到节点上 */

function install(node) {
    if (node.__aicg3dPromptSplitInstalled) return;
    node.__aicg3dPromptSplitInstalled = true;

    const button = node.addWidget("button", BUTTON_PREFIX, null, () => {
        setButtonLabel(node, fillSegments(node));
    });
    if (button) {
        button.serialize = false;
        button.tooltip = "按画布上的段落顺序，把每段提示词写进对应的「视频段落」节点。";
    }

    const textWidget = findWidget(node, "text");
    if (textWidget) {
        const original = textWidget.callback;
        textWidget.callback = function aicg3dPromptSplitCallback(...args) {
            const result = original?.apply(this, args);
            scheduleAutoFill(node);
            return result;
        };
    }
}

app.registerExtension({
    name: "AICG3D.PromptSegmentSplit",
    nodeCreated(node) {
        if (node?.comfyClass !== NODE_CLASS && node?.type !== NODE_CLASS) return;
        install(node);
    },
});
