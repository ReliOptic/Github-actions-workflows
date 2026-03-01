# 📰 News Automation — GitHub Actions 뉴스 자동화

VM(OpenClaw)에서 실행되던 뉴스 자동화 파이프라인을 **GitHub Actions**로 이전한 프로젝트입니다.

---

## 📁 프로젝트 구조

```
news-automation/
├── .github/workflows/
│   ├── daily_newsletter.yml     # 일일 뉴스레터 (KST 12:00)
│   └── us_premarket.yml         # 미국장 브리프 (KST 22:30)
├── config/
│   └── news_feeds.yaml          # RSS 피드 소스 & 노이즈 필터 설정
├── src/
│   ├── collector.py             # RSS 피드 수집 (Tier 1/2 fallback)
│   ├── dedup.py                 # 중복 제거 (URL 정규화 + 제목 유사도)
│   ├── scorer.py                # 기사 품질 점수 & 노이즈 필터
│   ├── formatter.py             # 뉴스레터/브리프 텍스트 포맷
│   ├── publisher_notion.py      # Notion DB 저장
│   ├── publisher_telegram.py    # Telegram 전송
│   ├── run_daily_newsletter.py  # 엔트리포인트: 일일 뉴스레터
│   └── run_us_premarket.py      # 엔트리포인트: 미국장 브리프
├── requirements.txt
└── README.md
```

---

## ⏰ 스케줄 기준 (KST ↔ UTC)

| 워크플로우 | KST | UTC (cron) | 실행 조건 |
|-----------|-----|-----------|---------|
| 일일 뉴스레터 | 12:00 | 03:00 | 매일 (주 7일) |
| 미국장 브리프 | 22:30 | 13:30 | 평일만 (월~금) |

> KST = UTC + 9시간. GitHub Actions cron은 항상 UTC 기준입니다.

---

## 🔐 Secrets 설정 방법

GitHub 리포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 설명 | 예시 |
|------------|------|------|
| `NOTION_TOKEN` | Notion Integration 토큰 | `secret_xxxx...` |
| `NOTION_DB_INBOX` | Notion 대상 데이터베이스 ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `TELEGRAM_BOT_TOKEN` | @BotFather에서 발급한 봇 토큰 | `1234567890:AAH...` |
| `TELEGRAM_CHAT_ID` | 대상 채널 또는 채팅방 ID | `-100123456789` |

### Notion 설정 상세

1. [Notion Developers](https://www.notion.so/my-integrations)에서 Integration 생성
2. 대상 데이터베이스 페이지에서 Integration 연결 (Share → Invite)
3. 데이터베이스 URL에서 ID 추출: `https://notion.so/workspace/[DATABASE_ID]?...`
4. 데이터베이스에 다음 프로퍼티 필요:
   - `Name` (title 타입)
   - `Status` (select 타입, "완료" 옵션 포함)

---

## 🚀 로컬 설치 및 실행

### 1. 의존성 설치

```bash
cd news-automation
pip install -r requirements.txt
```

### 2. 환경변수 설정 (로컬 테스트 시)

```bash
# Windows PowerShell
$env:NOTION_TOKEN = "secret_..."
$env:NOTION_DB_INBOX = "your-db-id"
$env:TELEGRAM_BOT_TOKEN = "your-bot-token"
$env:TELEGRAM_CHAT_ID = "-100..."
```

```bash
# macOS/Linux
export NOTION_TOKEN="secret_..."
export NOTION_DB_INBOX="your-db-id"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="-100..."
```

---

## 🧪 테스트 방법

### 로컬 Dry-Run (Notion/Telegram 전송 없이 출력만 확인)

```bash
# 일일 뉴스레터 dry-run
DRY_RUN=true python news-automation/src/run_daily_newsletter.py

# 미국장 브리프 dry-run
DRY_RUN=true python news-automation/src/run_us_premarket.py
```

> Windows PowerShell의 경우:
> ```powershell
> $env:DRY_RUN="true"; python news-automation/src/run_daily_newsletter.py
> $env:DRY_RUN="true"; python news-automation/src/run_us_premarket.py
> ```

### GitHub Actions 수동 실행

1. GitHub 리포지토리 → **Actions** 탭
2. 좌측에서 워크플로우 선택 (`Daily Newsletter` 또는 `US Pre-Market Brief`)
3. **Run workflow** 버튼 클릭
4. `dry_run` 옵션 선택 후 **Run workflow** 확인

---

## 🛡️ 장애 복구 방법

### 피드 실패 시

- `config/news_feeds.yaml`의 `tier1` 피드 실패 → 자동으로 `tier2` 피드 시도
- 최소 기사 수 이하이면 간소 브리프(fallback brief) 생성 후 전송

### 워크플로우 실패 시

1. GitHub **Actions** 탭에서 실패한 워크플로우 로그 확인
2. **Step Summary** 탭에서 요약 오류 내용 확인
3. Telegram에 자동 실패 알림 발송됨
4. `Run workflow`로 수동 재실행 가능

### VM 기존 작업 비활성화

VM의 crontab 항목을 삭제하지 말고 주석 처리로 보존:

```bash
# crontab -e 에서 아래처럼 주석 처리
# 0 12 * * * /path/to/run_newsletter.sh   # DISABLED: moved to GitHub Actions
# 30 22 * * 1-5 /path/to/run_premarket.sh  # DISABLED: moved to GitHub Actions
```

---

## 📦 의존성

| 라이브러리 | 버전 | 용도 |
|----------|------|------|
| `feedparser` | 6.0.11 | RSS/Atom 피드 파싱 |
| `requests` | 2.31.0 | HTTP 요청 (피드 fetch, Notion API, Telegram API) |
| `PyYAML` | 6.0.1 | 설정 파일 파싱 |

> 유료 API 미사용. 모든 처리는 오픈 RSS 피드와 공식 Notion/Telegram Bot API(무료)를 활용합니다.
