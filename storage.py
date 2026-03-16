"""
storage.py — SQLite-backed storage for tracking posted articles.
Prevents the bot from reposting the same article twice.
"""

import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def init_db():
    """
    Create the database and tables if they don't exist yet.
    Call this once at startup.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table: tracks every article URL we've seen or posted
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posted_articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT    UNIQUE NOT NULL,
            title       TEXT,
            posted_at   TEXT,           -- ISO timestamp
            fb_post_id  TEXT            -- Facebook post ID returned by Graph API
        )
    """)

    # Table: daily post counter (to enforce MAX_POSTS_PER_DAY)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date        TEXT PRIMARY KEY,   -- YYYY-MM-DD
            post_count  INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", DB_PATH)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_conn():
    return sqlite3.connect(DB_PATH)


def is_duplicate(url: str) -> bool:
    """Return True if this article URL has already been stored."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM posted_articles WHERE url = ?", (url,)
    ).fetchone()
    conn.close()
    return row is not None


def mark_posted(url: str, title: str, fb_post_id: str = ""):
    """Record that we've successfully posted this article."""
    now = datetime.utcnow().isoformat()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO posted_articles
               (url, title, posted_at, fb_post_id)
               VALUES (?, ?, ?, ?)""",
            (url, title, now, fb_post_id),
        )
        # Increment today's post counter
        conn.execute(
            """INSERT INTO daily_stats (date, post_count) VALUES (?, 1)
               ON CONFLICT(date) DO UPDATE SET post_count = post_count + 1""",
            (today,),
        )
        conn.commit()
        logger.info("Marked as posted: %s", url)
    except Exception as exc:
        logger.error("DB error marking posted: %s", exc)
    finally:
        conn.close()


def get_posts_today() -> int:
    """Return the number of posts made today (UTC date)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = _get_conn()
    row = conn.execute(
        "SELECT post_count FROM daily_stats WHERE date = ?", (today,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_recent_posted_urls(limit: int = 500) -> set:
    """Return a set of recently posted URLs for fast dedup checks."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT url FROM posted_articles ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}
