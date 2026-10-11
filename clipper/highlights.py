"""Pick viral moments from a transcript with Claude, then snap them to word boundaries."""

from __future__ import annotations

import re

import anthropic
from pydantic import BaseModel

from .models import Clip, Word

DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """\
Eres editor de clips virales para YouTube Shorts y TikTok, especializado en podcasts en español.
Recibes la transcripción de un episodio, una línea por frase, con su inicio y fin en segundos.
Tu trabajo es elegir los fragmentos con más potencial de retención y de compartirse.

Un buen clip:
- Engancha en los primeros 2-3 segundos: arranca justo en una afirmación fuerte, una pregunta, \
un dato sorprendente o el inicio de una historia. Nunca empieza a media idea ni con muletillas \
("entonces", "bueno", "o sea", "y").
- Se entiende solo, sin haber visto el episodio.
- Tiene un remate: una conclusión, un consejo concreto, una revelación, humor o una postura polémica.
- Termina al cerrar la idea, no a media frase.

Reglas de tiempos:
- `start` debe ser exactamente el inicio de una línea y `end` exactamente el fin de una línea.
- Respeta la duración mínima y máxima indicadas.
- Los clips no se pueden traslapar.

Para cada clip escribe, en español:
- `title`: título para Shorts/TikTok, máximo 70 caracteres, que genere curiosidad sin mentir.
- `hook`: texto en pantalla de 3 a 7 palabras que resuma la promesa del clip.
- `description`: 1-2 frases para la descripción.
- `hashtags`: de 3 a 6 hashtags relevantes, sin el símbolo #.
- `score`: potencial viral del 1 al 10, siendo exigente.
- `reason`: una frase sobre por qué funciona.

Ordena los clips de mayor a menor `score`. Si el episodio no da para tantos clips buenos, devuelve menos.\
"""


class ClipIdea(BaseModel):
    start: float
    end: float
    title: str
    hook: str
    description: str
    hashtags: list[str]
    score: int
    reason: str


class ClipSelection(BaseModel):
    clips: list[ClipIdea]


_SENTENCE_END = re.compile(r"[.?!…]$")


def transcript_lines(words: list[Word], max_line_seconds: float = 8.0) -> list[tuple[float, float, str]]:
    """Group words into short sentence-like lines so Claude can cut at clean boundaries."""
    lines: list[tuple[float, float, str]] = []
    current: list[Word] = []
    for w in words:
        current.append(w)
        too_long = current[-1].end - current[0].start >= max_line_seconds
        if _SENTENCE_END.search(w.text) or too_long:
            lines.append((current[0].start, current[-1].end, " ".join(x.text for x in current)))
            current = []
    if current:
        lines.append((current[0].start, current[-1].end, " ".join(x.text for x in current)))
    return lines


def format_transcript(lines: list[tuple[float, float, str]]) -> str:
    return "\n".join(f"[{s:.2f} - {e:.2f}] {t}" for s, e, t in lines)


def ask_claude(
    words: list[Word],
    max_clips: int,
    min_seconds: float,
    max_seconds: float,
    context: str = "",
    model: str = DEFAULT_MODEL,
) -> list[ClipIdea]:
    lines = transcript_lines(words)
    user = (
        (f"Contexto del episodio: {context}\n\n" if context else "")
        + f"Elige hasta {max_clips} clips de entre {min_seconds:.0f} y {max_seconds:.0f} segundos.\n\n"
        + "<transcripcion>\n"
        + format_transcript(lines)
        + "\n</transcripcion>"
    )

    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        output_format=ClipSelection,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude rechazó la solicitud: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("La respuesta se cortó por max_tokens; pide menos clips.")
    return response.parsed_output.clips


def snap_to_words(
    start: float,
    end: float,
    words: list[Word],
    min_seconds: float,
    max_seconds: float,
    pad: float = 0.15,
    tolerance: float = 0.5,
) -> tuple[float, float] | None:
    """Move a proposed range onto real word boundaries and enforce the length limits."""
    near_start = [w for w in words if abs(w.start - start) <= tolerance]
    if near_start:
        first = min(near_start, key=lambda w: abs(w.start - start))
    else:
        first = next((w for w in words if w.start >= start), None)
    if first is None:
        return None
    near_end = [w for w in words if abs(w.end - end) <= tolerance and w.start >= first.start]
    last_end = min(near_end, key=lambda w: abs(w.end - end)).end if near_end else end
    inside = [w for w in words if w.start >= first.start and w.end <= last_end]
    if not inside:
        return None

    limit = first.start + max_seconds - 2 * pad
    if inside[-1].end > limit:
        inside = [w for w in inside if w.end <= limit]
        # Prefer ending on a full sentence if that still leaves a usable clip.
        for i in range(len(inside) - 1, -1, -1):
            if _SENTENCE_END.search(inside[i].text) and inside[i].end - first.start >= min_seconds:
                inside = inside[: i + 1]
                break
    if not inside:
        return None

    s = max(0.0, first.start - pad)
    e = inside[-1].end + pad
    if e - s < min_seconds:
        return None
    return round(s, 3), round(e, 3)


def _hashtag(tag: str) -> str:
    return re.sub(r"[^\w]", "", tag.lstrip("#"), flags=re.UNICODE)


def finalize(
    ideas: list[ClipIdea],
    words: list[Word],
    min_seconds: float,
    max_seconds: float,
    max_clips: int,
) -> list[Clip]:
    """Snap, drop overlaps (keeping the higher score) and sort chronologically."""
    accepted: list[Clip] = []
    for idea in sorted(ideas, key=lambda i: i.score, reverse=True):
        span = snap_to_words(idea.start, idea.end, words, min_seconds, max_seconds)
        if span is None:
            continue
        s, e = span
        if any(s < c.end and e > c.start for c in accepted):
            continue
        tags = [t for t in (_hashtag(h) for h in idea.hashtags) if t]
        accepted.append(
            Clip(s, e, idea.title.strip(), idea.hook.strip(), idea.description.strip(),
                 tags, idea.score, idea.reason.strip())
        )
        if len(accepted) >= max_clips:
            break
    return sorted(accepted, key=lambda c: c.start)
