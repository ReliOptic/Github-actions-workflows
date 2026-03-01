"""
collector.py — RSS feed collector with Tier 1/Tier 2 fallback logic.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import feedparser
import requests
import yaml

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15  # seconds per feed fetch
MAX_ARTICLES_PER_FEED = 20


@dataclass
class Article:
    title: str
    url: str
    summary: str
    published: str
    source: str
    category: str
    tier: int
    extra: dict = field(default_factory=dict)


def _load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fetch_feed(feed_info: dict, category: str, tier: int, timeout: int = REQUEST_TIMEOUT) -> list[Article]:
    """Fetch a single RSS/Atom feed and return a list of Article objects."""
    articles: list[Article] = []
    url = feed_info["url"]
    name = feed_info.get("name", url)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except Exception as exc:
        logger.warning("Feed fetch failed [%s] %s: %s", name, url, exc)
        return []

    for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue

        summary = ""
        if hasattr(entry, "summary"):
            summary = entry.summary
        elif hasattr(entry, "description"):
            summary = entry.description
        # Strip HTML tags from summary
        summary = _strip_html(summary)[:500]

        published = getattr(entry, "published", getattr(entry, "updated", ""))

        articles.append(
            Article(
                title=title,
                url=link,
                summary=summary,
                published=published,
                source=name,
                category=category,
                tier=tier,
            )
        )

    logger.info("Fetched %d articles from [%s]", len(articles), name)
    return articles


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    import re
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text).strip()


def collect_articles(config_path: str, max_age_hours: int = 24) -> dict[str, list[Article]]:
    """
    Collect articles per category using Tier 1 feeds first.
    Falls back to Tier 2 if Tier 1 yields insufficient results.
    Returns {category_key: [Article]} dict.
    """
    config = _load_config(config_path)
    categories: dict[str, Any] = config.get("categories", {})
    results: dict[str, list[Article]] = {}

    for cat_key, cat_cfg in categories.items():
        select_count: int = cat_cfg.get("select_count", 3)
        feeds_cfg: dict = cat_cfg.get("feeds", {})
        tier1_feeds: list = feeds_cfg.get("tier1", [])
        tier2_feeds: list = feeds_cfg.get("tier2", [])

        articles: list[Article] = []

        # Tier 1
        for feed in tier1_feeds:
            fetched = _fetch_feed(feed, cat_key, tier=1)
            articles.extend(fetched)
            time.sleep(0.3)

        # Use Tier 2 if Tier 1 is insufficient
        if len(articles) < select_count * 2:
            logger.warning("[%s] Tier 1 insufficient (%d). Trying Tier 2.", cat_key, len(articles))
            for feed in tier2_feeds:
                fetched = _fetch_feed(feed, cat_key, tier=2)
                articles.extend(fetched)
                time.sleep(0.3)

        results[cat_key] = articles
        logger.info("[%s] Total collected: %d articles", cat_key, len(articles))

    return results
