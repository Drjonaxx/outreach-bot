"""Run the job described in job.json (used by the GitHub Actions workflow).

Stage 1, no jobs/<name>/clips.json yet: download (low res) + transcribe -> results/<name>/transcript.json
Stage 2, clips.json present:           download each clip's stretch in 1080p and render
                                       -> results/<name>/clip_XX.mp4

job.json fields: name, url, and optionally language ("es"), whisper_model ("small"),
limit_minutes (only the first N minutes), vod (Kick channel: 0 = latest VOD).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

job = json.loads(Path("job.json").read_text())
name = job["name"]
results = Path("results")
work = results / name
work.mkdir(parents=True, exist_ok=True)

# Once stage 1 has picked a video (e.g. a Kick channel's latest VOD), stick to it.
url = job["url"]
source = work / "source.json"
if source.exists():
    url = json.loads(source.read_text()).get("url") or url

cmd = [
    "clipper", url, "--out", str(results), "--name", name,
    "--language", job.get("language", "es"),
    "--whisper-model", job.get("whisper_model", "small"),
    "--vod", str(job.get("vod", 0)),
]
clips = Path("jobs") / name / "clips.json"
if clips.exists():
    shutil.copy(clips, work / "clips.json")
    cmd += ["--sections", "--layout", job.get("layout", "auto")]
else:
    cmd += ["--transcribe-only", "--max-height", "360"]
    if job.get("limit_minutes"):
        cmd += ["--limit-minutes", str(job["limit_minutes"])]

print("+", " ".join(cmd), flush=True)
sys.exit(subprocess.call(cmd))
