"""
notion_client.py — Shared API client for querying and updating Notion data.
(publisher_notion.py is kept for its specific layout generation logic).
"""
import logging
import os
import requests
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def _headers():
    return {
        "Authorization": f"Bearer {os.environ.get('NOTION_TOKEN')}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

def query_database(db_id: str, filter_payload: dict = None, sorts: list = None) -> list[dict]:
    """Query a Notion database and return the list of page results."""
    url = f"{NOTION_API}/databases/{db_id}/query"
    payload = {}
    if filter_payload:
        payload["filter"] = filter_payload
    if sorts:
        payload["sorts"] = sorts
        
    results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
        
    return results

def update_page_properties(page_id: str, properties: dict):
    """Update properties of an existing Notion page."""
    url = f"{NOTION_API}/pages/{page_id}"
    payload = {"properties": properties}
    resp = requests.patch(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
