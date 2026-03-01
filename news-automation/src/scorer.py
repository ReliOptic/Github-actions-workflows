"""
scorer.py — Article quality scoring: noise/spam/clickbait filtering + relevance scoring.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collector import Article

MIN_TITLE_LENGTH = 15
MIN_SUMMARY_LENGTH = 30


def _load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _has_noise_keyword(text: str, noise_keywords: list[str]) -> bool:
    """Return True if text contains any noise/spam keyword."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in noise_keywords)


def _is_clickbait(text: str, patterns: list[str]) -> bool:
    """Return True if text matches any clickbait regex pattern."""
    return any(re.search(p, text) for p in patterns)


def _score_article(article: "Article", config: dict) -> float:
    """
    Compute a quality score (0.0 – 1.0) for an article.
    Higher is better.
    Rules:
    - Tier 1 source: +0.3
    - Has non-empty summary: +0.2
    - Summary >= 100 chars: +0.1
    - Title length >= 20: +0.1
    - URL includes a path (not just domain root): +0.1
    - No noise keyword: +0.1
    - Not clickbait: +0.1
    """
    noise_keywords: list[str] = config.get("noise_keywords", [])
    clickbait_patterns: list[str] = config.get("clickbait_patterns", [])

    score = 0.0

    if article.tier == 1:
        score += 0.3

    summary = article.summary or ""
    if summary:
        score += 0.2
    if len(summary) >= 100:
        score += 0.1

    if len(article.title) >= 20:
        score += 0.1

    # URL has a path beyond just the root
    from urllib.parse import urlparse
    parsed = urlparse(article.url)
    if parsed.path and parsed.path != "/":
        score += 0.1

    if not _has_noise_keyword(article.title + " " + summary, noise_keywords):
        score += 0.1

    if not _is_clickbait(article.title, clickbait_patterns):
        score += 0.1

    return round(score, 3)


def filter_and_score(
    articles: list["Article"],
    config_path: str,
) -> list["Article"]:
    """
    Filter out low-quality articles and assign scores.
    Returns articles sorted by score descending.
    Articles failing hard quality gates are excluded entirely.
    """
    config = _load_config(config_path)
    noise_keywords: list[str] = config.get("noise_keywords", [])
    clickbait_patterns: list[str] = config.get("clickbait_patterns", [])

    passed: list[tuple[float, "Article"]] = []

    for article in articles:
        # Hard gates
        if len(article.title) < MIN_TITLE_LENGTH:
            continue
        if not article.url:
            continue
        # Noise keyword in title = hard reject
        if _has_noise_keyword(article.title, noise_keywords):
            continue
        # Clickbait in title = hard reject
        if _is_clickbait(article.title, clickbait_patterns):
            continue

        # Soft scoring
        score = _score_article(article, config)
        article.extra["score"] = score
        passed.append((score, article))

    passed.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in passed]
