from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .captions import write_ass
from .models import Clip, Word
from .reframe import VideoInfo, detect_faces, plan_crop, video_filter

FONTS_DIR = Path(__file__).parent / "fonts"
DEFAULT_FONT = "Montserrat ExtraBold"


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
) -> str:
    """Render one vertical clip. Returns the reframing mode used."""
    plan = plan_crop(detect_faces(source, clip.start, clip.end), info)
    graph = video_filter(plan, info)

    out_dir = out_path.parent
    if captions:
        ass = write_ass(
            out_path.with_suffix(".ass"), words, clip.start, clip.end,
            hook=clip.hook, hook_seconds=hook_seconds, font=font,
        )
        # Run ffmpeg from the output dir and pass a bare filename: avoids the
        # escaping mess of drive letters and colons inside filter arguments.
        fonts = out_dir / "_fonts"
        if not fonts.exists():
            shutil.copytree(FONTS_DIR, fonts)
        graph += f";[base]ass={ass.name}:fontsdir={fonts.name}[v]"
    else:
        graph += ";[base]null[v]"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{clip.start:.3f}", "-i", str(Path(source).resolve()),
        "-t", f"{clip.duration:.3f}",
        "-filter_complex", graph,
        "-map", "[v]", "-map", "0:a:0?",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
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
    lines += ["", " ".join(f"#{t}" for t in clip.hashtags + ["shorts", "podcast"])]
    lines += ["", f"(score {clip.score}/10 · {clip.duration:.0f}s) {clip.reason}"]
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
