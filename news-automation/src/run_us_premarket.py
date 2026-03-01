"""
run_us_premarket.py — Entry point for the US pre-market brief (KST 22:30 / UTC 13:30).

Pipeline:
  1. Collect articles from RSS feeds
  2. Deduplicate
  3. Filter & score
  4. Format pre-market brief
  5. Publish to Notion
  6. Send to Telegram (with Notion link)
  7. Log summary to GitHub Actions step summary
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from collector import collect_articles
from dedup import deduplicate
from scorer import filter_and_score
from formatter import format_us_premarket_brief
from publisher_notion import publish_to_notion
from publisher_telegram import publish_to_telegram, send_fallback_alert
from quality_gate import apply_quality_gate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
CONFIG_PATH = str(Path(__file__).parent.parent / "config" / "news_feeds.yaml")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def write_github_summary(text: str) -> None:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main() -> int:
    now_kst = datetime.now(KST)
    title = f"미국장 브리프 {now_kst.strftime('%Y-%m-%d')} (KST 22:30)"

    logger.info("=== US Pre-Market Brief Pipeline START ===")
    logger.info("DRY_RUN=%s", DRY_RUN)

    try:
        # 1. Collect
        logger.info("Step 1: Collecting articles...")
        all_articles = collect_articles(CONFIG_PATH)
        global_articles = all_articles.get("global_economy", [])
        semi_articles = all_articles.get("semiconductor", [])
        logger.info(
            "Collected: global=%d, semiconductor=%d",
            len(global_articles), len(semi_articles)
        )

        # 2. Deduplicate
        logger.info("Step 2: Deduplicating...")
        global_articles = deduplicate(global_articles, CONFIG_PATH)
        semi_articles = deduplicate(semi_articles, CONFIG_PATH)

        # 3. Filter & score
        logger.info("Step 3: Filtering and scoring...")
        global_articles = filter_and_score(global_articles, CONFIG_PATH)
        semi_articles = filter_and_score(semi_articles, CONFIG_PATH)

        logger.info(
            "Final: global=%d, semiconductor=%d",
            len(global_articles), len(semi_articles)
        )

        # Graceful fallback if articles are thin
        if len(global_articles) + len(semi_articles) < 2:
            logger.warning("Very few articles collected. Using fallback brief.")
            content = (
                f"🌙 *미국장 대기 브리프* | {now_kst.strftime('%Y-%m-%d %H:%M KST')}\n\n"
                "⚠️ 오늘은 충분한 뉴스를 수집하지 못했습니다.\n"
                "주요 지수 및 매크로 일정을 직접 확인하세요:\n"
                "• https://finance.yahoo.com\n"
                "• https://www.investing.com/economic-calendar/"
            )
        else:
            # 4. Format
            logger.info("Step 4: Formatting pre-market brief...")
            content = format_us_premarket_brief(
                global_articles=global_articles,
                semi_articles=semi_articles,
            )

        logger.info("Applying Quality Gate...")
        content = apply_quality_gate(content, is_newsletter=False)

        logger.info("Formatted content preview:\n%s", content[:500])

        notion_url: str | None = None

        if DRY_RUN:
            logger.info("=== DRY RUN MODE — skipping Notion/Telegram ===")
            print("\n" + "=" * 60)
            print("DRY RUN OUTPUT:")
            print("=" * 60)
            print(content)
            return 0

        # 5. Publish to Notion
        logger.info("Step 5: Publishing to Notion...")
        notion_url = publish_to_notion(title=title, content=content)
        logger.info("Notion URL: %s", notion_url)

        # 6. Send to Telegram
        logger.info("Step 6: Sending to Telegram...")
        publish_to_telegram(content=content, notion_url=notion_url)

        # 7. GitHub Actions summary
        summary_lines = [
            "## ✅ US Pre-Market Brief — 완료",
            f"- 발행 시각: {now_kst.strftime('%Y-%m-%d %H:%M KST')}",
            f"- 국제/경제 기사: {len(global_articles[:3])}건",
            f"- 반도체 기사: {len(semi_articles[:3])}건",
            f"- Notion 페이지: {notion_url}",
        ]
        write_github_summary("\n".join(summary_lines))
        logger.info("=== US Pre-Market Brief Pipeline COMPLETE ===")
        return 0

    except Exception:
        error_msg = traceback.format_exc()
        logger.error("Pipeline failed:\n%s", error_msg)
        send_fallback_alert(error_msg)
        write_github_summary(
            "## ❌ US Pre-Market Brief — 실패\n"
            f"```\n{error_msg[:1000]}\n```"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
