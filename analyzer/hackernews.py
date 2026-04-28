import requests


_ALGOLIA = "https://hn.algolia.com/api/v1/search"


def analyze(keyword: str, limit: int = 20) -> dict:
    try:
        params = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": limit,
        }
        resp = requests.get(_ALGOLIA, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("hits", [])
        if not hits:
            return {
                "source": "HackerNews",
                "keyword": keyword,
                "posts_analyzed": 0,
                "top_posts": [],
                "error": None,
            }

        posts = []
        total_points = 0
        total_comments = 0
        domains = {}

        for h in hits:
            points = h.get("points") or 0
            comments = h.get("num_comments") or 0
            total_points += points
            total_comments += comments

            url = h.get("url", "")
            if url:
                try:
                    domain = url.split("/")[2]
                    domains[domain] = domains.get(domain, 0) + 1
                except IndexError:
                    pass

            posts.append({
                "title": h.get("title", ""),
                "points": points,
                "comments": comments,
                "url": url or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            })

        top_posts = sorted(posts, key=lambda x: x["points"], reverse=True)[:5]
        avg_points = round(total_points / len(hits), 1)
        avg_comments = round(total_comments / len(hits), 1)
        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "source": "HackerNews",
            "keyword": keyword,
            "posts_analyzed": len(hits),
            "avg_points": avg_points,
            "avg_comments": avg_comments,
            "top_posts": top_posts,
            "top_domains": [d for d, _ in top_domains],
            "error": None,
        }

    except Exception as e:
        return {"source": "HackerNews", "keyword": keyword, "error": str(e)}
