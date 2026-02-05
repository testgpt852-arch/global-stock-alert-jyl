import aiohttp
import asyncio
import logging
from config import Config

logger = logging.getLogger(__name__)

class PriceScanner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.last_scan_result = set() # 중복 알림 방지용 캐시

    async def scan(self):
        """시장 전체 급등/급락 스캔 (Top Gainers & Losers)"""
        alerts = []
        
        try:
            # [변경점] 개별 종목 확인이 아니라 '시장 전체 순위'를 가져옵니다.
            params = {
                'function': 'TOP_GAINERS_LOSERS',
                'apikey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API Error: {response.status}")
                        return alerts
                    
                    data = await response.json()
                    
                    # 'top_gainers'만 봐도 되지만 'top_losers'도 확인 (과대낙폭에 따른 기술적 반등 기회)
                    for category in ['top_gainers', 'top_losers']:
                        if category not in data:
                            continue
                            
                        for item in data[category]:
                            try:
                                symbol = item['ticker']
                                price = float(item['price'])
                                change_amount = float(item['change_amount'])
                                change_pct = float(item['change_percentage'].rstrip('%'))
                                volume = int(item['volume'])
                                
                                # 1. 가격 필터 (Config에서 설정한 넓은 범위 적용)
                                if not (Config.MIN_PRICE <= price <= Config.MAX_PRICE):
                                    continue
                                    
                                # 2. 변동폭 필터 (설정된 % 이상만 알림)
                                if abs(change_pct) < Config.MIN_PRICE_CHANGE:
                                    continue

                                # 3. 중복 방지 (가격이 변해서 또 걸릴 수 있으므로 가격까지 포함해서 키 생성)
                                scan_id = f"{symbol}_{int(price)}" 
                                if scan_id in self.last_scan_result:
                                    continue

                                direction = "급등" if change_pct > 0 else "급락"
                                
                                alerts.append({
                                    'symbol': symbol,
                                    'price': price,
                                    'change_percent': change_pct,
                                    'volume': volume,
                                    'trigger_type': 'market_mover',
                                    'trigger_reason': f'실시간 {direction} 상위 포착 ({change_pct:+.1f}%)'
                                })
                                
                                self.last_scan_result.add(scan_id)
                                
                            except Exception as e:
                                continue
            
            # 메모리 관리 (캐시가 너무 커지면 비움)
            if len(self.last_scan_result) > 1000:
                self.last_scan_result.clear()
                
        except Exception as e:
            logger.error(f"Price scan error: {e}")
        
        return alerts