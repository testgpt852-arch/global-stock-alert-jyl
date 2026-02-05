import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class NewsScanner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.last_scan_time = datetime.now() - timedelta(minutes=10)
        self.processed_news = set()
        
    async def scan(self):
        """뉴스 스캔"""
        alerts = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/news"
                params = {'category': 'general', 'token': self.api_key}
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return alerts
                    
                    news_items = await response.json()
                    
                    for news in news_items[:30]:
                        try:
                            news_id = f"fn_{news.get('id', '')}_{news.get('headline', '')[:20]}"
                            
                            if news_id in self.processed_news:
                                continue
                            
                            news_time = datetime.fromtimestamp(news['datetime'])
                            if news_time < self.last_scan_time:
                                continue
                            
                            if not self.is_important_news(news):
                                continue
                            
                            related = news.get('related')
                            if not related:
                                continue
                            
                            stock_data = await self.get_stock_data(session, related)
                            
                            if stock_data:
                                alert = {
                                    'symbol': stock_data['symbol'],
                                    'price': stock_data['price'],
                                    'change_percent': stock_data['change_percent'],
                                    'volume': stock_data.get('volume', 0),
                                    'trigger_type': 'news',
                                    'trigger_reason': news['headline'][:150],
                                    'news_url': news.get('url', '')
                                }
                                alerts.append(alert)
                                self.processed_news.add(news_id)
                        
                        except Exception as e:
                            continue
                    
                    self.last_scan_time = datetime.now()
                    
        except Exception as e:
            logger.error(f"뉴스 스캔 오류: {e}")
        
        return alerts
    
    def is_important_news(self, news):
        from config import Config
        text = (news.get('headline', '') + ' ' + news.get('summary', '')).lower()
        positive = any(kw.lower() in text for kw in Config.POSITIVE_KEYWORDS)
        negative = any(kw.lower() in text for kw in Config.NEGATIVE_KEYWORDS)
        return positive and not negative
    
    async def get_stock_data(self, session, symbol):
        try:
            url = f"{self.base_url}/quote"
            params = {'symbol': symbol, 'token': self.api_key}
            
            async with session.get(url, params=params, timeout=5) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if not data.get('c') or data['c'] == 0:
                    return None
                
                from config import Config
                price = data['c']
                
                if not (Config.MIN_PRICE <= price <= Config.MAX_PRICE):
                    return None
                
                prev_close = data.get('pc', price)
                if prev_close == 0:
                    return None
                
                change_pct = ((price - prev_close) / prev_close) * 100
                
                if abs(change_pct) < Config.MIN_PRICE_CHANGE:
                    return None
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'change_percent': change_pct,
                    'volume': data.get('v', 0)
                }
        except:
            return None