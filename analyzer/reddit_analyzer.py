import praw
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT


def _find_subreddits(reddit: praw.Reddit, keyword: str) -> list[str]:
    results = []
    try:
        for sub in reddit.subreddits.search(keyword, limit=5):
            results.append(sub.display_name)
    except Exception:
        pass
    return results or [keyword]


def analyze(keyword: str, limit: int = 25) -> dict:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return {
            "source": "Reddit",
            "keyword": keyword,
            "error": "Credenciales de Reddit no configuradas (ver .env.example)",
        }

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

        subreddits = _find_subreddits(reddit, keyword)
        sub_str = "+".join(subreddits[:5])

        posts = []
        total_upvotes = 0
        awards_total = 0
        flairs = {}
        hour_counts = {h: 0 for h in range(24)}

        for post in reddit.subreddit(sub_str).search(keyword, sort="top", time_filter="month", limit=limit):
            import datetime
            post_hour = datetime.datetime.utcfromtimestamp(post.created_utc).hour
            hour_counts[post_hour] += 1
            total_upvotes += post.score
            awards_total += post.total_awards_received

            if post.link_flair_text:
                flair = post.link_flair_text
                flairs[flair] = flairs.get(flair, 0) + 1

            posts.append({
                "title": post.title,
                "upvotes": post.score,
                "comments": post.num_comments,
                "url": f"https://reddit.com{post.permalink}",
            })

        top_posts = sorted(posts, key=lambda x: x["upvotes"], reverse=True)[:5]
        peak_hour = max(hour_counts, key=hour_counts.get)
        avg_upvotes = round(total_upvotes / len(posts), 0) if posts else 0
        top_flairs = sorted(flairs.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "source": "Reddit",
            "keyword": keyword,
            "subreddits_found": subreddits[:5],
            "posts_analyzed": len(posts),
            "avg_upvotes": avg_upvotes,
            "total_awards": awards_total,
            "peak_post_hour_utc": peak_hour,
            "top_posts": top_posts,
            "popular_flairs": [f for f, _ in top_flairs],
            "error": None,
        }

    except Exception as e:
        return {"source": "Reddit", "keyword": keyword, "error": str(e)}
