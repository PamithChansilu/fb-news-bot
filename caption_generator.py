"""
caption_generator.py — Generates engaging Facebook post captions.

Combines:
  - A topic-appropriate emoji header
  - The article title
  - A short summary
  - The article link
  - Relevant hashtags

All output is in clear international English.
"""

import re
import logging
from config import DEFAULT_HASHTAGS, SUMMARY_MAX_CHARS

logger = logging.getLogger(__name__)


# ── Topic detection mappings ──────────────────────────────────────────────────
# Each entry: (keywords_list, emoji_header, topic_label)
TOPIC_RULES = [
    (
        ["ceasefire", "peace", "negotiations", "talks", "treaty", "agreement"],
        "🕊️", "PEACE TALKS"
    ),
    (
        ["nuclear", "nuke", "radiation", "atomic", "ICBM", "warhead"],
        "☢️", "NUCLEAR ALERT"
    ),
    (
        ["airstrike", "missile", "drone", "bombing", "strike", "attack", "rocket"],
        "💥", "MILITARY STRIKE"
    ),
    (
        ["war", "invasion", "offensive", "battle", "conflict", "troops", "military"],
        "⚔️", "WAR UPDATE"
    ),
    (
        ["sanction", "ban", "embargo", "restriction", "penalty"],
        "🚫", "SANCTIONS"
    ),
    (
        ["oil", "crude", "energy", "OPEC", "gas", "refinery", "pipeline", "fuel"],
        "🛢️", "ENERGY MARKETS"
    ),
    (
        ["gold", "inflation", "dollar", "euro", "currency", "forex", "bitcoin"],
        "💱", "CURRENCY & COMMODITIES"
    ),
    (
        ["stock", "market", "wall street", "nasdaq", "dow", "s&p", "shares", "equity"],
        "📈", "MARKETS"
    ),
    (
        ["economy", "gdp", "recession", "growth", "federal reserve", "fed", "rate", "debt"],
        "💰", "ECONOMY"
    ),
    (
        ["geopolit", "nato", "un ", "united nations", "summit", "g7", "g20"],
        "🌍", "GEOPOLITICS"
    ),
    (
        ["defense", "pentagon", "weapon", "arms", "fighter jet", "submarine", "carrier"],
        "🪖", "DEFENSE"
    ),
]

FALLBACK_EMOJI  = "📰"
FALLBACK_LABEL  = "WORLD NEWS"


def generate_caption(article: dict) -> str:
    """
    Build the full Facebook post caption for an article.

    Parameters
    ----------
    article : dict
        Must have keys: title, url, text (or summary), source

    Returns
    -------
    str — ready-to-post caption
    """
    title    = article.get("title", "").strip()
    url      = article.get("url", "").strip()
    body     = (article.get("text") or article.get("summary", "")).strip()
    source   = article.get("source", "").strip()

    # Detect topic for emoji + header
    emoji, topic_label = _detect_topic(f"{title} {body}")

    # Build the caption body text (short, punchy)
    body_lines = _format_body(title, body)

    # Auto-generate hashtags based on detected keywords
    hashtags = _generate_hashtags(f"{title} {body}")

    # Assemble final caption
    lines = [
        f"{emoji} {topic_label}",
        "",
        body_lines,
        "",
        f"🔗 Read more: {url}",
        "",
        f"📡 Source: {source}" if source else "",
        "",
        hashtags,
    ]

    caption = "\n".join(line for line in lines if line is not None)
    logger.debug("Generated caption (%d chars) for: %s", len(caption), title[:60])
    return caption.strip()


# ── Private helpers ───────────────────────────────────────────────────────────

def _detect_topic(text: str) -> tuple[str, str]:
    """Match text against topic rules; return (emoji, label)."""
    text_lower = text.lower()
    for keywords, emoji, label in TOPIC_RULES:
        if any(kw.lower() in text_lower for kw in keywords):
            return emoji, label
    return FALLBACK_EMOJI, FALLBACK_LABEL


def _format_body(title: str, summary: str) -> str:
    """
    Return a 2–3 line formatted body.
    Uses the title as the headline and the summary as context.
    """
    # Clean HTML tags from summary (some feeds include them)
    clean_summary = re.sub(r"<[^>]+>", "", summary).strip()
    clean_summary = re.sub(r"\s+", " ", clean_summary)

    # Trim summary to max length
    if len(clean_summary) > SUMMARY_MAX_CHARS:
        cut = clean_summary[:SUMMARY_MAX_CHARS]
        last_space = cut.rfind(" ")
        clean_summary = (cut[:last_space] + "…") if last_space > 0 else cut + "…"

    if clean_summary and clean_summary.lower() not in title.lower():
        return f"{title}\n\n{clean_summary}"
    return title


def _generate_hashtags(text: str) -> str:
    """
    Build a hashtag string based on detected keywords in the text.
    Always includes default hashtags; adds topic-specific ones.
    """
    text_lower = text.lower()
    extra_tags = []

    tag_rules = {
        "#Ukraine":       ["ukraine", "kyiv", "zelensky"],
        "#Russia":        ["russia", "moscow", "putin", "kremlin"],
        "#Gaza":          ["gaza", "hamas", "palestin"],
        "#Israel":        ["israel", "idf", "tel aviv"],
        "#Iran":          ["iran", "tehran"],
        "#NATO":          ["nato"],
        "#OilMarkets":    ["oil", "crude", "opec", "brent"],
        "#EnergyNews":    ["energy", "gas", "pipeline", "lng"],
        "#WallStreet":    ["wall street", "nasdaq", "dow", "s&p 500"],
        "#FederalReserve":["federal reserve", "fed", "interest rate"],
        "#GoldMarket":    ["gold", "silver", "precious metals"],
        "#Sanctions":     ["sanction", "embargo"],
        "#DefenseNews":   ["defense", "pentagon", "weapon", "arms"],
        "#BreakingNews":  ["breaking", "urgent", "developing"],
    }

    for tag, keywords in tag_rules.items():
        if any(kw in text_lower for kw in keywords):
            extra_tags.append(tag)

    # Combine default + specific (keep reasonable length)
    all_tags = DEFAULT_HASHTAGS
    if extra_tags:
        all_tags = " ".join(extra_tags[:4]) + " " + DEFAULT_HASHTAGS

    return all_tags
