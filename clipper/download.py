from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Source:
    path: str
    id: str
    title: str
    channel: str
    url: str

    def to_dict(self) -> dict:
        return asdict(self)


def is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value))


def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^\w\-]+", "-", text.lower(), flags=re.UNICODE).strip("-")
    return text[:max_len] or "video"


def fetch(source: str, downloads_dir: Path) -> Source:
    """Download a URL with yt-dlp, or wrap a local file path."""
    if not is_url(source):
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        return Source(str(path), slugify(path.stem), path.stem, "", "")

    import yt_dlp

    downloads_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        # Best video up to 1080p + best audio, merged to mp4.
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(downloads_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if os.environ.get("YTDLP_COOKIES"):
        opts["cookiefile"] = os.environ["YTDLP_COOKIES"]

    # YouTube sometimes answers server IPs with a bot check that only some
    # player clients get; try yt-dlp's default first, then the alternatives.
    clients = [None, "tv_simply", "web_embedded", "mweb", "android_vr"]
    last_error: Exception | None = None
    for client in clients:
        attempt = dict(opts)
        if client:
            attempt["extractor_args"] = {"youtube": {"player_client": [client]}}
        try:
            with yt_dlp.YoutubeDL(attempt) as ydl:
                info = ydl.extract_info(source, download=True)
                path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
                if not path.exists():
                    path = Path(ydl.prepare_filename(info))
            break
        except yt_dlp.utils.DownloadError as e:
            if "not a bot" not in str(e):
                raise
            print(f"  YouTube pidió verificación (cliente {client or 'default'}); probando otro…")
            last_error = e
    else:
        raise last_error
    return Source(
        path=str(path),
        id=info.get("id") or slugify(info.get("title", "video")),
        title=info.get("title", ""),
        channel=info.get("channel") or info.get("uploader") or "",
        url=info.get("webpage_url") or source,
    )
