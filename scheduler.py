"""
scheduler.py — Controls when and how many articles get posted.

Enforces:
  - MAX_POSTS_PER_DAY hard cap
  - Minimum gap between consecutive posts
  - Spreading posts across the day
  - Preferred posting hours (peak global audience times)
"""

import logging
from datetime import datetime, timezone, timedelta
from config import MAX_POSTS_PER_DAY, POST_INTERVAL_HOURS

logger = logging.getLogger(__name__)

# UTC hours considered "good" posting times
# Covers US morning, Europe daytime, Asia evening
PREFERRED_UTC_HOURS = list(range(6, 22))  # 06:00–21:59 UTC

# Track last post time in memory (also stored in DB for persistence)
_last_post_time: datetime | None = None


def can_post_now(posts_today: int) -> bool:
    """
    Return True if it's safe to post right now, based on:
      1. Daily cap not exceeded
      2. Enough time since the last post
      3. Currently within preferred UTC hours
    """
    global _last_post_time

    now_utc = datetime.now(timezone.utc)

    # 1. Check daily limit
    if posts_today >= MAX_POSTS_PER_DAY:
        logger.info(
            "Daily limit reached (%d/%d). Skipping until tomorrow.",
            posts_today, MAX_POSTS_PER_DAY
        )
        return False

    # 2. Check minimum interval between posts
    if _last_post_time is not None:
        elapsed = now_utc - _last_post_time
        min_gap = timedelta(hours=POST_INTERVAL_HOURS)
        if elapsed < min_gap:
            remaining = min_gap - elapsed
            logger.info(
                "Too soon since last post. Next post in %dm.",
                int(remaining.total_seconds() / 60)
            )
            return False

    # 3. Check preferred posting hours
    if now_utc.hour not in PREFERRED_UTC_HOURS:
        logger.info(
            "Outside preferred posting hours (current UTC: %02d:00). Skipping.",
            now_utc.hour
        )
        return False

    return True


def record_post_time():
    """Call this immediately after a successful post."""
    global _last_post_time
    _last_post_time = datetime.now(timezone.utc)
    logger.debug("Last post time updated to %s", _last_post_time.isoformat())


def next_run_info(posts_today: int) -> str:
    """
    Return a human-readable string explaining when the next post
    is expected. Useful for logging / monitoring.
    """
    global _last_post_time

    now_utc = datetime.now(timezone.utc)

    if posts_today >= MAX_POSTS_PER_DAY:
        tomorrow = (now_utc + timedelta(days=1)).replace(
            hour=PREFERRED_UTC_HOURS[0], minute=0, second=0, microsecond=0
        )
        return f"Daily limit hit. Next window: {tomorrow.strftime('%Y-%m-%d %H:%M UTC')}"

    if _last_post_time:
        earliest = _last_post_time + timedelta(hours=POST_INTERVAL_HOURS)
        if earliest > now_utc:
            return f"Next post earliest: {earliest.strftime('%H:%M UTC')}"

    return "Ready to post."
