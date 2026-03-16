"""
main_once.py — Single-cycle version for GitHub Actions / cron.

Instead of running forever (like main.py), this:
  1. Initialises the DB
  2. Verifies credentials
  3. Fetches + posts ONE article
  4. Exits cleanly

GitHub Actions calls this every hour via the cron schedule.
"""

import logging
import sys
from datetime import datetime, timezone

import storage
import news_fetcher
import article_parser
import caption_generator
import facebook_poster
import scheduler
from config import MAX_POSTS_PER_DAY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main_once")


def main():
    logger.info("=" * 60)
    logger.info(
        "One-shot cycle at %s UTC",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    )

    storage.init_db()

    if not facebook_poster.verify_credentials():
        logger.critical("Invalid Facebook credentials. Exiting.")
        sys.exit(1)

    posts_today = storage.get_posts_today()

    if not scheduler.can_post_now(posts_today):
        logger.info(
            "Not posting this cycle. %s",
            scheduler.next_run_info(posts_today),
        )
        sys.exit(0)

    posted_urls = storage.get_recent_posted_urls()
    articles    = news_fetcher.fetch_articles(posted_urls)

    if not articles:
        logger.info("No new relevant articles. Exiting.")
        sys.exit(0)

    # Post the single most recent relevant article
    article = articles[0]
    logger.info("Selected article: %s", article["title"][:80])

    article = article_parser.enrich_article(article)
    caption = caption_generator.generate_caption(article)

    post_id = facebook_poster.post_article(article, caption)

    if post_id:
        storage.mark_posted(
            url        = article["url"],
            title      = article["title"],
            fb_post_id = post_id,
        )
        scheduler.record_post_time()
        logger.info("✅ Successfully posted. FB Post ID: %s", post_id)
    else:
        # Still mark as seen to avoid infinite retry
        storage.mark_posted(
            url        = article["url"],
            title      = article["title"],
            fb_post_id = "FAILED",
        )
        logger.error("❌ Post failed. Article marked to skip next cycle.")
        sys.exit(1)


if __name__ == "__main__":
    main()
