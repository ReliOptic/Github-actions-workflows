"""
db_healthcheck.py — Scans Notion DB for empty/broken fields. (Feature A)
Sends a cleanup report via Telegram.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from notion_client import query_database
from publisher_telegram import _send_message

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

def main():
    logger.info("Starting Notion DB Healthcheck...")
    
    db_id = os.environ.get("NOTION_DB_INBOX")
    if not db_id:
        logger.error("NOTION_DB_INBOX missing.")
        return
        
    # Check items created in the last 7 days
    past_week = (datetime.now(KST) - timedelta(days=7)).isoformat()
    
    filter_payload = {
        "property": "Created time",
        "created_time": {
            "on_or_after": past_week.split('.')[0] + "z" if "+" not in past_week else past_week 
        }
    }
    
    try:
        results = query_database(db_id, filter_payload=filter_payload)
    except Exception as e:
        logger.error("Failed to query DB: %s", e)
        return
        
    logger.info("Found %d items created in the last 7 days.", len(results))
    
    warnings = []
    
    for page in results:
        props = page.get("properties", {})
        
        # Extract title
        title_prop = props.get("Name", {}).get("title", [])
        title = title_prop[0].get("plain_text", "Untitled") if title_prop else "Untitled"
        
        url = page.get("url", "No URL")
        
        issues = []
        
        # Check title
        if title == "Untitled" or not title.strip():
            issues.append("제목 없음(Untitled)")
            
        # Check Tags (Assuming property is named '태그' or 'Tags' based on user confirmation)
        tag_prop = props.get("태그", props.get("Tags"))
        if tag_prop:
            if tag_prop.get("type") == "multi_select" and not tag_prop.get("multi_select"):
                issues.append("태그 속성 비어있음")
        
        if issues:
            warnings.append(f"• [{title}]({url}): {', '.join(issues)}")
            
    if warnings:
        logger.warning("Found %d pages with issues.", len(warnings))
        msg = "🧹 *주간 Notion DB 휴지통 점검 리포트*\n\n"
        msg += "다음 페이지들에 빈 속성이나 문제가 있습니다. 정리가 필요합니다:\n"
        msg += "\n".join(warnings)
    else:
        logger.info("No issues found in the database. All clean!")
        msg = "✨ *주간 Notion DB 점검 완료*\n\n최근 7일간 저장된 모든 데이터가 깨끗하게 관리되고 있습니다!"
        
    # Send report via Telegram
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        _send_message(token, chat_id, msg)
        logger.info("Telegram report sent.")
    else:
        logger.warning("Missing Telegram credentials to send report:\n%s", msg)

if __name__ == "__main__":
    main()
