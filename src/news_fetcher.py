"""
Fetches recent AI news from curated, trusted RSS feeds.
"""

import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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


def _parse_date(date_str: str):
    """Try to parse common RSS date formats."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _get_text(element, tag: str) -> str:
    """Get text from an XML child element."""
    ns_variants = [tag, f"{{{tag}"]
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def fetch_ai_news(hours_back: int = 48) -> List[Dict]:
    """
    Fetch recent AI articles from trusted sources.
    Returns list of dicts with title, summary, url, source, published.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)"}

    for source in TRUSTED_SOURCES:
        try:
            resp = requests.get(source["url"], headers=headers, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            # Handle both RSS and Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item") or root.findall(".//atom:entry", ns)

            for item in items[:5]:
                def tag(t):
                    el = item.find(t)
                    return el.text.strip() if el is not None and el.text else ""

                title = tag("title")
                summary = (tag("description") or tag("summary"))[:600]
                url = tag("link") or tag("guid")
                pub_str = tag("pubDate") or tag("published") or tag("updated")

                # Atom link is an attribute
                if not url:
                    link_el = item.find("atom:link", ns)
                    if link_el is not None:
                        url = link_el.get("href", "")

                published = _parse_date(pub_str)
                if published and published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)

                if published is None or published >= cutoff:
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "url": url,
                        "source": source["name"],
                        "published": published.isoformat() if published else "unknown",
                    })
        except Exception as e:
            print(f"[news_fetcher] Error fetching {source['name']}: {e}")

    return articles
