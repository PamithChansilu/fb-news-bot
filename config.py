"""
config.py — Central configuration for the Facebook News Bot.
All settings, tokens, and constants live here.
Set sensitive values via environment variables (recommended for production).
"""

import os

# ─────────────────────────────────────────────
# FACEBOOK GRAPH API CREDENTIALS
# Set these as environment variables in production!
# ─────────────────────────────────────────────
FACEBOOK_PAGE_ID      = os.getenv("FB_PAGE_ID", "YOUR_PAGE_ID_HERE")
FACEBOOK_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "YOUR_PAGE_ACCESS_TOKEN_HERE")

# Facebook Graph API base URL (v19 is stable as of 2025)
FB_API_VERSION = "v19.0"
FB_API_BASE    = f"https://graph.facebook.com/{FB_API_VERSION}"

# ─────────────────────────────────────────────
# RSS FEED SOURCES
# Trusted global war & finance news sources
# ─────────────────────────────────────────────
RSS_FEEDS = [
    # ── Reuters ──
    "https://feeds.reuters.com/reuters/worldNews",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/UKBusinessNews",

    # ── BBC ──
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.bbci.co.uk/news/business/rss.xml",

    # ── CNBC ──
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",    # World
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",     # Markets

    # ── Al Jazeera ──
    "https://www.aljazeera.com/xml/rss/all.xml",

    # ── The Guardian ──
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/business/rss",

    # ── Financial Times ──
    # FT requires auth for full feed; using public snippet feed
    "https://www.ft.com/rss/home",

    # ── Nasdaq / MarketWatch ──
    "https://www.marketwatch.com/rss/topstories",
]

# ─────────────────────────────────────────────
# KEYWORD FILTERS
# Articles must contain at least one of these
# to be considered relevant.
# ─────────────────────────────────────────────
KEYWORDS = [
    # War / Military
    "war", "conflict", "military", "airstrike", "missile", "drone",
    "invasion", "troops", "offensive", "ceasefire", "battle", "strike",
    "NATO", "Russia", "Ukraine", "Gaza", "Israel", "Hamas", "Iran",
    "sanctions", "weapons", "defense", "pentagon", "army", "navy",
    # Finance / Economy
    "oil", "crude", "energy", "gas", "OPEC", "market", "stocks",
    "economy", "inflation", "recession", "dollar", "euro", "gold",
    "interest rate", "federal reserve", "Fed", "GDP", "debt",
    "geopolitics", "trade war", "tariff", "supply chain",
]

# ─────────────────────────────────────────────
# POSTING SCHEDULE
# ─────────────────────────────────────────────
MAX_POSTS_PER_DAY = 8          # Hard cap on daily posts
POST_INTERVAL_HOURS = 3        # Minimum hours between posts
FETCH_INTERVAL_MINUTES = 60    # How often to check for new articles

# ─────────────────────────────────────────────
# STORAGE
# ─────────────────────────────────────────────
DB_PATH = "posted_articles.db"   # SQLite database file path

# ─────────────────────────────────────────────
# ARTICLE EXTRACTION
# ─────────────────────────────────────────────
SUMMARY_MAX_CHARS = 220          # Max caption body length
REQUEST_TIMEOUT   = 15           # HTTP request timeout in seconds
USER_AGENT = (
    "Mozilla/5.0 (compatible; NewsBot/1.0; "
    "+https://github.com/your-username/fb-news-bot)"
)

# ─────────────────────────────────────────────
# HASHTAG SETS
# Automatically appended to every post
# ─────────────────────────────────────────────
DEFAULT_HASHTAGS = (
    "#WarNews #Geopolitics #GlobalMarkets "
    "#BreakingNews #Finance #WorldNews"
)
