import os
import sys

def main():
    print("🚀 [youtube-automation] fetch_videos.py is running!")
    print("이곳에 YouTube API 또는 yt-dlp 텍스트 추출 로직이 들어갈 예정입니다.")
    print("현재는 골격(Skeleton)만 잡혀 있는 상태입니다.")
    
    dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'
    if dry_run:
        print("모드: Dry Run (실제 저장 및 API 전송 생략)")
    else:
        print("모드: 실전 배포 (API 실제 호출)")

if __name__ == "__main__":
    main()
