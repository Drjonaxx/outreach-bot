"""Run the job described in job.json (used by the GitHub Actions workflow).

Stage 1, no jobs/<name>/clips.json yet: download (low res) + transcribe -> results/<name>/transcript.json
Stage 2, clips.json present:           download each clip's stretch in 1080p and render
                                       -> results/<name>/clip_XX.mp4

job.json fields: name, url, and optionally language ("es"), whisper_model ("small"),
limit_minutes (only the first N minutes), vod (Kick channel: 0 = latest VOD),
layout ("auto"/"crop"/"fit"), only (re-render just these clip numbers),
retranscribe (true: transcribe again even if results/<name>/transcript.json exists).
A new job whose VOD was already processed under another name writes
results/<name>/status.json {"status": "no_new_vod"} and stops.
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

job = json.loads(Path("job.json").read_text())
name = job["name"]
results = Path("results")
work = results / name
work.mkdir(parents=True, exist_ok=True)

clips = Path("jobs") / name / "clips.json"

# Once stage 1 has picked a video (e.g. a Kick channel's latest VOD), stick to it.
url = job["url"]
source = work / "source.json"
if source.exists():
    url = json.loads(source.read_text()).get("url") or url
elif not clips.exists():
    # New job: resolve the channel to a VOD now, and stop if an earlier job already
    # processed it (the daily routine runs even when the streamer didn't go live).
    from clipper.download import resolve

    try:
        url = resolve(job["url"], str(job.get("vod", 0)))
    except Exception as e:  # noqa: BLE001 - report any failure to the daily routine
        print(f"No pude obtener un VOD de {job['url']}: {e}", flush=True)
        (work / "status.json").write_text(json.dumps({"status": "error", "url": job["url"], "error": str(e)}, indent=2))
        sys.exit(0)
    for seen in results.glob("*/source.json"):
        if seen.parent != work and json.loads(seen.read_text()).get("url") == url:
            print(f"Sin VOD nuevo: {url} ya se procesó en {seen.parent.name}", flush=True)
            (work / "status.json").write_text(json.dumps(
                {"status": "no_new_vod", "url": url, "seen_in": seen.parent.name}, indent=2))
            sys.exit(0)

cmd = [
    "clipper", url, "--out", str(results), "--name", name,
    "--language", job.get("language", "es"),
    "--whisper-model", job.get("whisper_model", "small"),
    "--vod", str(job.get("vod", 0)),
]
if clips.exists():
    shutil.copy(clips, work / "clips.json")
    cmd += ["--sections", "--layout", job.get("layout", "auto")]
    if job.get("only"):
        cmd += ["--only", ",".join(str(i) for i in job["only"])]
else:
    if job.get("retranscribe"):
        (work / "transcript.json").unlink(missing_ok=True)
    cmd += ["--transcribe-only", "--max-height", "360"]
    if job.get("limit_minutes"):
        cmd += ["--limit-minutes", str(job["limit_minutes"])]

print("+", " ".join(cmd), flush=True)
code = subprocess.call(cmd)
if clips.exists() and code == 0:
    # The publish step keeps a job's videos for a few days so they can still be posted.
    (work / "rendered_at").write_text(f"{time.time():.0f}\n")
sys.exit(code)
