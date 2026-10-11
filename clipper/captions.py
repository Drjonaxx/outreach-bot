"""Animated word-by-word captions as an ASS subtitle file."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Word
from .reframe import OUT_H, OUT_W

HIGHLIGHT = "&H0000E5FF&"  # ASS colours are &HAABBGGRR -> warm yellow
TEXT = "&H00FFFFFF&"


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# Swear word stem -> the letter to star out (F*CK, SH*T, B*TCH).
_SWEARS = re.compile(r"(?i)\b(fu(?=ck)|shi(?=t)|bi(?=tch))(ck|t|tch)(\w*)")
_STARRED = {"fu": 1, "shi": 2, "bi": 1}


def _censor(text: str) -> str:
    def star(m: re.Match) -> str:
        stem, rest, tail = m.groups()
        i = _STARRED[stem.lower()]
        return stem[:i] + "*" + stem[i + 1:] + rest + tail
    return _SWEARS.sub(star, text)


def _clean(text: str) -> str:
    text = re.sub(r"[{}\\]", "", text)
    text = re.sub(r"^[\"'«“]+|[\"'»”,.;:…]+$", "", text)
    return _censor(text).upper()


def group_words(words: list[Word], max_words: int = 3, max_gap: float = 0.6, max_span: float = 1.6) -> list[list[Word]]:
    groups: list[list[Word]] = []
    current: list[Word] = []
    for w in words:
        if current and (
            len(current) >= max_words
            or w.start - current[-1].end > max_gap
            or w.end - current[0].start > max_span
        ):
            groups.append(current)
            current = []
        current.append(w)
        if re.search(r"[.?!…,;:]$", w.text):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _wrap_hook(text: str, max_chars: int = 22) -> str:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return r"\N".join(lines)


def _header(font: str, font_size: int) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUT_W}
PlayResY: {OUT_H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{font_size},{TEXT},{TEXT},&H00000000&,&H80000000&,1,0,0,0,100,100,0,0,1,7,3,2,60,60,560,1
Style: Hook,{font},64,&H00111111&,&H00111111&,&H00FFFFFF&,&H00FFFFFF&,1,0,0,0,100,100,0,0,3,14,0,8,80,80,190,1
Style: Sub,{font},70,{TEXT},{TEXT},&H00000000&,&H80000000&,1,0,0,0,100,100,0,0,1,6,3,2,70,70,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _hook_event(hook: str, hook_seconds: float, duration: float) -> list[str]:
    if not hook:
        return []
    end = duration if hook_seconds <= 0 else min(hook_seconds, duration)
    return [f"Dialogue: 1,{_ts(0)},{_ts(end)},Hook,,0,0,0,,{_wrap_hook(_clean(hook))}"]


def build_ass(
    words: list[Word],
    clip_start: float,
    clip_end: float,
    hook: str = "",
    hook_seconds: float = 0.0,
    font: str = "Montserrat ExtraBold",
    font_size: int = 86,
) -> str:
    """Word-by-word karaoke captions. Word times are absolute; they get shifted to the clip."""
    duration = clip_end - clip_start
    header = _header(font, font_size)
    events = _hook_event(hook, hook_seconds, duration)

    clip_words = [w for w in words if w.start >= clip_start - 0.05 and w.end <= clip_end + 0.05]
    groups = group_words(clip_words)
    for gi, group in enumerate(groups):
        next_start = groups[gi + 1][0].start if gi + 1 < len(groups) else clip_end
        tokens = [_clean(w.text) for w in group]
        for i, w in enumerate(group):
            start = w.start
            end = group[i + 1].start if i + 1 < len(group) else min(w.end + 0.25, next_start)
            if end <= start:
                continue
            parts = [
                (r"{\c" + HIGHLIGHT + r"\fscx108\fscy108}" + tok + r"{\c" + TEXT + r"\fscx100\fscy100}")
                if j == i else tok
                for j, tok in enumerate(tokens)
            ]
            text = " ".join(p for p in parts if p)
            events.append(
                f"Dialogue: 0,{_ts(start - clip_start)},{_ts(end - clip_start)},Cap,,0,0,0,,{text}"
            )
    return header + "\n".join(events) + "\n"


LABEL = "&H007AD2FF&"  # warm yellow-orange for "CHAT:" / "PAPÁ:" speaker tags


def build_subs_ass(
    subs: list[dict],
    duration: float,
    hook: str = "",
    hook_seconds: float = 0.0,
    font: str = "Montserrat ExtraBold",
) -> str:
    """Phrase subtitles (e.g. a translation). `subs` times are already on the clip timeline."""
    events = _hook_event(hook, hook_seconds, duration)
    for s in subs:
        start, end = max(0.0, s["start"]), min(duration, s["end"])
        if end - start < 0.05:
            continue
        text = _censor(re.sub(r"[{}\\]", "", s["text"].strip()))
        label = ""
        m = re.match(r"^([A-ZÁÉÍÓÚÑ]{2,}):\s*", text)
        if m:
            label = r"{\c" + LABEL + "}" + m.group(1) + r":{\c" + TEXT + "} "
            text = text[m.end():]
        body = _wrap_hook(text, max_chars=26)
        events.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Sub,,0,0,0,,{{\\fad(60,0)}}{label}{body}")
    return _header(font, 86) + "\n".join(events) + "\n"


def write_ass(path: Path, *args, **kwargs) -> Path:
    path.write_text(build_ass(*args, **kwargs), encoding="utf-8")
    return path
