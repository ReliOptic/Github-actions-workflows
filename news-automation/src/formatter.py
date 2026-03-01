"""
formatter.py — Format articles into daily newsletter and US pre-market brief.

Uses simple heuristics to split summary into two key points and one implication.
No paid LLM API is required — summaries are extracted from feed content.
"""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collector import Article

KST = timezone(timedelta(hours=9))


def _now_kst() -> str:
    return datetime.now(KST).strftime("%Y년 %m월 %d일 %H:%M KST")


def _extract_key_points(summary: str) -> tuple[str, str, str]:
    """
    Split summary into two key points and one implication.
    Simple heuristic: split on sentence boundaries.
    """
    import re
    sentences = re.split(r"(?<=[.!?])\s+", summary.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    if len(sentences) >= 3:
        point1 = sentences[0]
        point2 = sentences[1]
        implication = sentences[2]
    elif len(sentences) == 2:
        point1 = sentences[0]
        point2 = sentences[1]
        implication = "시장 영향 지속 가능성 주목."
    elif len(sentences) == 1:
        point1 = sentences[0]
        point2 = "추가 세부 정보는 원문 참고."
        implication = "관련 동향 모니터링 필요."
    else:
        point1 = summary[:120] if summary else "요약 없음."
        point2 = "추가 세부 정보는 원문 참고."
        implication = "관련 동향 모니터링 필요."

    # Truncate long sentences
    point1 = textwrap.shorten(point1, width=200, placeholder="…")
    point2 = textwrap.shorten(point2, width=200, placeholder="…")
    implication = textwrap.shorten(implication, width=200, placeholder="…")

    return point1, point2, implication


def _format_article_block(article: "Article", index: int) -> str:
    """Format a single article into the newsletter block format."""
    point1, point2, implication = _extract_key_points(article.summary)
    lines = [
        f"{index}. **{article.title}**",
        f"   • {point1}",
        f"   • {point2}",
        f"   💡 시사점: {implication}",
        f"   🔗 {article.url}",
    ]
    return "\n".join(lines)


def format_daily_newsletter(
    global_articles: list["Article"],
    semi_articles: list["Article"],
    select_global: int = 3,
    select_semi: int = 3,
) -> str:
    """
    일일 뉴스레터 (KST 12:00) 포맷 생성.

    1. 국제정세/경제시장: 선택 기사 블록
    2. 반도체: 선택 기사 블록
    3. 투자자 체크포인트 3개
    4. 리스크/기회 각 1줄
    """
    now = _now_kst()
    lines: list[str] = []

    lines.append(f"📰 **일일 뉴스 브리핑** | {now}")
    lines.append("=" * 50)
    lines.append("")

    # Section 1: 국제정세/경제시장
    lines.append("## 🌏 국제정세 / 경제시장")
    lines.append("")
    chosen_global = global_articles[:select_global]
    if chosen_global:
        for i, article in enumerate(chosen_global, 1):
            lines.append(_format_article_block(article, i))
            lines.append("")
    else:
        lines.append("⚠️ 오늘은 관련 기사를 수집하지 못했습니다.")
        lines.append("")

    lines.append("─" * 40)
    lines.append("")

    # Section 2: 반도체
    lines.append("## 💾 반도체")
    lines.append("")
    chosen_semi = semi_articles[:select_semi]
    if chosen_semi:
        for i, article in enumerate(chosen_semi, 1):
            lines.append(_format_article_block(article, i))
            lines.append("")
    else:
        lines.append("⚠️ 오늘은 반도체 관련 기사를 수집하지 못했습니다.")
        lines.append("")

    lines.append("─" * 40)
    lines.append("")

    # Section 3: 투자자 체크포인트
    lines.append("## ✅ 투자자 체크포인트")
    lines.append("")
    checkpoints = _generate_checkpoints(global_articles, semi_articles)
    for cp in checkpoints:
        lines.append(f"• {cp}")
    lines.append("")

    # Section 4: 리스크/기회
    lines.append("## ⚖️ 리스크 & 기회")
    risk, opportunity = _generate_risk_opportunity(global_articles, semi_articles)
    lines.append(f"🔴 **리스크**: {risk}")
    lines.append(f"🟢 **기회**: {opportunity}")
    lines.append("")

    return "\n".join(lines)


def format_us_premarket_brief(
    global_articles: list["Article"],
    semi_articles: list["Article"],
) -> str:
    """
    미국장 대기 브리프 (KST 22:30) 포맷 생성.

    1. 오늘 꼭 봐야 할 뉴스 5개
    2. 오늘 밤 매크로 일정
    3. 반도체 섹터 체크 3개
    4. 리스크 3개 + 대응 3개
    5. 한 줄 결론
    """
    now = _now_kst()
    lines: list[str] = []

    lines.append(f"🌙 **미국장 대기 브리프** | {now}")
    lines.append("=" * 50)
    lines.append("")

    # Section 1: 오늘 꼭 봐야 할 뉴스 5개
    lines.append("## 📌 오늘 꼭 봐야 할 뉴스 5선")
    lines.append("")
    all_articles = global_articles[:3] + semi_articles[:2]
    if not all_articles:
        # Fallback if no articles at all
        all_articles = global_articles[:5] or semi_articles[:5]
    for i, article in enumerate(all_articles[:5], 1):
        point1, _, _ = _extract_key_points(article.summary)
        lines.append(f"{i}. **{article.title}**")
        lines.append(f"   → {point1}")
        lines.append(f"   🔗 {article.url}")
        lines.append("")

    lines.append("─" * 40)
    lines.append("")

    # Section 2: 오늘 밤 매크로 일정
    lines.append("## 📅 오늘 밤 매크로 일정")
    lines.append("")
    macro_schedule = _generate_macro_schedule()
    for item in macro_schedule:
        lines.append(f"• {item}")
    lines.append("")

    lines.append("─" * 40)
    lines.append("")

    # Section 3: 반도체 섹터 체크 3개
    lines.append("## 💾 반도체 섹터 체크")
    lines.append("")
    chosen_semi = semi_articles[:3]
    if chosen_semi:
        for i, article in enumerate(chosen_semi, 1):
            point1, _, _ = _extract_key_points(article.summary)
            lines.append(f"{i}. {article.title}")
            lines.append(f"   → {point1}")
            lines.append(f"   🔗 {article.url}")
            lines.append("")
    else:
        lines.append("⚠️ 반도체 관련 기사 부족. 주요 지수 확인 권장.")
        lines.append("")

    lines.append("─" * 40)
    lines.append("")

    # Section 4: 리스크 3개 + 대응 3개
    lines.append("## ⚠️ 리스크 & 대응")
    lines.append("")
    risks_responses = _generate_risks_responses(global_articles, semi_articles)
    for i, (risk, response) in enumerate(risks_responses[:3], 1):
        lines.append(f"**리스크 {i}**: {risk}")
        lines.append(f"  → 대응: {response}")
        lines.append("")

    # Section 5: 한 줄 결론
    lines.append("─" * 40)
    lines.append("")
    risk_on_off = _determine_risk_signal(global_articles, semi_articles)
    lines.append(f"## 🎯 한 줄 결론")
    lines.append(f"**{risk_on_off}**")
    lines.append("")

    return "\n".join(lines)


def _generate_checkpoints(global_articles: list, semi_articles: list) -> list[str]:
    """Generate 3 investor checkpoint bullets from collected articles."""
    checkpoints = []
    headlines = [a.title for a in (global_articles + semi_articles)[:6]]

    if headlines:
        checkpoints.append(f"헤드라인 확인: {headlines[0][:60]}…" if len(headlines[0]) > 60 else f"헤드라인: {headlines[0]}")
    else:
        checkpoints.append("주요 지수(S&P500, NASDAQ, KOSPI) 전일 대비 방향 확인")

    checkpoints.append("미 연준 관련 발언/지표 발표 여부 확인")
    checkpoints.append("주요 반도체 종목(NVDA, TSMC, 삼성전자) 프리마켓 움직임 확인")

    return checkpoints[:3]


def _generate_risk_opportunity(global_articles: list, semi_articles: list) -> tuple[str, str]:
    """Generate one-liner risk and opportunity from article context."""
    risk = "글로벌 금리 불확실성 및 지정학적 리스크 지속"
    opportunity = "반도체 수요 회복 기대감 및 AI 인프라 투자 확대 모멘텀"

    # Customize based on available content
    if global_articles:
        first_title = global_articles[0].title[:80]
        risk = f"{first_title[:60]}… 관련 불확실성"
    if semi_articles:
        first_semi = semi_articles[0].title[:80]
        opportunity = f"{first_semi[:60]}… 관련 수혜 기대"

    return risk, opportunity


def _generate_macro_schedule() -> list[str]:
    """Return static macro schedule placeholders (no paid API needed)."""
    return [
        "미국 주요 경제 지표: investing.com 경제 캘린더 확인 권장",
        "연준 인사 발언 일정: Fed 공식 사이트 참고",
        "실적 발표: earnings.com 또는 seekingalpha 확인",
    ]


def _generate_risks_responses(global_articles: list, semi_articles: list) -> list[tuple[str, str]]:
    """Generate 3 risk/response pairs."""
    pairs = [
        ("미 연준 금리 정책 불확실성", "채권/달러 포지션 헤지 검토"),
        ("지정학적 리스크 (무역 갈등/분쟁)", "방어주 및 금(Gold) 비중 일부 확대"),
        ("반도체 공급망 리스크", "재고 지표 및 수주 데이터 모니터링"),
    ]
    # Customize first risk from article data if available
    if global_articles:
        pairs[0] = (
            f"{global_articles[0].title[:60]}… 변동성 리스크",
            "포지션 사이즈 축소 및 스탑로스 재설정",
        )
    return pairs


def _determine_risk_signal(global_articles: list, semi_articles: list) -> str:
    """
    Simple heuristic: determine risk-on/off based on keyword presence.
    """
    risk_off_keywords = ["crisis", "recession", "inflation", "war", "санкции", "tariff", "sanction", "default"]
    risk_on_keywords = ["rally", "surge", "growth", "record", "beat", "recovery", "expansion"]

    all_text = " ".join(
        (a.title + " " + a.summary).lower()
        for a in (global_articles + semi_articles)[:10]
    )

    risk_off_score = sum(1 for kw in risk_off_keywords if kw in all_text)
    risk_on_score = sum(1 for kw in risk_on_keywords if kw in all_text)

    if risk_off_score > risk_on_score:
        return "🔴 리스크오프 (Risk-Off) — 방어적 포지션 유지 권장"
    elif risk_on_score > risk_off_score:
        return "🟢 리스크온 (Risk-On) — 시장 모멘텀 활용 검토"
    else:
        return "🟡 중립 (Neutral) — 핵심 지표 발표 전까지 관망 권장"
