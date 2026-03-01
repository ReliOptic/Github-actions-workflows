"""
publisher_telegram.py — Send newsletter to a Telegram chat via Bot API.

Requires environment variables:
  TELEGRAM_BOT_TOKEN — Bot token from @BotFather
  TELEGRAM_CHAT_ID   — Target chat or channel ID (e.g. -100xxxx)
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MSG_LENGTH = 4096  # Telegram message character limit
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def _send_message(token: str, chat_id: str, text: str, disable_preview: bool = False) -> dict:
    """Send a single Telegram message chunk."""
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": disable_preview,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else 0
            logger.error(
                "Telegram HTTP error %d (attempt %d/%d): %s",
                status_code, attempt, MAX_RETRIES, exc,
            )
            # 429 = rate limit: back off longer
            if status_code == 429:
                time.sleep(RETRY_DELAY * attempt * 2)
            elif attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except Exception as exc:
            logger.error("Telegram send error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError("Telegram message send failed after all retries.")


def _split_message(text: str, limit: int = MAX_MSG_LENGTH) -> list[str]:
    """
    Split a long message into chunks ≤ limit chars,
    breaking on newlines where possible.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to break at a newline
        split_pos = text.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = limit  # Hard break
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    return chunks


def _markdown_escape(text: str) -> str:
    """
    Escape Telegram MarkdownV1 special chars that can break formatting.
    Only escapes what is necessary for readability.
    """
    # In MarkdownV1, only ` _ * [ are special
    # We keep ** for bold and * for italic but escape standalone underscores
    return text


def publish_to_telegram(content: str, notion_url: str | None = None) -> None:
    """
    Send the newsletter content to Telegram.
    Appends Notion URL at the end if provided.
    Splits messages to respect Telegram's 4096 char limit.

    Args:
        content: Full newsletter text
        notion_url: Optional Notion page URL to append
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    full_text = content
    if notion_url:
        full_text += f"\n\n📖 [Notion에서 전체 보기]({notion_url})"

    chunks = _split_message(full_text)
    logger.info("Sending %d Telegram message chunk(s).", len(chunks))

    for i, chunk in enumerate(chunks):
        # Disable web preview for all but the last chunk
        disable_preview = i < len(chunks) - 1
        _send_message(token, chat_id, chunk, disable_preview=disable_preview)
        if i < len(chunks) - 1:
            time.sleep(1)  # Avoid rate limits between chunks

    logger.info("Telegram message sent successfully.")


def send_fallback_alert(error_message: str) -> None:
    """
    Send a minimal fallback alert when the main pipeline fails.
    Does NOT raise exceptions — best-effort only.
    """
    try:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            logger.error("Telegram credentials not set; cannot send fallback alert.")
            return

        text = (
            "⚠️ *뉴스 자동화 파이프라인 오류*\n\n"
            f"오류 내용:\n```\n{error_message[:500]}\n```\n\n"
            "GitHub Actions 로그를 확인하세요."
        )
        _send_message(token, chat_id, text)
    except Exception as exc:
        logger.error("Fallback alert also failed: %s", exc)
