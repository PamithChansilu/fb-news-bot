"""
article_parser.py — Enriches raw RSS articles by scraping the full page.

Uses newspaper3k to extract:
  - Full article text  (for better summaries)
  - Top image URL      (higher quality than RSS thumbnails)
  - Authors            (optional metadata)

Falls back gracefully to RSS data if scraping fails.
"""

import logging
import requests
from config import REQUEST_TIMEOUT, USER_AGENT, SUMMARY_MAX_CHARS

logger = logging.getLogger(__name__)

# Lazy import — newspaper3k is optional but strongly recommended
try:
    from newspaper import Article as NewspaperArticle
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    logger.warning(
        "newspaper3k not installed. "
        "Install with: pip install newspaper3k  "
        "Falling back to RSS summaries only."
    )


def enrich_article(article: dict) -> dict:
    """
    Attempt to scrape the article page and enrich the dict with:
      - article['text']      : first SUMMARY_MAX_CHARS of the body
      - article['image_url'] : best available image (scrape > RSS)

    Always returns the article dict (modified in-place).
    """
    url = article.get("url", "")
    if not url:
        return article

    if NEWSPAPER_AVAILABLE:
        _enrich_with_newspaper(article, url)
    else:
        _enrich_with_requests(article, url)

    # Trim summary to configured length
    text = article.get("text") or article.get("summary", "")
    article["text"] = _trim_text(text)

    return article


# ── Private helpers ───────────────────────────────────────────────────────────

def _enrich_with_newspaper(article: dict, url: str):
    """Use newspaper3k for full text + top image extraction."""
    try:
        news = NewspaperArticle(url)
        news.config.browser_user_agent = USER_AGENT
        news.config.request_timeout    = REQUEST_TIMEOUT
        news.download()
        news.parse()

        if news.text:
            article["text"] = news.text

        # Prefer newspaper's top image if RSS didn't provide one
        if news.top_image and not article.get("image_url"):
            article["image_url"] = news.top_image
        elif news.top_image and _better_image(news.top_image, article.get("image_url", "")):
            article["image_url"] = news.top_image

    except Exception as exc:
        logger.debug("newspaper3k failed for %s: %s", url, exc)


def _enrich_with_requests(article: dict, url: str):
    """
    Minimal fallback: just fetch the page HTML and look for og:image
    (Open Graph image), which most news sites provide.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        # Parse og:image with a simple string search (no BeautifulSoup needed)
        og_start = html.find('property="og:image"')
        if og_start == -1:
            og_start = html.find("property='og:image'")
        if og_start != -1:
            content_start = html.find('content="', og_start)
            if content_start != -1:
                content_start += len('content="')
                content_end = html.find('"', content_start)
                og_image = html[content_start:content_end].strip()
                if og_image and not article.get("image_url"):
                    article["image_url"] = og_image

    except Exception as exc:
        logger.debug("Requests fallback failed for %s: %s", url, exc)


def _trim_text(text: str) -> str:
    """
    Trim article text to SUMMARY_MAX_CHARS.
    Tries to break at the last full sentence within the limit.
    """
    text = text.strip()
    if len(text) <= SUMMARY_MAX_CHARS:
        return text

    trimmed = text[:SUMMARY_MAX_CHARS]
    # Try to cut at the last sentence ending
    for sep in (". ", "! ", "? "):
        idx = trimmed.rfind(sep)
        if idx > SUMMARY_MAX_CHARS // 2:
            return trimmed[:idx + 1]

    # Fall back to word boundary
    idx = trimmed.rfind(" ")
    if idx > 0:
        return trimmed[:idx] + "…"
    return trimmed + "…"


def _better_image(new_url: str, existing_url: str) -> bool:
    """
    Heuristic: prefer larger/higher-res images.
    newspaper3k's top image is usually better than RSS thumbnails.
    """
    # Simple heuristic: newspaper images are often larger
    # RSS thumbnails often contain "thumb" or small dimensions in URL
    bad_signals = ("thumb", "icon", "logo", "16x", "32x", "48x", "64x")
    if any(s in existing_url.lower() for s in bad_signals):
        return True
    return False
