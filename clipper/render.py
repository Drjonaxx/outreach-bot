from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .captions import build_subs_ass, write_ass
from .models import Clip, Word
from .reframe import VideoInfo, detect_faces, plan_crop, video_filter

FONTS_DIR = Path(__file__).parent / "fonts"
DEFAULT_FONT = "Montserrat ExtraBold"


def keep_ranges(clip: Clip, words: list[Word], max_gap: float = 3.0, pad: float = 0.6) -> list[tuple[float, float]]:
    """Absolute time ranges to keep: the clip's `keep` pieces (or its whole span),
    with silences longer than `max_gap` shortened to 2 * `pad` (jump cuts)."""
    out: list[tuple[float, float]] = []
    for a, b in clip.keep or [[clip.start, clip.end]]:
        inside = [w for w in words if w.start >= a - 0.05 and w.end <= b + 0.05]
        if not max_gap or not inside:
            out.append((a, b))
            continue
        cur = max(a, inside[0].start - pad) if inside[0].start - a > max_gap else a
        for w1, w2 in zip(inside, inside[1:]):
            if w2.start - w1.end > max_gap:
                out.append((cur, w1.end + pad))
                cur = w2.start - pad
        end = min(b, inside[-1].end + pad) if b - inside[-1].end > max_gap else b
        out.append((cur, end))
    return [(s, e) for s, e in out if e - s > 0.05]


def remap(t: float, ranges: list[tuple[float, float]]) -> float:
    """Map an absolute time onto the timeline left after cutting to `ranges`."""
    acc = 0.0
    for s, e in ranges:
        if t < s:
            return acc
        if t <= e:
            return acc + t - s
        acc += e - s
    return acc


def render_clip(
    source: str,
    info: VideoInfo,
    clip: Clip,
    words: list[Word],
    out_path: Path,
    font: str = DEFAULT_FONT,
    hook_seconds: float = 0.0,
    captions: bool = True,
    crf: int = 20,
    max_gap: float = 3.0,
) -> str:
    """Render one vertical clip. Returns the reframing mode used."""
    plan = plan_crop(detect_faces(source, clip.start, clip.end), info)
    graph = video_filter(plan, info)

    ranges = keep_ranges(clip, words, max_gap)
    rel = [(s - clip.start, e - clip.start) for s, e in ranges]
    cut = not (len(rel) == 1 and rel[0][0] <= 0.01 and rel[0][1] >= clip.duration - 0.01)
    loudnorm = "loudnorm=I=-14:TP=-1.5:LRA=11"
    video = "base"
    audio = f"[0:a]{loudnorm}[a]"
    if cut:
        keep = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in rel)
        graph += f";[base]select='{keep}',setpts=N/FRAME_RATE/TB[cut]"
        video = "cut"
        audio = f"[0:a]aselect='{keep}',asetpts=N/SR/TB,{loudnorm}[a]"

    out_dir = out_path.parent
    if captions and clip.subs:
        ass = out_path.with_suffix(".ass")
        ass.write_text(build_subs_ass(
            [{**s, "start": remap(s["start"], ranges), "end": remap(s["end"], ranges)} for s in clip.subs],
            sum(e - s for s, e in ranges), hook=clip.hook, hook_seconds=hook_seconds, font=font,
        ), encoding="utf-8")
    elif captions:
        shown = [
            Word(remap(w.start, ranges), remap(w.end, ranges), w.text)
            for w in words if any(s - 0.05 <= w.start and w.end <= e + 0.05 for s, e in ranges)
        ]
        ass = write_ass(
            out_path.with_suffix(".ass"), shown, 0.0, sum(e - s for s, e in ranges),
            hook=clip.hook, hook_seconds=hook_seconds, font=font,
        )
    if captions:
        # Run ffmpeg from the output dir and pass a bare filename: avoids the
        # escaping mess of drive letters and colons inside filter arguments.
        fonts = out_dir / "_fonts"
        if not fonts.exists():
            shutil.copytree(FONTS_DIR, fonts)
        graph += f";[{video}]ass={ass.name}:fontsdir={fonts.name}[v]"
    else:
        graph += f";[{video}]null[v]"

    maps = ["-map", "[v]"]
    if info.has_audio:
        graph += f";{audio}"
        maps += ["-map", "[a]"]

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{clip.start:.3f}", "-i", str(Path(source).resolve()),
        "-t", f"{clip.duration:.3f}",
        "-filter_complex", graph,
        *maps,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", f"{min(info.fps, 60):.3f}",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart",
        out_path.name,
    ]
    subprocess.run(cmd, check=True, cwd=out_dir)
    return plan.mode


def write_metadata(path: Path, clip: Clip, source_title: str, channel: str, url: str) -> None:
    credit = " — ".join(x for x in (source_title, channel) if x)
    lines = [
        f"TÍTULO: {clip.title}",
        "",
        "DESCRIPCIÓN:",
        clip.description,
    ]
    if credit:
        lines += ["", f"🎙️ Clip de: {credit}"]
    if url:
        lines.append(url)
    lines += ["", " ".join(f"#{t}" for t in clip.hashtags + ["shorts"])]
    lines += ["", f"(score {clip.score}/10 · {clip.duration:.0f}s) {clip.reason}"]
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
