from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY


def analyze(keyword: str, max_results: int = 20) -> dict:
    if not YOUTUBE_API_KEY:
        return {
            "source": "YouTube",
            "keyword": keyword,
            "error": "YOUTUBE_API_KEY no configurada (ver .env.example)",
        }

    try:
        yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        search_resp = yt.search().list(
            q=keyword,
            part="snippet",
            type="video",
            order="viewCount",
            maxResults=max_results,
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        if not video_ids:
            return {
                "source": "YouTube",
                "keyword": keyword,
                "videos_analyzed": 0,
                "top_videos": [],
                "error": None,
            }

        stats_resp = yt.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics",
        ).execute()

        videos = []
        total_views = 0
        total_likes = 0
        total_comments = 0
        tags_count = {}
        channels = {}

        for item in stats_resp.get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            total_views += views
            total_likes += likes
            total_comments += comments

            for tag in snippet.get("tags", []):
                t = tag.lower()
                tags_count[t] = tags_count.get(t, 0) + 1

            ch = snippet.get("channelTitle", "")
            channels[ch] = channels.get(ch, 0) + views

            videos.append({
                "title": snippet.get("title", ""),
                "channel": ch,
                "views": views,
                "likes": likes,
                "url": f"https://youtu.be/{item['id']}",
            })

        top_videos = sorted(videos, key=lambda x: x["views"], reverse=True)[:5]
        top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:10]
        top_channels = sorted(channels.items(), key=lambda x: x[1], reverse=True)[:5]
        n = len(videos)

        return {
            "source": "YouTube",
            "keyword": keyword,
            "videos_analyzed": n,
            "avg_views": round(total_views / n) if n else 0,
            "avg_likes": round(total_likes / n) if n else 0,
            "avg_comments": round(total_comments / n) if n else 0,
            "top_videos": top_videos,
            "top_tags": [t for t, _ in top_tags],
            "top_channels": [c for c, _ in top_channels],
            "error": None,
        }

    except Exception as e:
        return {"source": "YouTube", "keyword": keyword, "error": str(e)}
