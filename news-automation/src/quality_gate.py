"""
quality_gate.py — Checks formatted newsletter/brief drafts before publishing.
Implements Soft Warning logic.
"""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
CONFIG_PATH = str(Path(__file__).parent.parent / "config" / "news_feeds.yaml")


def check_content_quality(content: str, is_newsletter: bool = True) -> tuple[bool, list[str]]:
    """
    Check the quality of the generated text.
    Returns (passed, list_of_warnings).
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    qg = config.get("quality_gate", {})
    clickbait_patterns = config.get("clickbait_patterns", [])
    
    warnings = []
    
    # 1. URL Presence Check
    # Ensure there are enough '🔗' links in the output to match minimums.
    link_count = content.count("🔗 http")
    if is_newsletter and link_count < 2:
        warnings.append(f"본문 내 링크 수가 너무 적습니다 (현재: {link_count}개). 파싱 오류 의심.")
    elif not is_newsletter and link_count < 3:
        warnings.append(f"브리프 내 주요 뉴스 링크가 부족합니다 (현재: {link_count}개).")
        
    # 2. Required Headers Check (Newsletter only)
    if is_newsletter:
        req_headers = qg.get("required_headers", {})
        if req_headers.get("global") and req_headers["global"] not in content:
            warnings.append(f"필수 헤더 누락: '{req_headers['global']}'")
        if req_headers.get("semi") and req_headers["semi"] not in content:
            warnings.append(f"필수 헤더 누락: '{req_headers['semi']}'")
            
    # 3. Overall Length Check
    # A standard brief should be at least a few hundred characters
    if len(content) < 300:
        warnings.append(f"출력물 길이가 비정상적으로 짧습니다 ({len(content)}자). 데이터 누락 의심.")
        
    # 4. Final Clickbait/Noise Check (Safety net)
    # Check if a heavily hyper-sensationalized phrase slipped through
    import re
    for pattern in clickbait_patterns:
        if re.search(pattern, content):
            warnings.append(f"본문에 과장 표현(클릭베이트) 필터 매칭 의심 내용 포함 (패턴: {pattern}).")
            break
            
    # Evaluate
    passed = len(warnings) == 0
    return passed, warnings


def apply_quality_gate(content: str, is_newsletter: bool = True) -> str:
    """
    Apply quality gate. If warnings exist, prepend a Soft Warning tag
    and list the warnings at the top of the content.
    """
    passed, warnings = check_content_quality(content, is_newsletter)
    
    if passed:
        return content
        
    # Soft warning mode
    logger.warning("Quality Gate warnings found: %s", warnings)
    
    warning_block = (
        "⚠️ **[시스템 품질 경고: 본문 포맷/데이터 이상 의심]**\n"
    )
    for i, w in enumerate(warnings, 1):
        warning_block += f"  - 경고 {i}: {w}\n"
    warning_block += "─" * 40 + "\n\n"
    
    return warning_block + content
