from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

KICK_CHANNEL = re.compile(r"^https?://(?:www\.)?kick\.com/([\w-]+)/?(?:[?#].*)?$")


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


def kick_vods(channel: str) -> list[dict]:
    """List a Kick channel's past broadcasts, newest first."""
    import yt_dlp
    from yt_dlp.networking import Request
    from yt_dlp.networking.impersonate import ImpersonateTarget

    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        resp = ydl.urlopen(Request(
            f"https://kick.com/api/v2/channels/{channel}/videos",
            extensions={"impersonate": ImpersonateTarget("chrome")},
        ))
        data = json.loads(resp.read())

    vods = []
    for v in data:
        video = v.get("video") or {}
        if not video.get("uuid"):
            continue
        vods.append({
            "url": f"https://kick.com/{channel}/videos/{video['uuid']}",
            "title": v.get("session_title") or "",
            "minutes": round((v.get("duration") or 0) / 60000),
            "date": v.get("start_time") or v.get("created_at") or "",
            "views": video.get("views") or v.get("views") or 0,
        })
    return sorted(vods, key=lambda x: x["date"], reverse=True)


def resolve(source: str, vod_index: int = 0) -> str:
    """Turn a Kick channel URL into one of its VOD URLs; anything else passes through."""
    m = KICK_CHANNEL.match(source)
    if not m or m.group(1) in ("video", "categories", "search", "auth"):
        return source
    vods = kick_vods(m.group(1))
    if not vods:
        raise RuntimeError(f"El canal {m.group(1)} no tiene VODs públicos.")
    for i, v in enumerate(vods[:10]):
        print(f"  {'→' if i == vod_index else ' '} [{i}] {v['date'][:10]} {v['minutes']:4d} min  {v['title'][:70]}")
    return vods[vod_index]["url"]


def _format(max_height: int) -> str:
    return f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b"


def _extract(source: str, opts: dict, download: bool) -> tuple[dict, Path]:
    import yt_dlp

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
                info = ydl.extract_info(source, download=download)
                path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
                if not path.exists():
                    path = Path(ydl.prepare_filename(info))
            return info, path
        except yt_dlp.utils.DownloadError as e:
            if "not a bot" not in str(e):
                raise
            print(f"  YouTube pidió verificación (cliente {client or 'default'}); probando otro…")
            last_error = e
    raise last_error


def fetch(
    source: str,
    downloads_dir: Path,
    max_height: int = 1080,
    limit_seconds: float | None = None,
    download: bool = True,
) -> Source:
    """Download a URL with yt-dlp (or just read its metadata), or wrap a local file path."""
    if not is_url(source):
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        return Source(str(path), slugify(path.stem), path.stem, "", "")

    from yt_dlp.utils import download_range_func

    downloads_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{max_height}p" + (f"_{int(limit_seconds)}s" if limit_seconds else "")
    opts = {
        "format": _format(max_height),
        "merge_output_format": "mp4",
        "outtmpl": str(downloads_dir / f"%(id)s{suffix}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 8,
    }
    if limit_seconds:
        opts["download_ranges"] = download_range_func(None, [(0, limit_seconds)])
    info, path = _extract(source, opts, download)
    return Source(
        path=str(path) if download else "",
        id=info.get("id") or slugify(info.get("title", "video")),
        title=info.get("title", ""),
        channel=info.get("channel") or info.get("uploader") or "",
        url=info.get("webpage_url") or source,
    )


def fetch_section(url: str, downloads_dir: Path, start: float, end: float, max_height: int = 1080) -> Path:
    """Download only [start, end) of a remote video, cut exactly at those times."""
    from yt_dlp.utils import download_range_func

    downloads_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": _format(max_height),
        "merge_output_format": "mp4",
        "outtmpl": str(downloads_dir / f"%(id)s_{start:.2f}-{end:.2f}_{max_height}p.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "download_ranges": download_range_func(None, [(start, end)]),
        "force_keyframes_at_cuts": True,
        "concurrent_fragment_downloads": 8,
    }
    _, path = _extract(url, opts, download=True)
    return path
