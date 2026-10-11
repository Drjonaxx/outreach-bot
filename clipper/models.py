from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


@dataclass
class Clip:
    start: float
    end: float
    title: str
    hook: str
    description: str
    hashtags: list[str]
    score: int
    reason: str
    # Absolute [start, end] pieces to keep; None keeps the whole span.
    keep: list[list[float]] | None = None
    # Phrase subtitles [{"start", "end", "text"}] in absolute time; replace the word captions.
    subs: list[dict] | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start


def all_words(segments: list[Segment]) -> list[Word]:
    return [w for s in segments for w in s.words]


def save_segments(segments: list[Segment], path: Path) -> None:
    path.write_text(json.dumps([asdict(s) for s in segments], ensure_ascii=False, indent=1))


def load_segments(path: Path) -> list[Segment]:
    raw = json.loads(path.read_text())
    return [
        Segment(s["start"], s["end"], s["text"], [Word(**w) for w in s["words"]])
        for s in raw
    ]


def save_clips(clips: list[Clip], path: Path) -> None:
    path.write_text(json.dumps([asdict(c) for c in clips], ensure_ascii=False, indent=2))


def load_clips(path: Path) -> list[Clip]:
    return [Clip(**c) for c in json.loads(path.read_text())]
