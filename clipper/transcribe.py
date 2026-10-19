from __future__ import annotations

import math
import subprocess
import sys

import numpy as np

from .models import Segment, Word

SAMPLE_RATE = 16000
# Long streams are transcribed in pieces: a whole 14 h stream decoded at once needs more
# memory than a CI runner has.
CHUNK_SECONDS = 20 * 60


def load_audio(path: str, start: float = 0.0, duration: float | None = None) -> np.ndarray:
    """Decode to 16 kHz mono float32 with ffmpeg (avoids faster-whisper's PyAV path,
    which breaks with recent PyAV releases), optionally only [start, start + duration).
    Audio dropouts in the VOD are filled with silence, as the renderer does, so word
    times stay on the video's clock."""
    window = ["-ss", f"{start:.3f}"] + (["-t", f"{duration:.3f}"] if duration else [])
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", *window, "-i", path,
         "-vn", "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(out, np.float32)


def media_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def transcribe(
    media_path: str,
    model_size: str = "small",
    language: str = "es",
    device: str = "auto",
) -> list[Segment]:
    """Transcribe with faster-whisper, keeping word-level timestamps."""
    from faster_whisper import WhisperModel

    if device == "auto":
        import ctranslate2
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute_type = "int8" if device == "cpu" else "default"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    total = media_duration(media_path)
    chunks = [(t, CHUNK_SECONDS) for t in range(0, math.ceil(total), CHUNK_SECONDS)] or [(0, None)]

    segments: list[Segment] = []
    for start, length in chunks:
        raw_segments, _ = model.transcribe(
            load_audio(media_path, start, length),
            language=language,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
        for s in raw_segments:
            words = [
                Word(round(start + w.start, 3), round(start + w.end, 3), w.word.strip())
                for w in (s.words or [])
                if w.word.strip()
            ]
            segments.append(Segment(round(start + s.start, 3), round(start + s.end, 3), s.text.strip(), words))
            pct = min(100, 100 * (start + s.end) / max(total, 1))
            print(f"\r  transcribiendo… {pct:5.1f}%", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    return segments
