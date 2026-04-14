#!/usr/bin/env python3
"""
AI News Outreach Bot
====================
Fetches recent AI news from trusted sources, has Claude verify and adapt
the content, then publishes automatically to LinkedIn and Threads in Spanish.

Run manually:    python agent.py
Run via cron:    see run.sh
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

from src.content_generator import generate_posts
from src.news_fetcher import fetch_ai_news
from src.poster import post_to_linkedin, post_to_threads


def run():
    log.info("=" * 50)
    log.info("AI Outreach Bot — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 50)

    # 1. Fetch recent AI news
    log.info("Obteniendo noticias de IA de fuentes confiables...")
    articles = fetch_ai_news(hours_back=48)
    log.info("Artículos encontrados: %d", len(articles))

    if not articles:
        log.warning("No se encontraron artículos recientes. Saliendo.")
        return

    # 2. Verify and generate posts with Claude
    log.info("Claude verificando contenido y generando posts...")
    result = generate_posts(articles)

    if not result:
        log.warning("No hay contenido válido para publicar hoy.")
        return

    title, source, linkedin_post, threads_post = result
    log.info("Artículo seleccionado: [%s] %s", source, title)

    # 3. Publish to LinkedIn
    try:
        log.info("Publicando en LinkedIn...")
        linkedin_result = post_to_linkedin(linkedin_post)
        log.info("LinkedIn OK — ID: %s", linkedin_result.get("id", "n/a"))
    except Exception as e:
        log.error("Error publicando en LinkedIn: %s", e)

    # 4. Publish to Threads
    try:
        log.info("Publicando en Threads...")
        threads_result = post_to_threads(threads_post)
        log.info("Threads OK — ID: %s", threads_result.get("id", "n/a"))
    except Exception as e:
        log.error("Error publicando en Threads: %s", e)

    log.info("Bot finalizado.")


if __name__ == "__main__":
    run()
