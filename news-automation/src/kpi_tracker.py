"""
kpi_tracker.py — Scrapes market KPIs (e.g. Semiconductor indicators) via standard APIs (Feature D)
Requires no LLM. Simple web requests to free finance endpoints.
"""
import logging
import os
import requests
from datetime import datetime, timedelta, timezone

from publisher_notion import publish_to_notion
from publisher_telegram import _send_message

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

def fetch_yahoo_quote(ticker: str) -> dict:
    """Fetch current price and change from Yahoo Finance public (undocumented) chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return {"price": "N/A", "change_pct": "N/A"}
            
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice", 0.0)
        prev_close = meta.get("chartPreviousClose", 0.0)
        
        # Calculate percentage change
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        return {
            "price": round(price, 2),
            "change_pct": round(change_pct, 2)
        }
    except Exception as e:
        logger.error("Failed fetching ticker %s: %s", ticker, e)
        return {"price": "ERROR", "change_pct": 0.0}

def format_ticker(label: str, data: dict) -> str:
    price = data["price"]
    change = data["change_pct"]
    
    if isinstance(change, (int, float)):
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        change_str = f"{change:+.2f}%"
    else:
        emoji = "❓"
        change_str = str(change)
        
    return f"• **{label}**: ${price} ({emoji} {change_str})"

def main():
    logger.info("Starting KPI Tracker...")
    
    # Selected semiconductor / macro KPIs
    tickers = {
        "SOXX (Semiconductor ETF)": "SOXX",
        "TSMC (Foundry)": "TSM",
        "NVIDIA (AI/Compute)": "NVDA",
        "ASML (EUV)": "ASML",
        "Micron (Memory/HBM proxy)": "MU",
        "US 10Y Treasury": "^TNX", # Macro
        "USD/KRW": "KRW=X" # FX
    }
    
    lines = ["## 📈 반도체 및 매크로 KPI 데일리 스코어카드\n\n최근 장 마감 기준 주요 지표 변화량입니다.\n"]
    
    for label, ticker in tickers.items():
        data = fetch_yahoo_quote(ticker)
        line = format_ticker(label, data)
        lines.append(line)
        logger.info("Fetched: %s", line)
        
    lines.append("\n---")
    
    content = "\n".join(lines)
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    title = f"📈 [KPI 트래커] {today_str} 반도체 주요 지표"
    
    url = publish_to_notion(title, content)
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        _send_message(token, chat_id, f"📈 *종가 기준 KPI 스코어카드 발행*\n\n반도체 및 매크로 수치가 업데이트 되었습니다.\n{url}")

if __name__ == "__main__":
    main()
