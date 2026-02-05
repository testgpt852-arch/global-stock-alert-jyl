import aiohttp
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PriceScanner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        
        # 핵심 모니터링 종목 (변동성 큰 것 위주)
        self.watchlist = [
            # 메가캡
            'AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT',
            'AMZN', 'GOOGL', 'META',
            
            # 바이오텍 (급등 잦음)
            'MRNA', 'BNTX', 'NVAX', 'SAVA', 'BLUE',
            
            # 고변동성 테크
            'PLTR', 'SOFI', 'RIVN', 'LCID', 'NIO',
            
            # 밈주
            'GME', 'AMC', 'BBBY',
            
            # 기타 인기주
            'COIN', 'HOOD', 'SNAP', 'PINS'
        ]
        
        self.last_prices = {}  # 이전 가격 저장
        
    async def scan(self):
        """가격 급등/급락 스캔"""
        alerts = []
        
        try:
            # API 한도 고려하여 5개씩 처리
            batch_size = 5
            for i in range(0, len(self.watchlist), batch_size):
                batch = self.watchlist[i:i+batch_size]
                
                async with aiohttp.ClientSession() as session:
                    tasks = [self.check_stock(session, symbol) for symbol in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Price check error: {result}")
                            continue
                        if result:
                            alerts.append(result)
                
                # API 한도 보호
                await asyncio.sleep(12)  # Alpha Vantage 무료: 5 req/min
                
        except Exception as e:
            logger.error(f"Price scan error: {e}")
        
        return alerts
    
    async def check_stock(self, session, symbol):
        """개별 종목 급등/급락 체크"""
        try:
            # 실시간 가격 조회 (GLOBAL_QUOTE)
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            async with session.get(self.base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if 'Global Quote' not in data:
                    return None
                
                quote = data['Global Quote']
                
                if not quote or '05. price' not in quote:
                    return None
                
                current_price = float(quote['05. price'])
                change_pct = float(quote['10. change percent'].rstrip('%'))
                volume = int(quote.get('06. volume', 0))
                
                # 가격 필터
                from config import Config
                if not (Config.MIN_PRICE <= current_price <= Config.MAX_PRICE):
                    return None
                
                # 급등/급락 체크
                if abs(change_pct) >= Config.MIN_PRICE_CHANGE:
                    
                    # 추가 검증: 거래량 체크
                    if volume > 0:  # 거래량 있어야 함
                        
                        direction = "급등" if change_pct > 0 else "급락"
                        
                        logger.info(f"🚀 {symbol} {direction} detected: {change_pct:+.2f}%")
                        
                        return {
                            'symbol': symbol,
                            'price': current_price,
                            'change_percent': change_pct,
                            'volume': volume,
                            'trigger_type': 'price_surge',
                            'trigger_reason': f'{direction} {abs(change_pct):.1f}% (거래량: {volume:,})'
                        }
                
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout checking {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
            return None