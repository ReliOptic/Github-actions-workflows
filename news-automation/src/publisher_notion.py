"""
publisher_notion.py — Save newsletter content to a Notion database page.

Requires environment variables:
  NOTION_TOKEN     — Integration token (secret_...)
  NOTION_DB_INBOX  — Target database ID (32-char hex or formatted UUID)
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_BLOCK_LENGTH = 2000  # Notion rich_text limit per block
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

KST = timezone(timedelta(hours=9))


def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _chunked_paragraph(text: str) -> list[dict]:
    """Split long text into Notion paragraph blocks (2000 char limit each)."""
    blocks = []
    for i in range(0, len(text), MAX_BLOCK_LENGTH):
        chunk = text[i : i + MAX_BLOCK_LENGTH]
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            }
        )
    return blocks


def _text_to_blocks(content: str) -> list[dict]:
    """
    Convert plain-text newsletter content into Notion blocks.
    Markdown-lite: lines starting with ## become heading_2, ## → heading_2, --- → divider.
    """
    blocks: list[dict] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading_text = stripped[3:]
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": heading_text[:2000]}}]
                    },
                }
            )
        elif stripped.startswith("─") or stripped.startswith("="):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif stripped.startswith("• ") or stripped.startswith("- "):
            bullet = stripped[2:]
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": bullet[:2000]}}]
                    },
                }
            )
        elif stripped:
            blocks.extend(_chunked_paragraph(stripped))
        # Empty lines → skip (Notion handles spacing)
    return blocks


def _create_page(token: str, db_id: str, title: str, content: str) -> dict:
    """Create a Notion page via API and return the response JSON."""
    now_kst = datetime.now(KST).isoformat()
    blocks = _text_to_blocks(content)

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
            "Status": {
                "select": {"name": "완료"}
            },
        },
        "children": blocks[:100],  # Notion limit: 100 blocks per request
    }

    url = f"{NOTION_API}/pages"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                headers=_notion_headers(token),
                data=json.dumps(payload),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            logger.error("Notion API HTTP error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except Exception as exc:
            logger.error("Notion API error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError("Notion page creation failed after all retries.")


def _append_blocks(token: str, page_id: str, content: str) -> None:
    """Append additional blocks to a page (for content > 100 blocks)."""
    blocks = _text_to_blocks(content)

    # Process in batches of 100
    for batch_start in range(0, len(blocks), 100):
        batch = blocks[batch_start : batch_start + 100]
        url = f"{NOTION_API}/blocks/{page_id}/children"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.patch(
                    url,
                    headers=_notion_headers(token),
                    data=json.dumps({"children": batch}),
                    timeout=30,
                )
                resp.raise_for_status()
                break
            except Exception as exc:
                logger.error("Notion append blocks error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)


def publish_to_notion(title: str, content: str) -> str:
    """
    Publish content to Notion and return the page URL.

    Args:
        title: Page title
        content: Full newsletter text

    Returns:
        Notion page URL (https://notion.so/...)
    """
    token = os.environ["NOTION_TOKEN"]
    db_id = os.environ["NOTION_DB_INBOX"]

    logger.info("Publishing to Notion: %s", title)
    page_data = _create_page(token, db_id, title, content)
    page_id = page_data.get("id", "")

    # If content produces more than 100 blocks, append remainder
    all_blocks = _text_to_blocks(content)
    if len(all_blocks) > 100:
        logger.info("Appending remaining %d blocks to Notion page.", len(all_blocks) - 100)
        remaining_content = "\n".join(content.splitlines()[100:])
        _append_blocks(token, page_id, remaining_content)

    # Build page URL
    page_url = page_data.get("url", f"https://notion.so/{page_id.replace('-', '')}")
    logger.info("Notion page created: %s", page_url)
    return page_url
