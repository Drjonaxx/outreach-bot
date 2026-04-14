"""
Fetches recent AI news from curated, trusted RSS feeds.
"""

import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Dict

TRUSTED_SOURCES = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/rss.xml"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/tag/artificial-intelligence/feed/"},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
    {"name": "ArXiv AI (cs.AI)", "url": "https://rss.arxiv.org/rss/cs.AI"},
]


def fetch_ai_news(hours_back: int = 48) -> List[Dict]:
    """
    Fetch recent AI articles from trusted sources.
    Returns list of dicts with title, summary, url, source, published.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []

    for source in TRUSTED_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:5]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                if published is None or published >= cutoff:
                    articles.append({
                        "title": entry.get("title", "").strip(),
                        "summary": entry.get("summary", "")[:600].strip(),
                        "url": entry.get("link", ""),
                        "source": source["name"],
                        "published": published.isoformat() if published else "unknown",
                    })
        except Exception as e:
            print(f"[news_fetcher] Error fetching {source['name']}: {e}")

    return articles
