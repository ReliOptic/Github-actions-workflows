# ✅ GitHub Actions 뉴스 자동화 — 배포 전 점검 체크리스트

아래 10개 항목을 모두 완료한 후 배포하세요.

---

## 필수 점검 항목

### 1. Secrets 등록 완료
- [ ] `NOTION_TOKEN` 설정됨
- [ ] `NOTION_DB_INBOX` 설정됨 (올바른 데이터베이스 ID)
- [ ] `TELEGRAM_BOT_TOKEN` 설정됨
- [ ] `TELEGRAM_CHAT_ID` 설정됨

### 2. Notion 데이터베이스 구조 확인
- [ ] `Name` 프로퍼티 존재 (title 타입)
- [ ] `Status` 프로퍼티 존재 (select 타입, **"완료"** 옵션 포함)
- [ ] Integration이 해당 데이터베이스에 연결(Share → Invite)됨

### 3. Telegram 봇 연결 확인
- [ ] 봇이 대상 채널/그룹에 **관리자**로 추가됨
- [ ] `TELEGRAM_CHAT_ID`가 채널인 경우 `-100` 접두사 포함 확인

### 4. 로컬 Dry-Run 통과
- [ ] `DRY_RUN=true python src/run_daily_newsletter.py` 오류 없이 출력됨
- [ ] `DRY_RUN=true python src/run_us_premarket.py` 오류 없이 출력됨

### 5. RSS 피드 접근성 확인
- [ ] `config/news_feeds.yaml`의 Tier 1 피드 중 1개 이상 정상 응답 확인
  ```bash
  python -c "import requests; r=requests.get('https://feeds.reuters.com/reuters/businessNews', timeout=10); print(r.status_code)"
  ```

### 6. GitHub Actions 권한 확인
- [ ] 리포지토리가 Public이거나 GitHub Actions quota가 충분함
- [ ] `.github/workflows/` 파일이 기본 브랜치(main/master)에 푸시됨

### 7. 스케줄 시간 확인
- [ ] `daily_newsletter.yml` cron이 `0 3 * * *` (UTC 03:00 = KST 12:00)
- [ ] `us_premarket.yml` cron이 `30 13 * * 1-5` (UTC 13:30 = KST 22:30, 평일)

### 8. VM 기존 작업 비활성화
- [ ] VM crontab에서 기존 뉴스레터 작업 주석 처리됨 (삭제 말고 보존)
- [ ] 중복 실행 없음 확인 (VM + GitHub Actions 동시 실행 방지)

### 9. GitHub Actions 수동 실행 테스트
- [ ] `Daily Newsletter` 워크플로우를 `dry_run: true`로 수동 실행 → 성공 확인
- [ ] `US Pre-Market Brief` 워크플로우를 `dry_run: true`로 수동 실행 → 성공 확인

### 10. 실전 실행 1회 확인
- [ ] `dry_run: false`로 1회 수동 실행
- [ ] Notion 페이지 생성 및 내용 확인
- [ ] Telegram 메시지 수신 확인
- [ ] GitHub Actions Step Summary에 요약 정보 표시 확인

---

## 빠른 검증 명령

```bash
# 전체 의존성 설치 확인
pip install -r news-automation/requirements.txt && echo "OK"

# 피드 수집 단독 테스트
python -c "
import sys; sys.path.insert(0,'news-automation/src')
from collector import collect_articles
r = collect_articles('news-automation/config/news_feeds.yaml')
for k,v in r.items(): print(f'{k}: {len(v)}건')
"

# 포맷 출력 확인 (dry-run)
DRY_RUN=true python news-automation/src/run_daily_newsletter.py
```

---

> 모든 항목 ✅ 후 GitHub Actions 스케줄 자동 실행을 신뢰할 수 있습니다.
