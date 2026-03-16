"""
facebook_poster.py — Posts photo+caption to a Facebook Page via Graph API.

Two posting strategies:
  1. post_with_image()  — uploads a remote image URL + caption (preferred)
  2. post_text_only()   — falls back to a link-post if no image is available

Facebook Graph API reference:
  https://developers.facebook.com/docs/graph-api/reference/page/photos/
"""

import logging
import requests
from config import (
    FACEBOOK_PAGE_ID,
    FACEBOOK_ACCESS_TOKEN,
    FB_API_BASE,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


def post_article(article: dict, caption: str) -> str | None:
    """
    High-level entry point: post an article to the Facebook page.

    Tries image post first; falls back to text/link post.

    Returns
    -------
    str — Facebook post ID if successful, None on failure.
    """
    image_url = article.get("image_url")

    if image_url:
        post_id = post_with_image(caption, image_url)
        if post_id:
            return post_id
        logger.warning("Image post failed, trying text-only post…")

    return post_text_only(caption)


def post_with_image(caption: str, image_url: str) -> str | None:
    """
    Upload a photo to the Facebook page with a caption.

    Uses the /PAGE_ID/photos endpoint with url= parameter.
    Facebook fetches the image from the URL directly — no download needed.

    Returns the new post ID or None on error.
    """
    endpoint = f"{FB_API_BASE}/{FACEBOOK_PAGE_ID}/photos"

    payload = {
        "url":           image_url,
        "caption":       caption,
        "access_token":  FACEBOOK_ACCESS_TOKEN,
        "published":     "true",
    }

    try:
        resp = requests.post(endpoint, data=payload, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        if resp.status_code == 200 and "id" in data:
            post_id = data["id"]
            logger.info("✅ Photo post published. Post ID: %s", post_id)
            return post_id
        else:
            _log_fb_error("post_with_image", data)
            return None

    except requests.RequestException as exc:
        logger.error("Network error posting image: %s", exc)
        return None


def post_text_only(caption: str) -> str | None:
    """
    Post a plain text/link update to the Facebook page feed.

    Used as a fallback when no image is available.

    Returns the new post ID or None on error.
    """
    endpoint = f"{FB_API_BASE}/{FACEBOOK_PAGE_ID}/feed"

    payload = {
        "message":       caption,
        "access_token":  FACEBOOK_ACCESS_TOKEN,
    }

    try:
        resp = requests.post(endpoint, data=payload, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        if resp.status_code == 200 and "id" in data:
            post_id = data["id"]
            logger.info("✅ Text post published. Post ID: %s", post_id)
            return post_id
        else:
            _log_fb_error("post_text_only", data)
            return None

    except requests.RequestException as exc:
        logger.error("Network error posting text: %s", exc)
        return None


def verify_credentials() -> bool:
    """
    Quick sanity-check: verify that the access token and page ID are valid.
    Call this at startup before attempting to post.

    Returns True if credentials look valid.
    """
    endpoint = f"{FB_API_BASE}/{FACEBOOK_PAGE_ID}"
    params = {
        "fields":        "name,id",
        "access_token":  FACEBOOK_ACCESS_TOKEN,
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        if "name" in data:
            logger.info(
                "✅ Facebook credentials OK. Page: '%s' (ID: %s)",
                data["name"], data["id"]
            )
            return True
        else:
            _log_fb_error("verify_credentials", data)
            return False

    except requests.RequestException as exc:
        logger.error("Network error verifying credentials: %s", exc)
        return False


# ── Private helpers ───────────────────────────────────────────────────────────

def _log_fb_error(context: str, response_data: dict):
    """Log a structured Facebook API error."""
    error = response_data.get("error", {})
    code    = error.get("code", "?")
    subcode = error.get("error_subcode", "")
    message = error.get("message", str(response_data))
    logger.error(
        "❌ Facebook API error in %s | Code: %s%s | %s",
        context, code,
        f"/{subcode}" if subcode else "",
        message,
    )
