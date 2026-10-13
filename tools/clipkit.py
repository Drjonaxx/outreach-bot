"""Helpers for picking clips by hand (or by Claude) from a transcript.

    python tools/clipkit.py lines TRANSCRIPT > lines.txt
        Transcript as short timestamped lines, for reading.

    python tools/clipkit.py cues TRANSCRIPT SPANS.json KEEP_OUT.json
        SPANS.json: {"name": [["FirstWord", t, "LastWord", t], ...]} -> exact keep ranges
        snapped to word boundaries (written to KEEP_OUT.json), plus the subtitle cues,
        final length, long silences and flagged words for each clip.

    python tools/clipkit.py build TRANSCRIPT KEEP.json META.json CLIPS_OUT.json
        META.json: {"name": {"hook", "title", "description", "score", "hashtags",
        "subs": [[start, end, "texto"], ...]}} -> clips.json (sorted by time).
        Leave "subs" out to burn word-by-word captions of the original audio instead.

    python tools/clipkit.py sync TRANSCRIPT CLIPS.json DIR
        Audio-vs-subtitle offset of rendered DIR/*clip_NN.mp4 (healthy: about +0.2 s).

    python tools/clipkit.py package NAME OUT_DIR "N:caption" ...
        Pull rendered clips from origin/claude/clipper-out (run inside the outreach-bot
        clone), number them in the given order, shrink anything over the 30 MiB chat
        limit, write captions.txt and add the clips to the posting queue
        (posting/queue.json: the next free slots at mediodía / noche, hora de Puerto Rico).

    python tools/clipkit.py due
        Queued clips whose slot has come, as JSON for tools/social.py (the platforms
        still to post, from posting/config.json).

    python tools/clipkit.py mark RESULTS.json
        Record what tools/social.py posted ({"id": {"youtube": {...}, ...}}).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clipper.highlights import format_transcript, transcript_lines  # noqa: E402
from clipper.models import Clip, Word, all_words, load_segments  # noqa: E402
from clipper.render import keep_ranges, remap  # noqa: E402

POSTING = Path(__file__).resolve().parents[1] / "posting"
RAW = "https://raw.githubusercontent.com/Drjonaxx/outreach-bot/claude/clipper-out"
PR = ZoneInfo("America/Puerto_Rico")
# Posting slots (Puerto Rico time; the posting routines fire right at these times) and
# clips per slot. A clip whose slot passed without posting is still tried for 2 days.
SLOT_TIMES = ("11:53", "19:56")
PER_SLOT = 3
MAX_TRIES = 3

FLAGGED = {
    "nigga", "nigger", "niggas", "niggers", "faggot", "faggots", "fag", "faggotry", "retard",
    "retarded", "cunt", "cunts", "tranny", "chink", "spic", "kike", "wetback", "beaner",
}


def words(transcript: str) -> list[Word]:
    return all_words(load_segments(Path(transcript)))


def norm(text: str) -> str:
    return text.lower().strip(".,!?¿¡\"'")


def find(ws: list[Word], text: str, near: float, tol: float = 2.5) -> int:
    hits = [i for i, w in enumerate(ws) if norm(w.text) == norm(text) and abs(w.start - near) <= tol]
    if not hits:
        around = [(w.text, round(w.start, 2)) for w in ws if abs(w.start - near) < 3]
        raise SystemExit(f"No encuentro «{text}» cerca de {near}: {around}")
    return min(hits, key=lambda i: abs(ws[i].start - near))


def span(ws: list[Word], first: str, t1: float, last: str, t2: float, pad: float = 0.12) -> list[float]:
    i, j = find(ws, first, t1), find(ws, last, t2)
    start = max(ws[i].start - pad, ws[i - 1].end + 0.02) if i else ws[i].start - pad
    end = min(ws[j].end + pad, ws[j + 1].start - 0.02) if j + 1 < len(ws) else ws[j].end + pad
    return [round(start, 2), round(end, 2)]


def cues_for(ws: list[Word], ranges) -> list[list[Word]]:
    inside = [w for w in ws if any(s - 0.05 <= w.start and w.end <= e + 0.05 for s, e in ranges)]
    cues, cur = [], []
    for w in inside:
        if cur and (w.start - cur[-1].end > 0.7 or w.end - cur[0].start > 3.2
                    or len(" ".join(x.text for x in cur + [w])) > 48):
            cues.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w.text):
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    return cues


def cmd_lines(transcript: str) -> None:
    print(format_transcript(transcript_lines(words(transcript), max_line_seconds=10)))


def cmd_cues(transcript: str, spans_path: str, keep_out: str) -> None:
    ws = words(transcript)
    keep = {name: [span(ws, *s) for s in specs] for name, specs in json.loads(Path(spans_path).read_text()).items()}
    Path(keep_out).write_text(json.dumps(keep, indent=1))
    for name, k in keep.items():
        clip = Clip(k[0][0], k[-1][1], "", "", "", [], 0, name, keep=k)
        ranges = keep_ranges(clip, ws)
        said = [w for w in ws if any(s - 0.05 <= w.start and w.end <= e + 0.05 for s, e in ranges)]
        flagged = sorted({w.text for w in said if norm(w.text) in FLAGGED})
        print(f"\n## {name} — final {sum(e - s for s, e in ranges):.0f}s"
              + (f"  ⚠️ PALABRAS MARCADAS: {flagged}" if flagged else ""))
        for q in cues_for(ws, ranges):
            print(f"[{q[0].start:.2f}, {q[-1].end:.2f}, \"\"],  # {' '.join(x.text for x in q)}")


def cmd_build(transcript: str, keep_path: str, meta_path: str, out: str) -> None:
    from dataclasses import asdict
    ws = words(transcript)
    keep = json.loads(Path(keep_path).read_text())
    meta = json.loads(Path(meta_path).read_text())
    clips = []
    for name, k in keep.items():
        m = dict(meta[name])
        # No "subs" (e.g. a Spanish-speaking streamer): word-by-word captions of the original audio.
        subs = [{"start": round(a, 2), "end": round(b, 2), "text": t} for a, b, t in m.pop("subs", None) or []] or None
        for s in subs or []:
            if not any(x - 0.3 <= s["start"] and s["end"] <= y + 0.3 for x, y in k):
                raise SystemExit(f"{name}: el subtítulo {s} cae fuera de los tramos {k}")
        clip = Clip(start=k[0][0], end=k[-1][1], reason=name, keep=k, subs=subs, **m)
        ranges = keep_ranges(clip, ws)
        said = [w.text for w in ws if any(s - 0.05 <= w.start and w.end <= e + 0.05 for s, e in ranges)]
        if any(norm(t) in FLAGGED for t in said):
            raise SystemExit(f"{name}: contiene palabras marcadas; recorta esos tramos")
        clips.append(clip)
    clips.sort(key=lambda c: c.start)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps([asdict(c) for c in clips], ensure_ascii=False, indent=2))
    for i, c in enumerate(clips, 1):
        print(f"clip_{i:02d}  {c.reason:14s} score {c.score}  {c.hook}")


def cmd_sync(transcript: str, clips_path: str, folder: str) -> None:
    import numpy as np
    ws = words(transcript)
    clips = [Clip(**c) for c in json.loads(Path(clips_path).read_text())]
    sr, hop = 16000, 0.02
    for i, c in enumerate(clips, 1):
        f = next(Path(folder).glob(f"*clip_{i:02d}.mp4"), None)
        if not f:
            continue
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", str(sr),
                              "-af", "highpass=f=250,lowpass=f=3500", "-f", "f32le", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, np.float32)
        n = int(hop * sr)
        env = np.log1p(100 * np.sqrt((a[: len(a) // n * n].reshape(-1, n) ** 2).mean(1)))
        env = (env - env.mean()) / (env.std() + 1e-9)
        ranges = keep_ranges(c, ws)
        mask = np.zeros(len(env))
        for w in ws:
            if any(s - 0.05 <= w.start and w.end <= e + 0.05 for s, e in ranges):
                mask[int(remap(w.start, ranges) / hop):int(remap(w.end, ranges) / hop)] = 1
        mask = (mask - mask.mean()) / (mask.std() + 1e-9)

        def score(lag: int) -> float:
            return float(np.dot(env[max(0, lag):len(env) + min(0, lag)], mask[max(0, -lag):len(mask) - max(0, lag)]))

        best = max(range(-150, 151), key=score)
        ok = "ok" if -0.2 <= best * hop <= 0.6 else "REVISAR"
        print(f"clip_{i:02d} {c.reason:14s} desfase {best * hop:+.2f}s  {ok}")


def cmd_package(name: str, out_dir: str, *items: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines, queued = [], []
    for pos, item in enumerate(items, 1):
        num, caption = item.split(":", 1)
        src = f"origin/claude/clipper-out:{name}/clip_{int(num):02d}.mp4"
        dest = out / f"{pos:02d}_clip_{int(num):02d}.mp4"
        dest.write_bytes(subprocess.run(["git", "show", src], check=True, capture_output=True).stdout)
        if dest.stat().st_size > 29 * 1024 * 1024:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        str(dest)], capture_output=True, text=True).stdout)
            vb = int(27.5 * 8 * 1024 * 1024 / dur - 160_000)
            tmp = dest.with_suffix(".tmp.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(dest), "-c:v", "libx264", "-preset", "medium",
                            "-b:v", str(vb), "-maxrate", str(vb * 3 // 2), "-bufsize", str(vb * 2), "-r", "30",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)], check=True)
            tmp.replace(dest)
        length = len(caption.encode("utf-16-le")) // 2
        if length > 100:
            raise SystemExit(f"Caption de {dest.name} tiene {length} caracteres (máx. 100)")
        lines += [f"{dest.name}  ({length} caracteres)", caption, ""]
        queued.append(post_fields(name, int(num), caption, read_meta(name, int(num))))
    (out / "captions.txt").write_text("\n".join(lines))
    print("\n".join(lines))
    queue = load_queue()
    known = {q["id"] for q in queue}
    for item in queued:
        if item["id"] not in known:
            item["at"] = free_slot(queue, datetime.now(PR))
            queue.append(item)
            print(f"en cola: {item['id']} -> {item['at']}")
    save_queue(queue)


def read_meta(name: str, num: int) -> dict:
    """Description, source link and hashtags from the clip's rendered .txt."""
    txt = subprocess.run(["git", "show", f"origin/claude/clipper-out:{name}/clip_{num:02d}.txt"],
                         check=True, capture_output=True, text=True).stdout
    body = txt.split("DESCRIPCIÓN:", 1)[1].strip()
    lines = body.splitlines()
    tags = next((ln.split() for ln in lines if ln.startswith("#") and all(t.startswith("#") for t in ln.split())), [])
    url = next((ln.strip() for ln in lines if ln.startswith("http")), "")
    return {"description": body.split("\n\n")[0].strip(), "url": url, "tags": [t.lstrip("#") for t in tags]}


def post_fields(name: str, num: int, caption: str, meta: dict) -> dict:
    """Title/description for YouTube and the Instagram caption. The caption (with the
    streamer credit) is the title; hashtags it already has aren't repeated."""
    have = {t.lower() for t in re.findall(r"#(\w+)", caption)}
    hashtags = " ".join(f"#{t}" for t in meta["tags"] if t.lower() not in have)
    source = f"\n\n🎥 Stream original: {meta['url']}" if meta["url"] else ""
    return {
        "id": f"{name}/{num:02d}",
        "url": f"{RAW}/{name}/clip_{num:02d}.mp4",
        "title": re.sub(r"[<>]", "", caption),
        "description": f"{caption}\n\n{meta['description']}{source}\n\n{hashtags}".strip(),
        "ig_caption": f"{caption}\n\n{meta['description']}\n\n{hashtags}".strip(),
        "tags": [t for t in meta["tags"] if t != "shorts"],
        "results": {},
    }


def load_queue() -> list[dict]:
    path = POSTING / "queue.json"
    return json.loads(path.read_text()) if path.exists() else []


def save_queue(queue: list[dict]) -> None:
    POSTING.mkdir(exist_ok=True)
    (POSTING / "queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=1) + "\n")


def free_slot(queue: list[dict], now: datetime) -> str:
    """First posting slot that hasn't passed yet and still has room."""
    day = now.date()
    while True:
        for hhmm in SLOT_TIMES:
            at = f"{day.isoformat()}T{hhmm}"
            if datetime.fromisoformat(at).replace(tzinfo=PR) > now - timedelta(minutes=5) \
                    and sum(q["at"] == at for q in queue) < PER_SLOT:
                return at
        day += timedelta(days=1)


def pending_platforms(item: dict, platforms: list[str]) -> list[str]:
    """Platforms where the clip isn't posted yet and still has tries left."""
    res = item.get("results", {})
    return [p for p in platforms
            if "id" not in res.get(p, {}) and res.get(p, {}).get("tries", 0) < MAX_TRIES]


def due_items(queue: list[dict], platforms: list[str], now: datetime) -> list[dict]:
    out = []
    for item in sorted(queue, key=lambda q: q["at"]):
        at = datetime.fromisoformat(item["at"]).replace(tzinfo=PR)
        todo = pending_platforms(item, platforms)
        if todo and now - timedelta(days=2) <= at <= now + timedelta(minutes=15):
            out.append({**{k: v for k, v in item.items() if k not in ("results", "at")}, "platforms": todo,
                        "pending": {p: item.get("results", {}).get(p, {}).get("pending") for p in todo}})
    return out


def merge_results(queue: list[dict], results: dict) -> list[str]:
    by_id = {q["id"]: q for q in queue}
    notes = []
    for item_id, per_platform in results.items():
        item = by_id.get(item_id)
        if not item:
            continue
        for platform, r in per_platform.items():
            old = item.setdefault("results", {}).get(platform, {})
            if "id" in old:
                continue
            new = {k: v for k, v in r.items() if v is not None}
            new["tries"] = old.get("tries", 0) + (1 if "error" in new and "pending" not in new else 0)
            item["results"][platform] = new
            notes.append(f"{item_id} {platform}: " + (new.get("url") or new.get("id") or
                                                      ("procesando" if "pending" in new else new.get("error", "?"))))
    return notes


def posting_config() -> dict:
    path = POSTING / "config.json"
    return json.loads(path.read_text()) if path.exists() else {"platforms": []}


def cmd_due() -> None:
    cfg = posting_config()
    print(json.dumps(due_items(load_queue(), cfg.get("platforms", []), datetime.now(PR)), ensure_ascii=False))


def cmd_mark(results_path: str) -> None:
    queue = load_queue()
    for note in merge_results(queue, json.loads(Path(results_path).read_text())):
        print(note)
    save_queue(queue)


if __name__ == "__main__":
    commands = {"lines": cmd_lines, "cues": cmd_cues, "build": cmd_build, "sync": cmd_sync, "package": cmd_package,
                "due": cmd_due, "mark": cmd_mark}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]](*sys.argv[2:])
