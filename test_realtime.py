import asyncio
from price_scanner import PriceScanner
from datetime import datetime

# 테스트를 위해 Config 값을 임시로 무시하고 다 출력하게 할 순 없지만,
# 현재 로직상 10% 이상 급등주가 없으면 아무것도 안 뜰 수 있습니다.
# 따라서 이 코드는 PriceScanner가 가져온 "원본 데이터"를 확인하는 용도입니다.

async def test_yahoo_crawling():
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%H:%M:%S')}")
    print("🔍 야후 파이낸스 실시간 데이터 크롤링 중...\n")
    
    # 키는 필요 없지만 형식상 넣어줌
    scanner = PriceScanner(av_key="dummy", finnhub_key="dummy")
    
    # 스캔 실행
    alerts = await scanner.scan()
    
    if not alerts:
        print("📭 현재 조건(10% 이상 상승 등)을 만족하는 급등주가 없거나, 장이 닫혀서 데이터가 없습니다.")
        print("💡 팁: config.py에서 MIN_PRICE_CHANGE를 0으로 잠시 바꾸고 테스트하면 다 뜹니다.")
    else:
        print(f"🔥 총 {len(alerts)}개의 급등주 포착!\n")
        print(f"{'종목명':<8} {'현재가':<10} {'등락률':<10} {'거래량'}")
        print("-" * 40)
        
        for stock in alerts:
            symbol = stock['symbol']
            price = stock['price']
            change = stock['change_percent']
            volume = stock['volume']
            
            print(f"{symbol:<8} ${price:<9.2f} {change:+.2f}%    {volume:,}")

if __name__ == "__main__":
    # 윈도우 환경에서 asyncio 오류 방지
    try:
        asyncio.run(test_yahoo_crawling())
    except KeyboardInterrupt:
        pass