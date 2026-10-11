"""clipper: podcast largo -> clips verticales para YouTube Shorts y TikTok.

Uso:
    python -m clipper "https://www.youtube.com/watch?v=..." --clips 6
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .download import fetch, fetch_section, is_url, resolve
from .highlights import DEFAULT_MODEL, ask_claude, finalize
from .models import Word, all_words, load_clips, load_segments, save_clips, save_segments
from .reframe import probe
from .render import DEFAULT_FONT, render_clip, write_metadata


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="clipper", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="URL (YouTube, etc.) o ruta a un video local")
    p.add_argument("--out", default="out", help="carpeta de salida (default: out)")
    p.add_argument("--clips", type=int, default=6, help="máximo de clips (default: 6)")
    p.add_argument("--min", dest="min_s", type=float, default=25, help="duración mínima en s (default: 25)")
    p.add_argument("--max", dest="max_s", type=float, default=75, help="duración máxima en s (default: 75)")
    p.add_argument("--language", default="es", help="idioma del audio: es, en… o auto (default: es)")
    p.add_argument("--whisper-model", default="small",
                   help="tiny/base/small/medium/large-v3 (default: small; large-v3 si tienes GPU)")
    p.add_argument("--device", default="auto", help="auto/cpu/cuda (default: auto)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"modelo de Claude (default: {DEFAULT_MODEL})")
    p.add_argument("--context", default="", help="contexto opcional: quién habla, de qué trata")
    p.add_argument("--reselect", action="store_true", help="volver a pedir clips a Claude aunque exista clips.json")
    p.add_argument("--name", help="nombre de la carpeta de trabajo (default: id del video)")
    p.add_argument("--transcribe-only", action="store_true", help="solo descargar y transcribir")
    p.add_argument("--select-only", action="store_true", help="solo transcribir y elegir clips, sin renderizar")
    p.add_argument("--font", default=DEFAULT_FONT, help=f"fuente de los subtítulos (default: {DEFAULT_FONT})")
    p.add_argument("--hook-seconds", type=float, default=0,
                   help="segundos que se muestra el texto gancho arriba (0 = todo el clip)")
    p.add_argument("--no-captions", action="store_true", help="no quemar subtítulos")
    p.add_argument("--jumpcut", type=float, default=3.0,
                   help="acortar silencios de más de N segundos (0 = no cortar; default: 3)")
    p.add_argument("--max-height", type=int, default=1080, help="calidad máxima a descargar (default: 1080)")
    p.add_argument("--limit-minutes", type=float, help="procesar solo los primeros N minutos")
    p.add_argument("--vod", default="0", help="con un canal de Kick: índice del VOD (0 = el más reciente) o parte de su título")
    p.add_argument("--sections", action="store_true",
                   help="al renderizar, descargar solo el tramo de cada clip (ideal para streams largos)")
    args = p.parse_args(argv)
    language = None if args.language == "auto" else args.language
    downloads = Path(args.out) / "_downloads"
    limit = args.limit_minutes * 60 if args.limit_minutes else None

    log("1/4 Obteniendo video…")
    url = resolve(args.source, args.vod) if is_url(args.source) else args.source
    meta = fetch(url, downloads, args.max_height, limit, download=False)
    work = Path(args.out) / (args.name or meta.id)
    work.mkdir(parents=True, exist_ok=True)
    (work / "source.json").write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2))
    log(f"    {meta.title or meta.path}")

    transcript_path = work / "transcript.json"
    if transcript_path.exists():
        log("2/4 Transcripción en caché")
        segments = load_segments(transcript_path)
    else:
        src = fetch(url, downloads, args.max_height, limit)
        log(f"2/4 Transcribiendo con Whisper ({args.whisper_model})…")
        from .transcribe import transcribe
        segments = transcribe(src.path, args.whisper_model, language, args.device)
        save_segments(segments, transcript_path)
    words = all_words(segments)
    if not words:
        log("No se detectó voz en el video.")
        return 1
    if args.transcribe_only:
        log(f"Transcripción lista: {transcript_path}")
        return 0

    clips_path = work / "clips.json"
    if clips_path.exists() and not args.reselect:
        log("3/4 Usando clips.json existente (edítalo a mano o usa --reselect)")
        clips = load_clips(clips_path)
    else:
        log(f"3/4 Eligiendo momentos con {args.model}…")
        context = args.context or " — ".join(x for x in (meta.title, meta.channel) if x)
        ideas = ask_claude(words, args.clips, args.min_s, args.max_s, context, args.model)
        clips = finalize(ideas, words, args.min_s, args.max_s, args.clips)
        save_clips(clips, clips_path)
    for i, c in enumerate(clips, 1):
        log(f"    {i:02d}. [{c.start:7.1f}s +{c.duration:4.0f}s] {c.score}/10  {c.title}")
    if args.select_only or not clips:
        return 0

    log("4/4 Renderizando clips verticales…")
    sections = args.sections and is_url(url)
    if not sections:
        src = fetch(url, downloads, args.max_height, limit)
        info = probe(src.path)
    for i, clip in enumerate(clips, 1):
        out_path = work / f"clip_{i:02d}.mp4"
        if sections:
            # Grab just this stretch (plus a margin) and shift times onto it.
            s0, s1 = max(0.0, clip.start - 1.0), clip.end + 1.0
            path = str(fetch_section(meta.url, downloads, s0, s1, args.max_height))
            render_info = probe(path)
            render_clip_ = replace(
                clip, start=clip.start - s0, end=clip.end - s0,
                keep=[[a - s0, b - s0] for a, b in clip.keep] if clip.keep else None,
            )
            render_words = [Word(w.start - s0, w.end - s0, w.text) for w in words if s0 <= w.start < s1]
        else:
            path, render_info, render_clip_, render_words = src.path, info, clip, words
        mode = render_clip(
            path, render_info, render_clip_, render_words, out_path,
            font=args.font, hook_seconds=args.hook_seconds, captions=not args.no_captions,
            max_gap=args.jumpcut,
        )
        write_metadata(out_path.with_suffix(".txt"), clip, meta.title, meta.channel, meta.url)
        log(f"    ✓ {out_path} ({'sigue la cara' if mode == 'crop' else 'plano completo'})")

    log(f"\nListo: {len(clips)} clips en {work}/")
    return 0

if __name__ == "__main__":
    sys.exit(main())
