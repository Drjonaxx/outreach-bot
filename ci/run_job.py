"""Run the job described in job.json (used by the GitHub Actions workflow).

Stage 1, no jobs/<name>/clips.json yet: download + transcribe -> results/<name>/transcript.json
Stage 2, clips.json present:           render the clips      -> results/<name>/clip_XX.mp4
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

cmd = [
    "clipper", job["url"], "--out", str(results), "--name", name,
    "--whisper-model", job.get("whisper_model", "small"),
]
clips = Path("jobs") / name / "clips.json"
if clips.exists():
    shutil.copy(clips, work / "clips.json")
else:
    cmd.append("--transcribe-only")

print("+", " ".join(cmd), flush=True)
sys.exit(subprocess.call(cmd))
