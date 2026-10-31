import { app } from "../../scripts/app.js";

const VOICE_LIBRARY_FRAGMENT = "CharacterVoiceLibrary";
const SEQUENCE_SEGMENT_FRAGMENT = "SequenceSegment";
const PATCH_FLAG = "__AICG3D_VOICE_CAST_SUBMISSION_PATCHED";

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
    const mode = Number(node?.mode ?? 0);
    return mode !== 2 && mode !== 4 && className(node).includes(VOICE_LIBRARY_FRAGMENT);
}

function isSequenceSegmentNode(node) {
    return className(node).includes(SEQUENCE_SEGMENT_FRAGMENT);
}

function isMainH3Node(node) {
    const name = className(node);
    return name === "MiniMaxH3Easy" || name === "AICG3D_H3";
}

function slotIndex(slots, name) {
    return (slots || []).findIndex((slot) => String(slot?.name || "") === name);
}

function findGraphLink(graph, linkId) {
    if (linkId == null) return null;
    const links = graph?.links;
    if (links instanceof Map) return links.get(linkId) || null;
    if (!Array.isArray(links)) return null;
    return links.find((link) => (
        Array.isArray(link)
            ? Number(link[0]) === Number(linkId)
            : Number(link?.id) === Number(linkId)
    )) || null;
}

function linkOriginId(link) {
    if (Array.isArray(link)) return link[1];
    return link?.origin_id ?? link?.originId ?? link?.from_id ?? link?.fromId ?? null;
}

function linkedSource(node, graph, inputName) {
    const index = slotIndex(node?.inputs, inputName);
    if (index < 0) return null;
    const originId = linkOriginId(findGraphLink(graph, node.inputs[index]?.link));
    return originId != null ? graph?.getNodeById?.(Number(originId)) : null;
}

function previousSegment(node, graph) {
    const source = linkedSource(node, graph, "previous_segment");
    return isSequenceSegmentNode(source) ? source : null;
}

function linkedVoiceLibrary(node, graph) {
    const source = linkedSource(node, graph, "voice_cast");
    return isVoiceLibraryNode(source) ? source : null;
}

function voiceLibraryForSegment(node, graph = app.graph) {
    const seen = new Set();
    let current = node;
    while (current && !seen.has(current)) {
        seen.add(current);
        const linked = linkedVoiceLibrary(current, graph);
        if (linked) return linked;
        current = previousSegment(current, graph);
    }

    // Keep the canvas simple: one library is inherited by the whole graph,
    // even when only the first segment has a visible voice_cast socket.
    const libraries = (graph?._nodes || graph?.nodes || []).filter(isVoiceLibraryNode);
    return libraries.length === 1 ? libraries[0] : null;
}

function voiceLibraryForMainNode(node, graph = app.graph) {
    const linked = linkedVoiceLibrary(node, graph);
    if (linked) return linked;
    const libraries = (graph?._nodes || graph?.nodes || []).filter(isVoiceLibraryNode);
    return libraries.length === 1 ? libraries[0] : null;
}

function installSubmissionPatch() {
    if (globalThis[PATCH_FLAG] || typeof app.graphToPrompt !== "function") return;
    globalThis[PATCH_FLAG] = true;
    const original = app.graphToPrompt;
    app.graphToPrompt = async function graphToPromptWithStableVoiceCast() {
        // Remove links left behind after the voice-library node was deleted.
        // graphToPrompt must never serialize a voice_cast input that no longer
        // points to a real CharacterVoiceLibrary node.
        for (const node of app.graph?._nodes || []) {
            if (!isSequenceSegmentNode(node) && !isMainH3Node(node)) continue;
            const index = slotIndex(node.inputs, "voice_cast");
            if (index < 0) continue;
            if (linkedVoiceLibrary(node, node.graph || app.graph)) continue;
            const input = node.inputs?.[index];
            if (input && input.link != null) input.link = null;
        }
        const promptData = await original.apply(this, arguments);
        const output = promptData?.output || {};
        for (const node of app.graph?._nodes || []) {
            const segment = isSequenceSegmentNode(node);
            const mainH3 = isMainH3Node(node);
            if (!segment && !mainH3) continue;
            const promptNode = output[String(node.id)];
            if (!promptNode) continue;
            const source = segment
                ? voiceLibraryForSegment(node, node.graph || app.graph)
                : voiceLibraryForMainNode(node, node.graph || app.graph);
            if (!source || source.id == null) {
                if (promptNode.inputs) delete promptNode.inputs.voice_cast;
                continue;
            }
            promptNode.inputs ||= {};
            // Explicit input on every segment prevents a cached previous
            // segment from reviving an older cast after single-shot redraw.
            promptNode.inputs.voice_cast = [String(source.id), 0];
        }
        return promptData;
    };
}

app.registerExtension({
    name: "AICG3D.CharacterVoiceSequenceBridge",
    setup() {
        installSubmissionPatch();
        for (const delay of [0, 100, 500, 1200]) {
            setTimeout(installSubmissionPatch, delay);
        }
    },
    loadedGraphNode(node) {
        if (isVoiceLibraryNode(node) || isSequenceSegmentNode(node) || isMainH3Node(node)) installSubmissionPatch();
    },
});

globalThis.AICG3D_VOICE_SEQUENCE_BRIDGE = {
    voiceLibraryForSegment,
    voiceLibraryForMainNode,
    installSubmissionPatch,
};
