"""
dedup.py — Deduplication of articles using URL normalization and title similarity.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collector import Article


def _normalize_url(url: str, strip_params: list[str]) -> str:
    """Strip tracking query parameters and normalize URL."""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
    for param in strip_params:
        query.pop(param, None)
    new_query = urllib.parse.urlencode(query, doseq=True)
    normalized = parsed._replace(query=new_query, fragment="").geturl()
    # Remove trailing slash for consistency
    return normalized.rstrip("/").lower()


def _tokenize(title: str) -> set[str]:
    """Simple word-tokenizer for title similarity."""
    title = title.lower()
    # Remove punctuation
    title = re.sub(r"[^\w\s]", "", title)
    words = title.split()
    # Remove very short words (articles/prepositions)
    return {w for w in words if len(w) > 2}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def deduplicate(articles: list["Article"], config_path: str, similarity_threshold: float = 0.65) -> list["Article"]:
    """
    Remove duplicate articles.
    Dedup strategy:
      1. Exact URL match (after normalization)
      2. Title Jaccard similarity >= threshold
    Returns a deduplicated list preserving Tier 1 articles preferentially.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    strip_params: list[str] = config.get("url_strip_params", [])

    # Sort: Tier 1 first so they are kept, Tier 2 dropped if duplicate
    sorted_articles = sorted(articles, key=lambda a: a.tier)

    seen_urls: set[str] = set()
    seen_token_sets: list[set[str]] = []
    unique: list["Article"] = []

    for article in sorted_articles:
        norm_url = _normalize_url(article.url, strip_params)
        if norm_url in seen_urls:
            continue

        tokens = _tokenize(article.title)
        is_dup = any(
            _jaccard_similarity(tokens, existing) >= similarity_threshold
            for existing in seen_token_sets
        )
        if is_dup:
            continue

        seen_urls.add(norm_url)
        seen_token_sets.append(tokens)
        unique.append(article)

    return unique
