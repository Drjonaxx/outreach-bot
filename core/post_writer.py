"""
Generates Threads posts (ES + EN) from a verified news item.
Posts are capped at 480 chars (Threads limit is 500, we leave margin).
Tone: educational, direct, no hype — beingvortex style.
"""

import json
import logging
import re

import anthropic

log = logging.getLogger("beingvortex.post_writer")

MAX_CHARS = 480

_CATEGORY_HASHTAGS = {
    "model_release": {"es": "#NuevoModelo #IA", "en": "#NewModel #AI"},
    "research":      {"es": "#InvestigaciónIA #IA", "en": "#AIResearch #AI"},
    "company_news":  {"es": "#Tech #IA", "en": "#Tech #AI"},
    "policy":        {"es": "#RegulacionIA #IA", "en": "#AIPolicy #AI"},
    "application":   {"es": "#IA #Tecnología", "en": "#AI #Technology"},
}

_BASE_HASHTAGS = {"es": "#beingvortex", "en": "#beingvortex"}


def _hashtags(category: str) -> dict[str, str]:
    cat = _CATEGORY_HASHTAGS.get(category, {"es": "#IA", "en": "#AI"})
    return {
        "es": f"{cat['es']} {_BASE_HASHTAGS['es']}",
        "en": f"{cat['en']} {_BASE_HASHTAGS['en']}",
    }


def _extract_json_object(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def generate_posts(news_item: dict) -> dict[str, str]:
    """
    Generate a Threads post in Spanish and English for a news item.

    Returns: {"es": "...", "en": "..."}
    Both values are empty strings if generation fails.
    """
    client = anthropic.Anthropic()
    tags = _hashtags(news_item.get("category", ""))

    prompt = f"""Create two Threads posts for this verified AI news. Keep beingvortex's style: educational, direct, no hype.

NEWS:
Title: {news_item.get("title", "")}
Summary (EN): {news_item.get("summary_en", "")}
Summary (ES): {news_item.get("summary_es", "")}
Source: {news_item.get("source_name", "")}
Category: {news_item.get("category", "")}

RULES FOR EACH POST:
- Max {MAX_CHARS} characters total (count everything including hashtags and newlines)
- Start with the key fact — no "New:", "Breaking:", or clickbait openers
- Explain what happened and why it matters in 2-3 sentences
- Tone: clear, factual, educational. Assume the reader is curious but not an expert
- End with the source name on its own line: "Fuente: X" (ES) or "Source: X" (EN)
- Then add the hashtags on the final line
- At most 1 emoji, only if it genuinely adds clarity (not decoration)
- Do NOT include any URL

HASHTAGS TO USE:
Spanish post: {tags["es"]}
English post: {tags["en"]}

Respond ONLY with this JSON (no markdown, no intro):
{{"es": "texto completo del post en español", "en": "full text of the post in english"}}"""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        posts = _extract_json_object(text)

        es = posts.get("es", "").strip()
        en = posts.get("en", "").strip()

        # Enforce char limit — truncate at last full sentence if over
        if len(es) > MAX_CHARS:
            log.warning(f"ES post too long ({len(es)} chars), trimming")
            es = es[:MAX_CHARS].rsplit(".", 1)[0] + "."
        if len(en) > MAX_CHARS:
            log.warning(f"EN post too long ({len(en)} chars), trimming")
            en = en[:MAX_CHARS].rsplit(".", 1)[0] + "."

        return {"es": es, "en": en}

    except anthropic.APIError as exc:
        log.error(f"Anthropic API error generating posts: {exc}")
        return {"es": "", "en": ""}
