"""AICG3D 分段提示词解析：把一整篇分段剧本自动拆开，分别送给每一个「视频段落」节点。

配套 comfyui-AICG3D 的「MiniMax H3 Aicg 无限段落顺序生成」工作流：

    剧本（一整段文字）
        ↓
    【AICG3D 分段提示词解析】 -- 一键填入 --> 视频段落1 / 2 / 3 / ...
        ↓
    提示词、秒数、种子自动填好，画布上不用多拉一根线

两种用法：

1. 一键填入（推荐，不用拉线）
   节点上的按钮「一键填入全部视频段落」会按画布上的段落顺序，
   把每一段写进对应「视频段落」节点的提示词框。
   打开「自动填入」后，改一次剧本文本就自动重填一次。

2. 图内走线（走 API / 队列也一样认）
   本节点只有一路输出「段1提示词」，接到第 1 个「视频段落」的 prompt 输入即可；
   接在哪一段都行，会自动回到那条链的第 1 段再往下排。其余段落仍然靠按钮铺开。
"""

from __future__ import annotations

import re

# 一次最多解析并填入多少段。段落节点够多就能一直往后加，这里只留个安全上限。
MAX_SEGMENTS = 64

MODE_AUTO = "自动识别"
MODE_HEADER = "第N段标记"
MODE_BLANK = "空行分段"
MODE_DIVIDER = "分隔线 ---"
MODE_LINE = "每行一段"
MODE_REGEX = "自定义正则"
SEGMENT_MODES = (MODE_AUTO, MODE_HEADER, MODE_BLANK, MODE_DIVIDER, MODE_LINE, MODE_REGEX)

SECONDS_FROM_TEXT = "跟随文本标注"
SECONDS_FIXED = "固定值"
SECONDS_KEEP = "不改动"
SECONDS_MODES = (SECONDS_FROM_TEXT, SECONDS_FIXED, SECONDS_KEEP)

DEFAULT_SECONDS = 5.0

EXAMPLE_TEXT = """第1段（5秒）
竖屏9:16电影感情绪短片，冷调低饱和，阴天柔光。人物：女主，二十多岁女性，齐肩微卷短发，米白色针织毛衣。
镜头缓慢推近，她抬头看向远处的高楼，霓虹灯在湿润路面上拉出长长的光带。

第2段（5秒）
镜头跟着她走进狭窄的小巷，巷口挂着一盏昏黄的灯泡，墙面斑驳；她停下脚步回头看了一眼来路。

第3段（5秒）
她推开巷子尽头的铁门，天光一下子亮起来，来到开阔的江边；镜头缓缓拉远，画面停在她的背影上。
"""

# 从网页/文档里复制出来时经常夹带的隐形字符
_INVISIBLE = (
    "\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\u00a0",
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
)

_CN_DIGITS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# 段标题：第1段 / 第 1 段（5秒） / 第一段 / 镜头2 / 分镜3 / 场景4 / Shot 5 / 6. / 7、
_HEADER_RE = re.compile(
    r"^[\s>*#\-—•·]*"
    r"(?P<marker>"
    r"第\s*(?:[0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*[段幕镜场景节]"
    r"|(?:镜头|分镜|场景|画面|shot|Shot|SHOT)\s*[0-9]{1,3}"
    r"|[0-9]{1,3}\s*[.、)）](?=\s|$)"
    r")"
    r"(?P<tail>.*)$"
)

# 标题后面紧跟的东西：空、空白、分隔符、括号里的时长 —— 才算“这是个标题”。
# 「第一段正文。」这种句子开头就不当标题，免得把正文里的字吃掉。
_LABEL_TAIL_CHARS = set(" \t：:、,。.-—–)）]】")
_LABEL_TAIL_PREFIXES = ("（", "(", "【", "[")

# 整块标签式段标题： 【第1段｜5秒】 / [第2段|6秒] / 【镜头3｜4秒】
# 方括号里必须带段标记（第N段 / 镜头N …），所以 【人物说明】 这种普通标注不会被当段标题。
_BRACKET_HEADER_RE = re.compile(
    r"^[\s>*#\-—•·]*(?P<label>[【\[［][^】\]］]*[】\]］])(?P<rest>.*)$"
)
_SEGMENT_MARK_RE = re.compile(
    r"第\s*(?:[0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*[段幕镜场景节]"
    r"|(?:镜头|分镜|场景|画面|shot|Shot|SHOT)\s*[0-9]{1,3}"
)
# 标签内的时长：5秒 / 5s / 5 sec。只在标签里用，避免正文里的 1920s 之类被误判。
_SEC_LABEL_RE = re.compile(
    r"(?<![0-9.])(?P<sec>[0-9]+(?:\.[0-9]+)?)\s*(?:秒|s|S|sec|Sec|SEC)(?![0-9A-Za-z])"
)


def _header_match(line):
    match = _HEADER_RE.match(str(line or ""))
    if match is None:
        return None
    tail = match.group("tail") or ""
    if not tail:
        return match
    if tail[0] in _LABEL_TAIL_CHARS or tail.startswith(_LABEL_TAIL_PREFIXES):
        return match
    return None


def _header_rest(match) -> str:
    return _strip_leading_separators(match.group("tail") or "")


def _strip_leading_separators(text: str) -> str:
    return re.sub(r"^[\s：:、,，.。\-—–)）|\]】]+", "", str(text or "")).strip()


def _line_header(line):
    """(是不是段标题, 这一行剩下的正文, 这一行标注的秒数)。

    两种写法都认：

    1. 【第1段｜5秒】 整块标签式（方括号里必须带段标记）
    2. 第1段 / 第 1 段（5秒） / 镜头2 / Shot 3 / 6.
    """
    text = str(line or "")
    bracket = _bracketed_header(text)
    if bracket is not None:
        label, rest = bracket
        found = _SEC_BRACKET_RE.search(label) or _SEC_LABEL_RE.search(label)
        seconds = None
        if found is not None:
            try:
                seconds = float(found.group("sec"))
            except (TypeError, ValueError):
                seconds = None
        return True, rest, seconds
    match = _header_match(text)
    if match is None:
        return False, "", None
    return True, _header_rest(match), _read_seconds(text)


def _bracketed_header(line):
    """是「【第1段｜5秒】」这种整块标签就返回 (标签, 标签后面的正文)，否则 None。"""
    bracket = _BRACKET_HEADER_RE.match(str(line or ""))
    if bracket is None or not _SEGMENT_MARK_RE.search(bracket.group("label") or ""):
        return None
    return bracket.group("label") or "", _strip_leading_separators(bracket.group("rest") or "")

# 带括号的时长：（5秒） (5s) 【5秒】
_SEC_BRACKET_RE = re.compile(
    r"[（(\[【]\s*(?P<sec>[0-9]+(?:\.[0-9]+)?)\s*(?:秒|s|S|sec|Sec|SEC)\s*[)）\]】]"
)
# 裸的时长：5秒 / 12 秒
_SEC_BARE_RE = re.compile(r"(?<![0-9.])(?P<sec>[0-9]+(?:\.[0-9]+)?)\s*秒")
# 段首残留的括号时长，去标题时一并删掉
_SEC_LEADING_RE = re.compile(
    r"^\s*[（(\[【]\s*[0-9]+(?:\.[0-9]+)?\s*(?:秒|s|S|sec|Sec|SEC)\s*[)）\]】]\s*[：:、,，.。\-—–]?\s*"
)
_DIVIDER_RE = re.compile(r"^[ \t]*[-=_*~—]{3,}[ \t]*$", re.M)
_BLANK_RE = re.compile(r"\n[ \t]*\n+")


def normalize_text(text) -> str:
    value = str(text or "")
    for marker in _INVISIBLE:
        value = value.replace(marker, "")
    value = value.replace("\u2028", "\n").replace("\u2029", "\n")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value


def _cn_number(token):
    if not token:
        return None
    token = token.strip()
    if token.isdigit():
        return int(token)
    if token == "十":
        return 10
    if "十" in token:
        head, _, tail = token.partition("十")
        tens = _CN_DIGITS.get(head, 1) if head else 1
        ones = _CN_DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    return _CN_DIGITS.get(token)


def _read_seconds(line):
    text = str(line or "")
    match = _SEC_BRACKET_RE.search(text)
    if match is None:
        match = _SEC_BARE_RE.search(text)
    if match is None:
        return None
    try:
        return float(match.group("sec"))
    except (TypeError, ValueError):
        return None


def _clean_body(text: str, keep_header: bool) -> str:
    value = str(text or "").strip()
    if not keep_header:
        previous = None
        while previous != value:
            previous = value
            value = _SEC_LEADING_RE.sub("", value)
    value = "\n".join(line.rstrip() for line in value.split("\n"))
    value = value.strip("\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _plain_block(chunk: str) -> dict:
    lines = str(chunk or "").strip("\n").split("\n")
    first = lines[0] if lines else ""
    return {"header": "", "rest": "", "body": lines, "seconds": _read_seconds(first)}


def _blocks_from_headers(text: str) -> list:
    lines = text.split("\n")
    entries = [_line_header(line) for line in lines]
    marks = [index for index, entry in enumerate(entries) if entry[0]]
    if not marks:
        return []
    blocks = []
    for position, start in enumerate(marks):
        end = marks[position + 1] if position + 1 < len(marks) else len(lines)
        _is_header, rest, seconds = entries[start]
        blocks.append({
            "header": lines[start],
            "rest": rest,
            "body": lines[start + 1:end],
            "seconds": seconds,
        })
    return blocks


def _split_plain(text: str, pattern) -> list:
    parts = pattern.split(text)
    return [part for part in parts if part and part.strip()]


def parse_prompt_text(
    text,
    mode: str = MODE_AUTO,
    custom_regex: str = "",
    keep_header: bool = False,
    default_seconds: float = DEFAULT_SECONDS,
):
    """把一整段文本拆成 (每段提示词, 每段秒数)，不截断。"""

    raw = normalize_text(text)
    if not raw.strip():
        return [], []

    blocks = []

    if mode == MODE_REGEX and str(custom_regex or "").strip():
        blocks = [_plain_block(part) for part in _split_plain(raw, re.compile(custom_regex, re.M))]
    elif mode == MODE_HEADER:
        blocks = _blocks_from_headers(raw)
    elif mode == MODE_BLANK:
        blocks = [_plain_block(part) for part in _split_plain(raw, _BLANK_RE)]
    elif mode == MODE_DIVIDER:
        blocks = [_plain_block(part) for part in _split_plain(raw, _DIVIDER_RE)]
    elif mode == MODE_LINE:
        blocks = [_plain_block(line) for line in raw.split("\n") if line.strip()]
    else:
        header_blocks = _blocks_from_headers(raw)
        divider_blocks = [_plain_block(part) for part in _split_plain(raw, _DIVIDER_RE)]
        # 【第1段｜5秒】这种整块标签本身就够明确，只有一段时也直接采信。
        single_bracket_header = (
            len(header_blocks) == 1
            and _bracketed_header(header_blocks[0]["header"]) is not None
        )
        if len(header_blocks) >= 2 and len(header_blocks) > len(divider_blocks):
            # 段标题比 --- 分得更细，信段标题
            blocks = header_blocks
        elif len(divider_blocks) >= 2:
            # --- 是显式分隔线，段数相当或更多时以它为准
            blocks = divider_blocks
        elif len(header_blocks) >= 2 or single_bracket_header:
            blocks = header_blocks
        else:
            blank_blocks = [_plain_block(part) for part in _split_plain(raw, _BLANK_RE)]
            if len(blank_blocks) >= 2:
                blocks = blank_blocks
            else:
                blocks = [_plain_block(raw)] if raw.strip() else []

    prompts = []
    seconds = []
    pending_seconds = None
    for block in blocks:
        if keep_header and block["header"]:
            body = _clean_body("\n".join([block["header"]] + list(block["body"])), True)
        else:
            body = _clean_body("\n".join([block["rest"]] + list(block["body"])), False)
        value = block["seconds"]
        if not body:
            # 整块只剩一个标题（下一行本身又是标题），说明它其实是上一段的标题行：
            # 把它标注的时长留给下一块用，本身不出段。
            if value is not None:
                pending_seconds = value
            continue
        if value is None:
            value = pending_seconds
        if value is None:
            value = _read_seconds(body)
        pending_seconds = None
        prompts.append(body)
        seconds.append(float(value if value is not None else default_seconds))
    return prompts, seconds


def split_prompt_text(
    text,
    mode: str = MODE_AUTO,
    custom_regex: str = "",
    keep_header: bool = False,
    default_seconds: float = DEFAULT_SECONDS,
    limit: int = MAX_SEGMENTS,
):
    prompts, seconds = parse_prompt_text(
        text, mode=mode, custom_regex=custom_regex,
        keep_header=keep_header, default_seconds=default_seconds,
    )
    cap = max(1, min(int(limit or MAX_SEGMENTS), MAX_SEGMENTS))
    return prompts[:cap], seconds[:cap]


class AICG3DPromptSegmentSplit:
    """分段提示词解析：一段文本进，每段提示词分别出。"""

    CATEGORY = "AICG3D/H3 工作流"
    FUNCTION = "run"
    OUTPUT_NODE = False

    # 只留一路输出：接不接都行，接了就是「第一段走线、其余段落一键填」。
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("段1提示词",)
    DESCRIPTION = (
        "把一整篇分段剧本（第1段 / 第2段）自动拆开，再一段一段填进画布上的「视频段落」节点。"
        "节点上的「一键填入全部视频段落」按钮会把结果直接写进画布上每个「MiniMax H3 Aicg 视频段落」节点，"
        "不用手动拉线；打开「自动填入」后改文本就自动重填。"
        "唯一那根「段1提示词」输出接不接都不影响按钮；接上就相当于第一段走线、后面几段照旧一键填。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": EXAMPLE_TEXT,
                        "tooltip": "整篇分段剧本。段标题支持 第1段 / 第一段 / 镜头2 / Shot 3 / 4. 等写法。",
                    },
                ),
                "mode": (
                    list(SEGMENT_MODES),
                    {
                        "default": MODE_AUTO,
                        "tooltip": "自动识别：先找段标题，其次 --- 分隔线，其次空行，都没有就整段当一段。",
                    },
                ),
                "custom_regex": (
                    "STRING",
                    {"multiline": False, "default": "", "tooltip": "解析方式选「自定义正则」时才生效。"},
                ),
                "keep_header": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "开 = 「第1段（5秒）」这种标题也留在提示词里；关 = 自动删掉标题和段首时长。",
                    },
                ),
                "seconds_mode": (
                    list(SECONDS_MODES),
                    {
                        "default": SECONDS_FROM_TEXT,
                        "tooltip": "一键填入时秒数怎么写：跟随文本标注 / 全部用固定值 / 完全不碰秒数。",
                    },
                ),
                "default_seconds": (
                    "FLOAT",
                    {"default": DEFAULT_SECONDS, "min": 1.0, "max": 60.0, "step": 0.1},
                ),
                "auto_fill": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "开 = 改动上面的文本后，自动重填画布上的每个「视频段落」节点。"},
                ),
                "randomize_seed": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "一键填入时给每段换一个随机种子，避免各段画面太像。"},
                ),
                "max_segments": (
                    "INT",
                    {"default": MAX_SEGMENTS, "min": 1, "max": MAX_SEGMENTS, "step": 1},
                ),
            },
        }

    def run(
        self,
        text,
        mode,
        custom_regex,
        keep_header,
        seconds_mode,
        default_seconds,
        auto_fill=True,
        randomize_seed=True,
        max_segments=MAX_SEGMENTS,
    ):
        del auto_fill, randomize_seed, seconds_mode  # 只给界面按钮用，走线时不影响

        try:
            prompts, seconds = parse_prompt_text(
                text,
                mode=mode,
                custom_regex=custom_regex,
                keep_header=bool(keep_header),
                default_seconds=float(default_seconds or DEFAULT_SECONDS),
            )
        except re.error as exc:
            raise ValueError("自定义正则写错了：{}".format(exc)) from exc

        if not prompts:
            raise ValueError(
                "没解析出任何段落。检查「解析方式」，或者把文本写成「第1段 / 第2段 …」这样带标记的形式。"
            )

        cap = max(1, min(int(max_segments or MAX_SEGMENTS), MAX_SEGMENTS))
        if len(prompts) > cap:
            print(
                "[AICG3D 分段提示词解析] 解析出 {} 段，本次只输出前 {} 段（「解析上限」最多 {} 段）。".format(
                    len(prompts), cap, MAX_SEGMENTS
                )
            )
        # 只把第一段交给输出；其余段落由节点上的「一键填入全部视频段落」按钮铺开。
        return (prompts[0],)


NODE_CLASS_MAPPINGS = {
    "AICG3DPromptSegmentSplit": AICG3DPromptSegmentSplit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AICG3DPromptSegmentSplit": "AICG3D 分段提示词解析",
}
