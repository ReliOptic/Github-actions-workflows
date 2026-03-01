"""
weekly_recap.py — Summarizes the week's output into a unified action plan using Gemini. (Feature B)
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from notion_client import query_database, NOTION_API, _headers
from publisher_telegram import _send_message
from publisher_notion import publish_to_notion
from llm_client import generate_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

def fetch_content_blocks(page_id: str) -> str:
    """Fetch text from all paragraph/list blocks of a Notion page."""
    url = f"{NOTION_API}/blocks/{page_id}/children"
    import requests
    resp = requests.get(url, headers=_headers(), timeout=30)
    if not resp.ok:
        return ""
        
    text_content = ""
    for block in resp.json().get("results", []):
        block_type = block.get("type", "")
        if block_type in ["paragraph", "bulleted_list_item", "heading_2"]:
            rich_texts = block.get(block_type, {}).get("rich_text", [])
            for r in rich_texts:
                text_content += r.get("plain_text", "")
            text_content += "\n"
    return text_content

def main():
    logger.info("Starting Weekly Recap generation...")
    db_id = os.environ.get("NOTION_DB_INBOX")
    if not db_id:
        logger.error("NOTION_DB_INBOX missing.")
        return

    # Look back 5 days (Monday to Friday)
    lookback = (datetime.now(KST) - timedelta(days=5)).isoformat()
    filter_payload = {
        "property": "Created time",
        "created_time": {"on_or_after": lookback}
    }
    
    results = query_database(db_id, filter_payload=filter_payload)
    logger.info("Found %d entries in the last 5 days.", len(results))
    
    if not results:
        logger.warning("No articles found to recap.")
        return
        
    all_text = ""
    for page in results[:10]:  # Limit to 10 most recent to fit context window safely
        page_id = page["id"]
        all_text += f"---\n\n{fetch_content_blocks(page_id)}\n\n"
        
    if len(all_text) < 500:
        logger.warning("Not enough text extracted for recap.")
        return

    prompt = f"""
다음은 이번 주에 수집된 주요 뉴스 브리핑 텍스트 모음입니다:

{all_text[-8000:]}

위 내용을 종합적으로 분석하여, 다음 주를 대비하기 위한 매우 실용적인 '3가지 핵심 인사이트 및 행동 지침'을 작성해주세요. 
출력 형식은 마크다운이며 다음과 같이 작성해야 합니다. 추가적인 인사말은 제외하고 아래 포맷만 출력하세요.

## 📊 이번 주 시장 요약
(전반적인 글로벌/반도체 시장 흐름 1~2문단)

## 🎯 다음 주 핵심 실행안 3가지
1. **[키워드]** 핵심 내용
   - 시사점/대응 방안
2. **[키워드]** 핵심 내용
   - 시사점/대응 방안
3. **[키워드]** 핵심 내용
   - 시사점/대응 방안
"""

    logger.info("Generating recap via Gemini...")
    recap_markdown = generate_text(prompt, max_tokens=1500)
    
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    title = f"💡 [주간 리캡] {today_str} 다음 주 인사이트 & 실행안"
    
    logger.info("Generated recap. Publishing...")
    notion_url = publish_to_notion(title, recap_markdown)
    
    # Notify telegram
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"📊 *주간 인사이트 리캡 발행 완료*\n\n다음 주를 위한 3가지 동작 플랜이 요약되었습니다.\nNotion에서 확인하세요:\n{notion_url}"
        _send_message(token, chat_id, msg)

if __name__ == "__main__":
    main()
