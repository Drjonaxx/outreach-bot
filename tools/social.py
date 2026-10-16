"""Post queued clips to YouTube Shorts and Instagram Reels from Composio's remote workbench.

Runs INSIDE the workbench, where run_composio_tool() and upload_local_file() come preloaded:

    import requests
    exec(requests.get("https://raw.githubusercontent.com/Drjonaxx/outreach-bot/claude/clipper/tools/social.py").text)
    upload_private(UPCOMING)         # early morning: upload to YouTube as private, scheduled for its slot
                                     # (`clipkit.py upcoming`); YouTube then publishes it by itself
    start(ITEMS, ig_user_id="...", yt_channel_id="UC...")   # at the slot: make them public (or upload)
                                     # + the channel's comment, and create the Reel containers
    finish(ig_user_id="...")         # publish the Reels once Instagram has processed them

ITEMS is the output of `clipkit.py due`. Each call prints its results as JSON for
`clipkit.py mark`; they are also kept in LEDGER so a clip is never posted twice.
Uses the Composio accounts with alias ACCOUNT (the channel's, not any other account).
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ACCOUNT = "gringo"
LEDGER = Path("/mnt/files/gringo_posted.json")
_lock = threading.Lock()


def _ledger() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def _record(item_id: str, platform: str, result: dict) -> dict:
    with _lock:
        data = _ledger()
        data.setdefault(item_id, {})[platform] = result
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(data, indent=1))
    return result


def _find(obj, key: str):
    """First non-empty value for `key` anywhere in a nested tool response."""
    if isinstance(obj, dict):
        if obj.get(key):
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            found = _find(v, key)
            if found:
                return found
    return None


def _failed(res, err) -> str | None:
    if err:
        return str(err)[:300]
    if isinstance(res, dict) and (res.get("successful") is False or res.get("error")):
        return str(res.get("error") or res)[:300]
    return None


def _stage(item: dict) -> dict:
    path = Path("/tmp") / (item["id"].replace("/", "_") + ".mp4")
    r = requests.get(item["url"], timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    res, err = upload_local_file(str(path))  # noqa: F821 - workbench helper
    if err:
        raise RuntimeError(err)
    return {"name": path.name, "mimetype": "video/mp4", "s3key": res["s3key"]}


def _youtube(item: dict, video: dict, privacy: str = "public") -> dict:
    res, err = run_composio_tool("YOUTUBE_UPLOAD_VIDEO", {  # noqa: F821 - workbench helper
        "title": item["title"], "description": item["description"], "tags": item["tags"],
        "categoryId": "24", "privacyStatus": privacy, "videoFilePath": video,
    }, account=ACCOUNT)
    vid = None if _failed(res, err) else _find(res, "id")
    if not vid:
        return {"error": _failed(res, err) or str(res)[:300]}
    if privacy != "public":
        return {"private_id": vid}
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}"}


def _release(vid: str) -> dict:
    """Make a video uploaded earlier as private public."""
    res, err = run_composio_tool("YOUTUBE_UPDATE_VIDEO", {  # noqa: F821 - workbench helper
        "video_id": vid, "privacy_status": "public"}, account=ACCOUNT)
    if _failed(res, err):
        return {"private_id": vid, "error": _failed(res, err)}
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}"}


def _schedule(vid: str, publish_at: str) -> str | None:
    """Have YouTube publish a private video by itself at `publish_at` (UTC), so its slot needs no
    API quota (the shared one is often used up by then). Composio has no tool for this, so it goes
    through the channel's connection (the only YouTube account connected) with proxy_execute."""
    when = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    if when < datetime.now(timezone.utc) + timedelta(minutes=10):
        return None
    _, err = proxy_execute("PUT", "https://www.googleapis.com/youtube/v3/videos", "youtube",  # noqa: F821
                           query_params={"part": "status"},
                           body={"id": vid, "status": {"privacyStatus": "private", "publishAt": publish_at,
                                                       "selfDeclaredMadeForKids": False}})
    return None if err else publish_at


def _reel_container(item: dict, video: dict, ig_user_id: str) -> dict:
    res, err = run_composio_tool("INSTAGRAM_POST_IG_USER_MEDIA", {  # noqa: F821 - workbench helper
        "ig_user_id": ig_user_id, "video_file": video, "caption": item["ig_caption"],
        "media_type": "REELS", "share_to_feed": True,
    }, account=ACCOUNT)
    cid = None if _failed(res, err) else _find(res, "id")
    return {"pending": cid, "tries": 0} if cid else {"error": _failed(res, err) or str(res)[:300]}


def _comment(video_id: str, channel_id: str, text: str) -> str | None:
    res, err = run_composio_tool("YOUTUBE_POST_COMMENT", {  # noqa: F821 - workbench helper
        "videoId": video_id, "channelId": channel_id, "textOriginal": text}, account=ACCOUNT)
    return None if _failed(res, err) else _find(res, "id")


def start(items: list[dict], ig_user_id: str | None = None, yt_channel_id: str | None = None) -> dict:
    """Stage each clip once, upload it to YouTube (plus the channel's own comment under it)
    and create its Reel container (< 1 min)."""
    def one(item: dict):
        done = _ledger().get(item["id"], {})
        # The queue remembers containers created by an earlier run (if the ledger was lost).
        for p, cid in (item.get("pending") or {}).items():
            if cid and p not in done:
                done[p] = _record(item["id"], p, {"pending": cid, "tries": 0})
        private_id = item.get("youtube_private_id") or done.get("youtube", {}).get("private_id")
        scheduled = item.get("youtube_scheduled") or done.get("youtube", {}).get("scheduled")
        if scheduled and datetime.fromisoformat(scheduled.replace("Z", "+00:00")) > datetime.now(timezone.utc):
            item = {**item, "platforms": [p for p in item["platforms"] if p != "youtube"]}  # not out yet
        todo = [p for p in item["platforms"] if not ({"id", "pending"} & done.get(p, {}).keys())]
        if "instagram" in todo and not ig_user_id:
            todo.remove("instagram")
        out = {p: done[p] for p in item["platforms"] if p in done and p not in todo}
        upload = [p for p in todo if p == "instagram" or (p == "youtube" and not private_id)]
        video = None
        if upload:
            try:
                video = _stage(item)
            except Exception as e:  # noqa: BLE001 - report and let the next run retry
                out.update({p: {"error": f"descarga: {e}"[:300]} for p in upload})
                todo = [p for p in todo if p not in upload]
        if "youtube" in todo:
            if private_id and scheduled:  # YouTube already published it at its time
                yt = {"id": private_id, "url": f"https://youtube.com/shorts/{private_id}"}
            else:
                yt = _release(private_id) if private_id else _youtube(item, video)
            if "id" in yt and yt_channel_id and item.get("comment"):
                yt["comment"] = _comment(yt["id"], yt_channel_id, item["comment"])
            out["youtube"] = _record(item["id"], "youtube", yt)
        if "instagram" in todo:
            out["instagram"] = _record(item["id"], "instagram", _reel_container(item, video, ig_user_id))
        return item["id"], out

    with ThreadPoolExecutor(4) as ex:
        results = dict(ex.map(one, items))
    print(json.dumps(results, ensure_ascii=False))
    return results


def upload_private(items: list[dict]) -> dict:
    """Upload clips to YouTube as private ahead of time (the shared upload quota resets at
    midnight Pacific), scheduled to go public at their slot; start() then only marks them and
    comments (or makes them public itself if scheduling failed). Output is for `clipkit.py mark`."""
    def one(item: dict):
        state = _ledger().get(item["id"], {}).get("youtube", {})
        if {"id", "private_id"} & state.keys():
            return item["id"], {"youtube": state}
        try:
            video = _stage(item)
        except Exception as e:  # noqa: BLE001 - report and let the next run retry
            return item["id"], {"youtube": {"error": f"descarga: {e}"[:300]}}
        yt = _youtube(item, video, "private")
        if "private_id" in yt and item.get("publish_at"):
            yt["scheduled"] = _schedule(yt["private_id"], item["publish_at"])
        return item["id"], {"youtube": _record(item["id"], "youtube", yt)}

    with ThreadPoolExecutor(3) as ex:
        results = dict(ex.map(one, items))
    print(json.dumps(results, ensure_ascii=False))
    return results


def finish(ig_user_id: str, wait: int = 120) -> dict:
    """Publish every Reel container still pending (Instagram needs ~30-120 s per video)."""
    pend = [(i, r["instagram"]) for i, r in _ledger().items() if "pending" in r.get("instagram", {})]

    def publish(entry):
        item_id, state = entry
        res, err = run_composio_tool("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {  # noqa: F821
            "ig_user_id": ig_user_id, "creation_id": state["pending"], "max_wait_seconds": wait,
        }, account=ACCOUNT)
        mid = None if _failed(res, err) else _find(res, "id")
        if mid:
            info, _ = run_composio_tool("INSTAGRAM_GET_IG_MEDIA", {  # noqa: F821
                "ig_media_id": mid, "fields": "permalink,caption"}, account=ACCOUNT)
            caption = _find(info, "caption") or ""
            result = {"id": mid, "url": _find(info, "permalink"), "hashtags_ok": "#" in caption}
        elif state.get("tries", 0) + 1 >= 3:
            result = {"error": _failed(res, err) or str(res)[:300]}  # a new container next time
        else:
            result = {"pending": state["pending"], "tries": state.get("tries", 0) + 1,
                      "error": _failed(res, err) or str(res)[:300]}
        return item_id, {"instagram": _record(item_id, "instagram", result)}

    with ThreadPoolExecutor(6) as ex:
        results = dict(ex.map(publish, pend))
    print(json.dumps(results, ensure_ascii=False))
    return results
