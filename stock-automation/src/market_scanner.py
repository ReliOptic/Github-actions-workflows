import os
import sys

def main():
    print("📈 [stock-automation] market_scanner.py is running!")
    print("이곳에 yfinance 또는 증권사 API 연동 로직이 들어갈 예정입니다.")
    print("현재는 골격(Skeleton)만 잡혀 있는 상태입니다.")
    
    dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'
    if dry_run:
        print("모드: Dry Run (실제 매매/알림 생략)")
    else:
        print("모드: 실전 배포 (매매 시그널 전송)")

if __name__ == "__main__":
    main()
