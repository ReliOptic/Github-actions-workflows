"""
healthcheck_feeds.py — Daily check of RSS/API feed URLs.
Proposes fallback sources for broken links.
"""
import logging
import os
import sys
from pathlib import Path

import requests
import yaml
from publisher_telegram import _send_message

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = str(Path(__file__).parent.parent / "config" / "news_feeds.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_url(url: str, timeout: int = 15) -> tuple[bool, str]:
    """Return (is_ok, status_message) for a given URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; HealthcheckBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return True, "OK"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as exc:
        return False, str(exc)[:50]


def recommend_fallback(category: str, config: dict) -> str:
    """Recommend up to 2 fallback sources for a category."""
    fallbacks = config.get("fallback_database", {}).get(category, [])
    if not fallbacks:
        return "추천 가능 대체 소스 없음."
    
    recs = []
    for f in fallbacks[:2]:
        recs.append(f"• {f['name']}: {f['url']}")
    return "\n".join(recs)


def main():
    logger.info("Starting Feed Healthcheck...")
    config = load_config()
    categories = config.get("categories", {})
    
    failed_feeds = []
    total_checked = 0

    for cat_key, cat_data in categories.items():
        feeds = cat_data.get("feeds", {})
        for tier in ["tier1", "tier2"]:
            for feed in feeds.get(tier, []):
                total_checked += 1
                name = feed.get("name", "Unknown")
                url = feed.get("url", "")
                
                is_ok, msg = check_url(url)
                if is_ok:
                    logger.info("✅ [%s] %s: OK", tier, name)
                else:
                    logger.warning("❌ [%s] %s: %s", tier, name, msg)
                    failed_feeds.append({
                        "category": cat_key,
                        "tier": tier,
                        "name": name,
                        "url": url,
                        "error": msg
                    })

    # Report results
    if failed_feeds:
        logger.error("Healthcheck found %d broken feeds out of %d.", len(failed_feeds), total_checked)
        
        # Build alert message
        alert_lines = [
            "⚠️ *뉴스 소스 헬스체크 경고*",
            f"총 {total_checked}개 중 *{len(failed_feeds)}개* 피드 응답 오류 발생.\n"
        ]
        
        for fail in failed_feeds:
            alert_lines.append(f"▪️ *{fail['name']}* ({fail['tier']})")
            alert_lines.append(f"  URL: `{fail['url']}`")
            alert_lines.append(f"  오류: {fail['error']}")
            
            fallback = recommend_fallback(fail["category"], config)
            if fallback:
                alert_lines.append("  💡 추천 대체 소스:")
                alert_lines.append(f"  {fallback}")
            alert_lines.append("")
            
        alert_text = "\n".join(alert_lines)
        
        # Send via Telegram if configured
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if token and chat_id:
            try:
                _send_message(token, chat_id, alert_text)
                logger.info("Healthcheck alert sent to Telegram.")
            except Exception as e:
                logger.error("Failed to send Telegram alert: %s", e)
        else:
            logger.warning("Telegram credentials missing. Alert skipped.")
            
        sys.exit(1)  # Fail step so it shows in GitHub Actions
        
    else:
        logger.info("All %d feeds are perfectly healthy!", total_checked)
        
        # Write success to summary
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write(f"## 🟢 RSS Feed Healthcheck: 정상\n- 총 {total_checked}개 소스 모두 접근 가능.\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
