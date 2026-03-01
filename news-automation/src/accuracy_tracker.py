"""
accuracy_tracker.py — Compares yesterday's pre-market brief with today's daily newsletter. (Feature C)
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from notion_client import query_database
from weekly_recap import fetch_content_blocks
from llm_client import generate_text
from publisher_telegram import _send_message
from publisher_notion import publish_to_notion

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

def fetch_latest_by_keyword(db_id: str, keyword: str, days_back: int) -> dict | None:
    lookback = (datetime.now(KST) - timedelta(days=days_back)).isoformat()
    filter_payload = {
        "and": [
            {
                "property": "Created time",
                "created_time": {"on_or_after": lookback.split('.')[0] + 'z' if '+' not in lookback else lookback}
            },
            {
                "property": "Name",
                "title": {"contains": keyword}
            }
        ]
    }
    
    # Sort descending
    sorts = [{"property": "Created time", "direction": "descending"}]
    
    results = query_database(db_id, filter_payload=filter_payload, sorts=sorts)
    if results:
        return results[0]  # most recent match
    return None

def main():
    logger.info("Starting Accuracy Tracker...")
    db_id = os.environ.get("NOTION_DB_INBOX")
    if not db_id:
        logger.error("Missing NOTION_DB_INBOX")
        return
        
    # Get the latest US Pre-Market Brief (usually from yesterday night KST)
    yesterday_brief = fetch_latest_by_keyword(db_id, "🇺🇸", 2)
    # Get the latest Daily Newsletter (usually from today noon KST)
    today_newsletter = fetch_latest_by_keyword(db_id, "🗞️", 1)
    
    if not yesterday_brief or not today_newsletter:
        logger.warning(f"Could not find required files: USBrief={bool(yesterday_brief)}, Daily={bool(today_newsletter)}")
        return
        
    premarket_text = fetch_content_blocks(yesterday_brief["id"])
    daily_text = fetch_content_blocks(today_newsletter["id"])
    
    if len(premarket_text) < 100 or len(daily_text) < 100:
        logger.warning("Extracted text is too short for comparison.")
        return
        
    prompt = f"""
다음은 어제 밤에 예측/발행된 "미국장 프리마켓 브리프"의 내용입니다:
[어제 브리프]
{premarket_text[:3000]}

다음은 오늘 낮에 아침 장 마감 후 발행된 "일일 글로벌 뉴스레터"의 실제 흐름입니다:
[오늘 뉴스레터]
{daily_text[:4000]}

당신의 임무는 어제 우리가 가졌던 '프리마켓 프리뷰/예상'이 오늘 실제 결과(뉴스레터)와 얼마나 일치했는지 판별하는 것입니다.
다음 형식으로 출력해 주세요. 인사말 없이 바로 출력하세요.

## ⚖️ 미국장 브리프 정확도 리뷰
- **총평 요약**: (전체적으로 예상이 맞았는지, 아니면 예상치 못한 이슈가 있었는지 1~2문장)
- **적중한 포인트**: (예: 프리마켓에서 우려한 특정 종목 하락이 실제로 반영됨)
- **엇나간 포인트 (또는 새롭게 등장한 변수)**: (예상과 다르게 진행된 부분)
"""

    logger.info("Calling Gemini API for accuracy comparison...")
    verdict = generate_text(prompt, max_tokens=1000)
    
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    title = f"⚖️ [정확도 리포트] {today_str} 프리마켓 vs 실제 마감 비교"
    
    # publish to Notion
    url = publish_to_notion(title, verdict)
    
    # notify TG
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"⚖️ *일일 브리프 정확도 리포트 발행*\n\n전날 예상과 오늘 마감 결과 비교 분석이 완료되었습니다.\n{url}"
        _send_message(token, chat_id, msg)
        logger.info("Accuracy tracker finished.")

if __name__ == "__main__":
    main()
