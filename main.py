"""
main.py — Entry point for the Facebook News Bot.

Orchestration flow (runs every FETCH_INTERVAL_MINUTES):
  1. Initialise database
  2. Verify Facebook credentials
  3. Fetch articles from RSS feeds (keyword-filtered)
  4. For each article (newest first):
       a. Check posting rules (daily cap, interval, hours)
       b. Enrich article (scrape full text + better image)
       c. Generate caption
       d. Post to Facebook
       e. Mark as posted in DB
  5. Sleep and repeat

Run directly:  python main.py
Or via cron:   */60 * * * * cd /path/to/bot && python main.py
"""

import logging
import time
import schedule
from datetime import datetime, timezone

# ── Local modules ─────────────────────────────────────────────────────────────
import storage
import news_fetcher
import article_parser
import caption_generator
import facebook_poster
import scheduler
from config import FETCH_INTERVAL_MINUTES, MAX_POSTS_PER_DAY

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),                          # Console
        logging.FileHandler("bot.log", encoding="utf-8") # Log file
    ],
)
logger = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────────────
# CORE JOB
# ─────────────────────────────────────────────────────────────────────────────

def run_bot():
    """
    Main job: fetch → filter → post.
    Called on schedule and also once at startup.
    """
    logger.info("=" * 60)
    logger.info("Bot cycle started at %s UTC", datetime.now(timezone.utc).strftime("%H:%M:%S"))

    # How many posts have we made today?
    posts_today = storage.get_posts_today()
    logger.info("Posts today: %d / %d", posts_today, MAX_POSTS_PER_DAY)

    # Fast-exit if we've already hit today's cap
    if posts_today >= MAX_POSTS_PER_DAY:
        logger.info("Daily limit reached. Sleeping until tomorrow.")
        return

    # Fetch articles (excluding already-posted URLs)
    posted_urls = storage.get_recent_posted_urls()
    articles    = news_fetcher.fetch_articles(posted_urls)

    if not articles:
        logger.info("No new relevant articles found this cycle.")
        return

    logger.info("Processing %d candidate articles…", len(articles))

    posted_this_cycle = 0

    for article in articles:
        # Re-check limits on every iteration (another thread could have posted)
        posts_today = storage.get_posts_today()

        if not scheduler.can_post_now(posts_today):
            logger.info(
                "Posting paused. %s",
                scheduler.next_run_info(posts_today)
            )
            break

        # ── Enrich ────────────────────────────────────────────────────────────
        logger.info("Enriching: %s", article["title"][:80])
        article = article_parser.enrich_article(article)

        # ── Generate caption ──────────────────────────────────────────────────
        caption = caption_generator.generate_caption(article)
        logger.debug("Caption preview:\n%s", caption[:200])

        # ── Post to Facebook ──────────────────────────────────────────────────
        logger.info("Posting to Facebook…")
        post_id = facebook_poster.post_article(article, caption)

        if post_id:
            storage.mark_posted(
                url       = article["url"],
                title     = article["title"],
                fb_post_id= post_id,
            )
            scheduler.record_post_time()
            posted_this_cycle += 1
            logger.info(
                "✅ Posted (%d this cycle): %s",
                posted_this_cycle, article["title"][:70]
            )
        else:
            # Mark as seen even on failure to avoid retrying bad articles
            storage.mark_posted(
                url   = article["url"],
                title = article["title"],
                fb_post_id = "FAILED",
            )
            logger.warning("Post failed for: %s", article["title"][:70])

        # Only post one article per cycle — next article posts next hour
        break

    logger.info(
        "Cycle complete. Posted %d article(s). Next run in %d min.",
        posted_this_cycle, FETCH_INTERVAL_MINUTES
    )


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────────────────

def main():
    logger.info("🚀 Facebook News Bot starting up…")

    # Initialise SQLite database
    storage.init_db()

    # Verify Facebook API credentials before doing anything
    if not facebook_poster.verify_credentials():
        logger.critical(
            "❌ Facebook credentials invalid! "
            "Check FB_PAGE_ID and FB_ACCESS_TOKEN env vars. Exiting."
        )
        return

    logger.info("✅ Startup checks passed. Scheduling job every %d minutes.", FETCH_INTERVAL_MINUTES)

    # Run once immediately at startup
    run_bot()

    # Then run on schedule
    schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(run_bot)

    logger.info("⏰ Scheduler running. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()
