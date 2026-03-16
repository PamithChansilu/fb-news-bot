"""
news_fetcher.py — Fetches articles from RSS feeds and filters by keyword.
Returns a list of raw article dicts for further processing.
"""

import logging
import feedparser
from datetime import datetime, timezone
from config import RSS_FEEDS, KEYWORDS

logger = logging.getLogger(__name__)


def _is_relevant(text: str) -> bool:
    """
    Return True if the text contains at least one keyword
    from our war / finance topic list (case-insensitive).
    """
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def _parse_published(entry) -> datetime:
    """
    Try to extract a timezone-aware published datetime from an RSS entry.
    Falls back to 'now' if the field is missing or unparseable.
    """
    try:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)


def fetch_articles(posted_urls: set) -> list[dict]:
    """
    Pull articles from all configured RSS feeds.

    Parameters
    ----------
    posted_urls : set
        URLs already stored in the DB — used for quick dedup.

    Returns
    -------
    list of dicts with keys:
        title, url, summary, image_url, published_at, source
    Sorted newest-first.
    """
    articles = []

    for feed_url in RSS_FEEDS:
        try:
            logger.info("Fetching feed: %s", feed_url)
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    "Feed parse warning for %s: %s",
                    feed_url, feed.bozo_exception
                )

            source_name = feed.feed.get("title", feed_url)

            for entry in feed.entries:
                url = entry.get("link", "").strip()
                if not url:
                    continue

                # Skip already-posted articles
                if url in posted_urls:
                    continue

                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()

                # Filter: only include relevant war/finance articles
                combined_text = f"{title} {summary}"
                if not _is_relevant(combined_text):
                    continue

                # Try to grab the best image from the RSS entry
                image_url = _extract_image(entry)

                articles.append({
                    "title":        title,
                    "url":          url,
                    "summary":      summary,
                    "image_url":    image_url,
                    "published_at": _parse_published(entry),
                    "source":       source_name,
                })

        except Exception as exc:
            logger.error("Error fetching feed %s: %s", feed_url, exc)

    # Sort: newest articles first
    articles.sort(key=lambda a: a["published_at"], reverse=True)

    # Deduplicate by URL (across feeds)
    seen_urls = set()
    unique = []
    for art in articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique.append(art)

    logger.info("Fetched %d relevant new articles.", len(unique))
    return unique


def _extract_image(entry) -> str | None:
    """
    Try multiple RSS fields to find an image URL.
    Returns the URL string or None.
    """
    # 1. media:content or media:thumbnail (common in Reuters, BBC)
    media_content = entry.get("media_content", [])
    for media in media_content:
        url = media.get("url", "")
        if url and _looks_like_image(url):
            return url

    media_thumbnail = entry.get("media_thumbnail", [])
    for media in media_thumbnail:
        url = media.get("url", "")
        if url and _looks_like_image(url):
            return url

    # 2. enclosures (podcast-style image enclosure)
    for enc in entry.get("enclosures", []):
        url = enc.get("href", "") or enc.get("url", "")
        if url and _looks_like_image(url):
            return url

    # 3. links with image type
    for link in entry.get("links", []):
        if "image" in link.get("type", ""):
            return link.get("href", "") or None

    return None


def _looks_like_image(url: str) -> bool:
    """Quick check: does the URL point to an image file?"""
    return any(
        url.lower().endswith(ext)
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
    ) or "image" in url.lower()
