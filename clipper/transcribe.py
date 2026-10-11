from __future__ import annotations

import subprocess
import sys

import numpy as np

from .models import Segment, Word

SAMPLE_RATE = 16000


def load_audio(path: str) -> np.ndarray:
    """Decode to 16 kHz mono float32 with ffmpeg (avoids faster-whisper's PyAV path,
    which breaks with recent PyAV releases)."""
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path,
         "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(out, np.float32)


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
    raw_segments, info = model.transcribe(
        load_audio(media_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )

    segments: list[Segment] = []
    for s in raw_segments:
        words = [
            Word(round(w.start, 3), round(w.end, 3), w.word.strip())
            for w in (s.words or [])
            if w.word.strip()
        ]
        segments.append(Segment(round(s.start, 3), round(s.end, 3), s.text.strip(), words))
        pct = min(100, 100 * s.end / max(info.duration, 1))
        print(f"\r  transcribiendo… {pct:5.1f}%", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    return segments
