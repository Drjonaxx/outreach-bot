"""
Tracks published news to avoid duplicate posts.
Stores data in published_posts.json in the working directory.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

TRACKER_FILE = Path("published_posts.json")
MAX_ENTRIES = 300  # Keep last N entries to avoid unbounded growth


def _load() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"posts": []}


def _save(data: dict) -> None:
    TRACKER_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _key(url: str) -> str:
    """Stable short key for a news URL."""
    return hashlib.md5(url.strip().encode()).hexdigest()[:16]


def is_published(url: str) -> bool:
    """Return True if this URL was already published."""
    key = _key(url)
    data = _load()
    return any(p["key"] == key for p in data["posts"])


def mark_published(url: str, title: str, threads_ids: dict) -> None:
    """Record that a news item was successfully posted."""
    data = _load()
    data["posts"].append(
        {
            "key": _key(url),
            "url": url,
            "title": title,
            "published_at": datetime.now().isoformat(),
            "threads_ids": threads_ids,
        }
    )
    # Trim to max entries
    data["posts"] = data["posts"][-MAX_ENTRIES:]
    _save(data)


def recent_titles(n: int = 20) -> list[str]:
    """Return titles of the N most recently published items (for dedup prompts)."""
    data = _load()
    return [p["title"] for p in data["posts"][-n:]]
