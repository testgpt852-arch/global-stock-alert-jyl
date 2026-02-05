import asyncio
import os
import logging

# 1. 봇 안심시키기 (가짜 키)
os.environ["TELEGRAM_TOKEN"] = "dummy"
os.environ["TELEGRAM_CHAT_ID"] = "123456"
os.environ["GEMINI_API_KEY"] = "dummy"
os.environ["FINNHUB_API_KEY"] = "dummy"
os.environ["ALPHA_VANTAGE_KEY"] = "dummy"

logging.basicConfig(level=logging.CRITICAL)

from news_scanner import NewsScanner
from kr_stock_scanner import KRStockScanner
from config import Config

# ==========================================
# 🛠️ 필터링 해제 마법 (Monkey Patching)
# 기존 파일 수정 없이, 메모리 상에서만 기능을 바꿔치기합니다.
# ==========================================

# 1. 미국 뉴스 필터 해제 함수
def permissive_add(self, news_list, title, url, symbol, source_name):
    # 키워드 검사 없이 무조건 추가!
    news_list.append({
        'symbol': symbol,
        'title': title,
        'url': url,
        'source': source_name
    })

# 2. 한국 뉴스 필터 해제 함수
def permissive_kr_check(self, title):
    # 무조건 통과!
    return True

# 3. 기능 덮어쓰기 (이 스크립트 실행 중에만 적용됨)
NewsScanner._add_if_valid = permissive_add
KRStockScanner.is_important_kr_news = permissive_kr_check
# ==========================================


async def test_raw_news():
    print("\n🕵️‍♂️ [무삭제 모드] 필터를 끄고 모든 뉴스를 긁어옵니다...\n")

    # --- 1. 미국 뉴스 (Raw) ---
    print(f"🇺🇸 [미국] 3대 뉴스 사이트 원본 데이터 수집 중...")
    try:
        us_scanner = NewsScanner()
        us_news_list = await us_scanner.scan()
        
        if us_news_list:
            print(f"🔥 총 {len(us_news_list)}개의 뉴스를 가져왔습니다. (최신 10개만 출력)")
            for i, news in enumerate(us_news_list[:10]):
                print(f"  {i+1}. [{news['source']}] {news['title'][:80]}...") 
                # 너무 길어서 제목 80자에서 자름
        else:
            print("❌ 미국: 뉴스를 하나도 못 가져왔습니다. (사이트 접속 차단 가능성)")
            
    except Exception as e:
        print(f"❌ 미국 스캔 에러: {e}")

    print("-" * 50)

    # --- 2. 한국 뉴스 (Raw) ---
    print(f"🇰🇷 [한국] 네이버 금융 실시간 속보 원본 데이터 수집 중...")
    try:
        kr_scanner = KRStockScanner(telegram_bot=None, ai_analyzer=None)
        kr_news_list = await kr_scanner.scan_naver_news()
        
        if kr_news_list:
             print(f"🔥 총 {len(kr_news_list)}개의 뉴스를 가져왔습니다. (최신 10개만 출력)")
             for i, news in enumerate(kr_news_list[:10]):
                 title = news.get('title', str(news))
                 print(f"  {i+1}. {title}")
        else:
            print("❌ 한국: 뉴스를 하나도 못 가져왔습니다. (네이버 HTML 구조 변경 의심)")

    except Exception as e:
        print(f"❌ 한국 스캔 에러: {e}")

    print("\n✅ 확인 종료")

if __name__ == "__main__":
    try:
        asyncio.run(test_raw_news())
    except KeyboardInterrupt:
        pass