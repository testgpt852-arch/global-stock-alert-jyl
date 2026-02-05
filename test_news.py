import asyncio
import os
import logging

# 1. 봇을 안심시키는 가짜 키 등록
os.environ["TELEGRAM_TOKEN"] = "dummy"
os.environ["TELEGRAM_CHAT_ID"] = "123456"
os.environ["GEMINI_API_KEY"] = "dummy"
os.environ["FINNHUB_API_KEY"] = "dummy"
os.environ["ALPHA_VANTAGE_KEY"] = "dummy"

logging.basicConfig(level=logging.CRITICAL)

from news_scanner import NewsScanner
from kr_stock_scanner import KRStockScanner

async def test_global_news():
    print("\n🌍 글로벌 뉴스 감시 시스템 가동 중... (PR Newswire 추가됨)\n")

    # --- 1. 미국 뉴스 테스트 ---
    print("🇺🇸 [미국] Business Wire / GlobeNewswire / PR Newswire 통합 스캔 중...")
    try:
        # 이제 api_key 없이도 호출 가능!
        us_scanner = NewsScanner() 
        us_news_list = await us_scanner.scan()
        
        if us_news_list:
            print(f"✅ 미국 호재 뉴스 {len(us_news_list)}건 발견!")
            for news in us_news_list:
                print(f"  [{news['source']}] {news['title']}")
                print(f"    👉 {news['url']}")
        else:
            print("📭 미국: 현재 설정된 '호재 키워드'에 맞는 뉴스가 없습니다.")
            print("   (참고: 단순 뉴스나 실적 발표 예고 등은 필터링됩니다)")
            
    except Exception as e:
        print(f"❌ 미국 뉴스 스캔 오류 상세: {e}")

    print("-" * 50)

    # --- 2. 한국 뉴스 테스트 ---
    print("🇰🇷 [한국] 네이버 금융 실시간 속보 스캔 중...")
    try:
        kr_scanner = KRStockScanner(telegram_bot=None, ai_analyzer=None)
        kr_news_list = await kr_scanner.scan_naver_news()
        
        if kr_news_list:
             print(f"✅ 한국 호재 뉴스 {len(kr_news_list)}건 발견!")
             for news in kr_news_list:
                 title = news.get('title', '제목 없음') if isinstance(news, dict) else str(news)
                 print(f"  - {title}")
        else:
            print("📭 한국: 현재 설정된 키워드에 맞는 뉴스 없음")

    except Exception as e:
        print(f"❌ 한국 뉴스 스캔 오류: {e}")

    print("\n✅ 테스트 종료")

if __name__ == "__main__":
    try:
        asyncio.run(test_global_news())
    except KeyboardInterrupt:
        pass