"""
Finds and verifies AI news using Claude + web_search.
Returns a list of verified news items ready for post generation.
"""

import json
import logging
import re
from datetime import datetime

import anthropic

log = logging.getLogger("beingvortex.news_finder")

# Claude uses this tool to search the web
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

_SYSTEM = """Eres un investigador de noticias de IA para la página "beingvortex".
Tu misión es encontrar noticias recientes y verificadas sobre inteligencia artificial.

REGLAS ESTRICTAS:
- Solo reporta hechos confirmados por fuentes confiables
- Nunca incluyas rumores, especulaciones o noticias no verificadas
- Si no puedes confirmar una noticia con al menos 2 fuentes, no la incluyas
- Prioriza anuncios oficiales, papers publicados y medios de tecnología reconocidos
"""


def _extract_json_array(text: str) -> list:
    """Extract the first JSON array found in text."""
    # Try to find a JSON array (handles markdown code blocks too)
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


def find_ai_news(max_items: int = 5, already_posted: list[str] | None = None) -> list[dict]:
    """
    Search for recent verified AI news.

    Returns a list of dicts with keys:
        title, summary_en, summary_es, url, source_name, category, verified
    """
    client = anthropic.Anthropic()
    today = datetime.now().strftime("%B %d, %Y")

    exclusion_note = ""
    if already_posted:
        titles_str = "\n".join(f"- {t}" for t in already_posted[-10:])
        exclusion_note = f"\n\nDO NOT include news about these already-posted topics:\n{titles_str}"

    prompt = f"""Today is {today}.

Search for the top {max_items} most important AI news from the last 48 hours.{exclusion_note}

TOPICS TO COVER:
- New AI model releases (GPT, Claude, Gemini, Llama, Mistral, Grok, etc.)
- AI research breakthroughs (published papers, new benchmarks, techniques)
- AI company news (product launches, funding rounds, acquisitions)
- AI policy and regulation (laws, bans, government actions)
- Practical AI tools making headlines

VERIFICATION RULES:
1. Search for each story from at least 2 reliable sources before including it
2. Only include news from the last 48 hours
3. Only include items where you found multiple confirmations (verified = true)
4. Reliable sources: official blogs (openai.com, anthropic.com, etc.), arXiv, TechCrunch, The Verge, Wired, Reuters, Bloomberg, IEEE

After searching, respond ONLY with a JSON array. No intro text, no markdown, just the array:

[
  {{
    "title": "Short factual headline in English (max 80 chars)",
    "summary_en": "2-3 sentences: what happened and why it matters. Factual, no hype.",
    "summary_es": "Lo mismo en español. 2-3 oraciones. Tono educativo, sin exageración.",
    "url": "https://primary-source-url.com/article",
    "source_name": "Name of primary source (e.g. OpenAI Blog, arXiv, TechCrunch)",
    "category": "model_release OR research OR company_news OR policy OR application",
    "verified": true
  }}
]

Include ONLY items where verified is true. If you find fewer than {max_items} verified stories, that is fine."""

    messages: list[dict] = [{"role": "user", "content": prompt}]

    # Agentic loop: Claude may call web_search multiple times (server-side)
    # We handle pause_turn in case the server-side loop needs more iterations.
    max_iterations = 8
    for attempt in range(max_iterations):
        log.debug(f"Claude API call (attempt {attempt + 1})")
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=_SYSTEM,
            tools=[_WEB_SEARCH_TOOL],
            messages=messages,
        )

        if response.stop_reason == "pause_turn":
            # Server-side tool loop needs to continue — append and re-send
            messages.append({"role": "assistant", "content": response.content})
            log.debug("pause_turn received, continuing...")
            continue

        # Extract text blocks from the final response
        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        full_text = "\n".join(text_parts)

        items = _extract_json_array(full_text)
        verified = [i for i in items if i.get("verified") is True]

        if verified:
            log.info(f"Found {len(verified)} verified news items")
        else:
            log.warning("No verified news items found in this run")

        return verified

    log.error("Reached max iterations without a final response")
    return []
