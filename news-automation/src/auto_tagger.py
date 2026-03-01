"""
auto_tagger.py — Automatically categorizes and tags untagged Notion DB entries. (Feature E)
"""
import logging
import os
import json
from datetime import datetime, timedelta, timezone

from notion_client import query_database, update_page_properties
from weekly_recap import fetch_content_blocks
from llm_client import generate_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

def extract_tags_via_llm(title: str, content: str) -> list[str]:
    prompt = f"""
다음은 테크/금융 섹터의 자동화된 뉴스레터/브리프입니다.
제목과 본문 요약을 읽고 이 글에 가장 잘 어울리는 태그를 최대 3개까지 선택해서 배열 형태로만 출력하세요. 
태그는 반드시 아래 [허용된 태그 목록] 안에서만 골라야 합니다.
JSON 배열 형식 외의 어떤 텍스트도 출력하지 마세요 (마크다운 백틱 금지).

[허용된 태그 목록]
Macro, Semiconductor, AI, Regulation, Corporate, Market, KPI, Brief, Startup, Crypto

[분석할 텍스트]
제목: {title}
본문: {content[:1500]}

출력 예시:
["Macro", "AI"]
"""
    result_text = generate_text(prompt, max_tokens=100)
    
    # Clean up markdown if Gemini adds it
    result_text = result_text.replace("```json", "").replace("```", "").strip()
    
    try:
        tags = json.loads(result_text)
        if isinstance(tags, list):
            return tags
    except Exception as e:
        logger.error("Failed to parse tags from LLM output: %s. Output: %s", e, result_text)
        
    return ["Market"] # Fallback

def main():
    logger.info("Starting Auto Tagger...")
    db_id = os.environ.get("NOTION_DB_INBOX")
    if not db_id:
        logger.error("Missing NOTION_DB_INBOX")
        return
        
    lookback = (datetime.now(KST) - timedelta(days=2)).isoformat()
    filter_payload = {
        "and": [
            {
                "property": "Created time",
                "created_time": {"on_or_after": lookback.split('.')[0] + 'z' if '+' not in lookback else lookback}
            },
            {
                "property": "태그",
                "multi_select": {"is_empty": True}
            }
        ]
    }
    
    try:
        results = query_database(db_id, filter_payload=filter_payload)
    except Exception as e:
        logger.warning("Query specifically for '태그' failed, trying fallback to 'Tags': %s", e)
        # Fallback to 'Tags' if '태그' doesn't exist
        filter_payload["and"][1]["property"] = "Tags"
        results = query_database(db_id, filter_payload=filter_payload)
        
    logger.info("Found %d untagged items from the last 48 hours.", len(results))
    
    tagged_count = 0
    for page in results:
        page_id = page["id"]
        props = page.get("properties", {})
        
        tag_prop_name = "태그" if "태그" in props else "Tags"
        
        # Extract title
        title_prop = props.get("Name", {}).get("title", [])
        title = title_prop[0].get("plain_text", "Untitled") if title_prop else "Untitled"
        
        logger.info("Processing: %s", title)
        
        # Read content
        content = fetch_content_blocks(page_id)
        if len(content) < 50:
            logger.warning("Content too short, skipping.")
            continue
            
        # Get tags
        predicted_tags = extract_tags_via_llm(title, content)
        logger.info("Suggested tags: %s", predicted_tags)
        
        # Update Notion
        # Notion requires a list of dicts: [{"name": "Macro"}]
        new_tags_payload = [{"name": t} for t in predicted_tags]
        
        update_payload = {
            tag_prop_name: {
                "multi_select": new_tags_payload
            }
        }
        
        try:
            update_page_properties(page_id, update_payload)
            tagged_count += 1
            logger.info("Successfully tagged %s", title)
        except Exception as e:
            logger.error("Failed to update tags for %s: %s", title, e)
            
    logger.info("Auto Tagger completed. Tagged %d items.", tagged_count)

if __name__ == "__main__":
    main()
