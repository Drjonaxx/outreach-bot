#!/usr/bin/env python3
"""
beingvortex News Agent
======================
Finds verified AI news and publishes posts to Threads (ES + EN).

Usage:
  python agent.py --dry-run      # Find news + show posts, do NOT publish
  python agent.py --once         # Find news + publish once, then exit
  python agent.py --schedule     # Publish every SCHEDULE_HOURS hours (default: 4)
  python agent.py --check-auth   # Verify your Threads credentials are working
"""

import argparse
import logging
import os
import sys
import time

import schedule
from dotenv import load_dotenv

load_dotenv()

# Configure logging before importing local modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("beingvortex")

from core import tracker  # noqa: E402
from core.news_finder import find_ai_news  # noqa: E402
from core.post_writer import generate_posts  # noqa: E402
from core.threads_client import ThreadsClient  # noqa: E402

# Delay between posting ES and EN versions of the same story (seconds)
INTER_POST_DELAY = 30
# Delay between different news items (seconds)
INTER_ITEM_DELAY = 60


# ────────────────────────────────────────────────────────────────────────────
#  Core logic
# ────────────────────────────────────────────────────────────────────────────

def run_once(dry_run: bool = False) -> None:
    log.info("=" * 60)
    log.info(f"Starting run {'(DRY RUN)' if dry_run else ''}")
    log.info("=" * 60)

    max_news = int(os.getenv("MAX_NEWS_ITEMS", "5"))
    max_per_run = int(os.getenv("MAX_POSTS_PER_RUN", "2"))

    # Pass recent titles so Claude doesn't re-post the same topics
    already_posted = tracker.recent_titles(n=20)

    # ── 1. Find news ─────────────────────────────────────────────────────
    log.info(f"Searching for up to {max_news} verified AI news items...")
    news_items = find_ai_news(max_items=max_news, already_posted=already_posted)

    if not news_items:
        log.warning("No verified news items found this run — nothing to post")
        return

    log.info(f"Found {len(news_items)} verified items")

    # ── 2. Filter already-published URLs ─────────────────────────────────
    new_items = [n for n in news_items if not tracker.is_published(n["url"])]
    log.info(f"{len(new_items)} items not yet published")

    if not new_items:
        log.info("All found items were already published — skipping")
        return

    items_to_post = new_items[:max_per_run]

    # ── 3. Generate + publish ─────────────────────────────────────────────
    threads = ThreadsClient() if not dry_run else None

    for idx, item in enumerate(items_to_post):
        log.info(f"[{idx + 1}/{len(items_to_post)}] Processing: {item['title']}")
        log.info(f"  Source: {item.get('source_name')} | {item.get('url', '')[:80]}")

        posts = generate_posts(item)

        es_text = posts.get("es", "").strip()
        en_text = posts.get("en", "").strip()

        if not es_text or not en_text:
            log.error(f"  Post generation failed for: {item['title']} — skipping")
            continue

        log.info(f"  ES ({len(es_text)} chars): {es_text[:100]}...")
        log.info(f"  EN ({len(en_text)} chars): {en_text[:100]}...")

        if dry_run:
            _print_dry_run(item, es_text, en_text)
            continue

        # Publish
        post_ids: dict[str, str] = {}

        es_id = threads.publish_text(es_text)
        if es_id:
            log.info(f"  ✓ Published ES post (id: {es_id})")
            post_ids["es"] = es_id
        else:
            log.error(f"  ✗ ES publish failed for: {item['title']}")

        time.sleep(INTER_POST_DELAY)

        en_id = threads.publish_text(en_text)
        if en_id:
            log.info(f"  ✓ Published EN post (id: {en_id})")
            post_ids["en"] = en_id
        else:
            log.error(f"  ✗ EN publish failed for: {item['title']}")

        if post_ids:
            tracker.mark_published(item["url"], item["title"], post_ids)
            log.info(f"  Marked as published")
        else:
            log.error(f"  Both posts failed — not marking as published")

        # Wait before next item
        if idx < len(items_to_post) - 1:
            log.info(f"  Waiting {INTER_ITEM_DELAY}s before next item...")
            time.sleep(INTER_ITEM_DELAY)

    log.info("Run complete")


def _print_dry_run(item: dict, es_text: str, en_text: str) -> None:
    sep = "─" * 50
    print(f"\n{sep}")
    print(f"NEWS: {item['title']}")
    print(f"URL:  {item.get('url', 'n/a')}")
    print(sep)
    print("🇪🇸 SPANISH POST:")
    print(es_text)
    print(f"({len(es_text)} chars)")
    print()
    print("🇺🇸 ENGLISH POST:")
    print(en_text)
    print(f"({len(en_text)} chars)")
    print(sep)


# ────────────────────────────────────────────────────────────────────────────
#  Auth check
# ────────────────────────────────────────────────────────────────────────────

def check_auth() -> None:
    log.info("Checking Threads credentials...")
    try:
        client = ThreadsClient()
        profile = client.whoami()
        log.info(f"✓ Connected as: @{profile.get('username', '?')} (id: {profile.get('id')})")
        print(f"\nSuccess! Connected to Threads as @{profile.get('username', '?')}")
    except KeyError:
        print("\nERROR: THREADS_ACCESS_TOKEN or THREADS_USER_ID not set.")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: Could not connect to Threads API: {exc}")
        print("Check that your THREADS_ACCESS_TOKEN is valid and not expired.")
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="beingvortex AI News Agent — posts verified AI news to Threads"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Find news and show generated posts without publishing",
    )
    group.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit",
    )
    group.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a schedule (every SCHEDULE_HOURS hours, default 4)",
    )
    group.add_argument(
        "--check-auth",
        action="store_true",
        help="Verify Threads API credentials",
    )
    args = parser.parse_args()

    # Default to --dry-run if nothing specified (safe default)
    if not any([args.dry_run, args.once, args.schedule, args.check_auth]):
        log.info("No mode specified — defaulting to --dry-run (safe mode)")
        args.dry_run = True

    if args.check_auth:
        check_auth()
        return

    if args.dry_run:
        log.info("DRY RUN mode — no posts will be published")
        run_once(dry_run=True)
        return

    if args.once:
        run_once(dry_run=False)
        return

    if args.schedule:
        hours = int(os.getenv("SCHEDULE_HOURS", "4"))
        log.info(f"Schedule mode: running every {hours} hour(s)")

        # Run immediately on start
        run_once(dry_run=False)

        # Then schedule
        schedule.every(hours).hours.do(run_once, dry_run=False)

        log.info(f"Next run in {hours} hour(s). Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    main()
