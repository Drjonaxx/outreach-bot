from newsapi import NewsApiClient
from config import NEWS_API_KEY
from datetime import datetime, timedelta


def analyze(keyword: str, days_back: int = 30, page_size: int = 20) -> dict:
    if not NEWS_API_KEY:
        return {
            "source": "NewsAPI",
            "keyword": keyword,
            "error": "NEWS_API_KEY no configurada (ver .env.example)",
        }

    try:
        client = NewsApiClient(api_key=NEWS_API_KEY)
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        response = client.get_everything(
            q=keyword,
            from_param=from_date,
            language="es",
            sort_by="popularity",
            page_size=page_size,
        )

        articles = response.get("articles", [])

        if not articles:
            response = client.get_everything(
                q=keyword,
                from_param=from_date,
                sort_by="popularity",
                page_size=page_size,
            )
            articles = response.get("articles", [])

        if not articles:
            return {
                "source": "NewsAPI",
                "keyword": keyword,
                "articles_analyzed": 0,
                "total_results": 0,
                "top_articles": [],
                "error": None,
            }

        sources = {}
        day_counts = {}
        top_articles = []

        for art in articles:
            source_name = art.get("source", {}).get("name", "Desconocido")
            sources[source_name] = sources.get(source_name, 0) + 1

            pub = art.get("publishedAt", "")
            if pub:
                day = pub[:10]
                day_counts[day] = day_counts.get(day, 0) + 1

            top_articles.append({
                "title": art.get("title", ""),
                "source": source_name,
                "url": art.get("url", ""),
                "published": pub[:10] if pub else "",
            })

        top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]
        busiest_day = max(day_counts, key=day_counts.get) if day_counts else None

        return {
            "source": "NewsAPI",
            "keyword": keyword,
            "articles_analyzed": len(articles),
            "total_results": response.get("totalResults", 0),
            "top_articles": top_articles[:5],
            "top_sources": [s for s, _ in top_sources],
            "busiest_news_day": busiest_day,
            "error": None,
        }

    except Exception as e:
        return {"source": "NewsAPI", "keyword": keyword, "error": str(e)}
