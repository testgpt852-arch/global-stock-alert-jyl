import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging
import feedparser
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class NewsScanner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.finnhub_url = "https://finnhub.io/api/v1"
        
        # Wire 서비스 RSS 피드
        self.wire_feeds = {
            'prnewswire': 'https://www.prnewswire.com/rss/news-releases-list.rss',
            'businesswire': 'https://www.businesswire.com/portal/site/home/news/',
            'globenewswire': 'https://www.globenewswire.com/RssFeed/subjectcode/51-Medical%20Equipment%20And%20Devices/feedTitle/GlobeNewswire%20-%20Medical%20Equipment%20And%20Devices'
        }
        
        self.last_scan_time = datetime.now() - timedelta(minutes=10)
        self.processed_news = set()
        
    async def scan(self):
        """통합 뉴스 스캔"""
        alerts = []
        
        try:
            # 동시에 모든 소스 스캔
            results = await asyncio.gather(
                self.scan_finnhub(),
                self.scan_prnewswire(),
                self.scan_businesswire(),
                self.scan_globenewswire(),
                return_exceptions=True
            )
            
            # 결과 병합
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"News source error: {result}")
                    continue
                if result:
                    alerts.extend(result)
            
            # 중복 제거 (같은 종목 같은 시간)
            unique_alerts = self.deduplicate_alerts(alerts)
            
            logger.info(f"📰 Found {len(unique_alerts)} unique news alerts")
            
        except Exception as e:
            logger.error(f"News scan error: {e}")
        
        return unique_alerts
    
    async def scan_finnhub(self):
        """Finnhub 뉴스 (기존 코드)"""
        alerts = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.finnhub_url}/news"
                params = {
                    'category': 'general',
                    'token': self.api_key
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return alerts
                    
                    news_items = await response.json()
                    
                    for news in news_items[:30]:
                        try:
                            news_id = f"finnhub_{news.get('id', '')}_{news.get('headline', '')[:30]}"
                            
                            if news_id in self.processed_news:
                                continue
                            
                            news_time = datetime.fromtimestamp(news['datetime'])
                            if news_time < self.last_scan_time:
                                continue
                            
                            if not self.is_important_news(news.get('headline', '') + ' ' + news.get('summary', '')):
                                continue
                            
                            related_symbol = news.get('related')
                            if not related_symbol:
                                continue
                            
                            stock_data = await self.get_stock_data(session, related_symbol)
                            
                            if stock_data:
                                alert = {
                                    'symbol': stock_data['symbol'],
                                    'price': stock_data['price'],
                                    'change_percent': stock_data['change_percent'],
                                    'volume': stock_data.get('volume', 0),
                                    'trigger_type': 'news',
                                    'trigger_reason': news['headline'][:150],
                                    'news_url': news.get('url', ''),
                                    'news_source': 'Finnhub'
                                }
                                alerts.append(alert)
                                self.processed_news.add(news_id)
                                
                        except Exception as e:
                            logger.error(f"Finnhub item error: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Finnhub scan error: {e}")
        
        return alerts
    
    async def scan_prnewswire(self):
        """PR Newswire RSS 스캔"""
        return await self.scan_rss_feed('prnewswire', self.wire_feeds['prnewswire'])
    
    async def scan_businesswire(self):
        """Business Wire 스크래핑"""
        alerts = []
        
        try:
            url = "https://www.businesswire.com/portal/site/home/news/"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 최신 뉴스 추출 (구조는 실제 사이트 확인 필요)
                    news_items = soup.find_all('div', class_='bw-release-main', limit=20)
                    
                    for item in news_items:
                        try:
                            title_elem = item.find('a', class_='bw-release-story')
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            link = title_elem['href']
                            
                            # 시간 추출
                            time_elem = item.find('time')
                            if time_elem:
                                news_time_str = time_elem.get('datetime', '')
                                news_time = datetime.fromisoformat(news_time_str.replace('Z', '+00:00'))
                                
                                if news_time < self.last_scan_time:
                                    continue
                            
                            news_id = f"bw_{link}"
                            if news_id in self.processed_news:
                                continue
                            
                            # 중요 뉴스 필터
                            if not self.is_important_news(title):
                                continue
                            
                            # 티커 추출
                            ticker = self.extract_ticker_from_text(title)
                            if not ticker:
                                # 뉴스 본문까지 확인 (옵션)
                                continue
                            
                            # 종목 데이터
                            async with aiohttp.ClientSession() as quote_session:
                                stock_data = await self.get_stock_data(quote_session, ticker)
                            
                            if stock_data:
                                alert = {
                                    'symbol': stock_data['symbol'],
                                    'price': stock_data['price'],
                                    'change_percent': stock_data['change_percent'],
                                    'volume': stock_data.get('volume', 0),
                                    'trigger_type': 'news',
                                    'trigger_reason': title[:150],
                                    'news_url': f"https://www.businesswire.com{link}",
                                    'news_source': 'Business Wire'
                                }
                                alerts.append(alert)
                                self.processed_news.add(news_id)
                                
                        except Exception as e:
                            logger.error(f"Business Wire item error: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Business Wire scan error: {e}")
        
        return alerts
    
    async def scan_globenewswire(self):
        """GlobeNewswire RSS 스캔"""
        return await self.scan_rss_feed('globenewswire', self.wire_feeds['globenewswire'])
    
    async def scan_rss_feed(self, source_name, feed_url):
        """범용 RSS 스캔"""
        alerts = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=15) as response:
                    if response.status != 200:
                        return alerts
                    
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    for entry in feed.entries[:30]:
                        try:
                            title = entry.get('title', '')
                            link = entry.get('link', '')
                            
                            news_id = f"{source_name}_{link}"
                            if news_id in self.processed_news:
                                continue
                            
                            # 시간 체크
                            if hasattr(entry, 'published_parsed'):
                                news_time = datetime(*entry.published_parsed[:6])
                                if news_time < self.last_scan_time:
                                    continue
                            
                            # 중요 뉴스 필터
                            summary = entry.get('summary', '')
                            full_text = f"{title} {summary}"
                            
                            if not self.is_important_news(full_text):
                                continue
                            
                            # 티커 추출
                            ticker = self.extract_ticker_from_text(full_text)
                            if not ticker:
                                continue
                            
                            # 종목 데이터
                            async with aiohttp.ClientSession() as quote_session:
                                stock_data = await self.get_stock_data(quote_session, ticker)
                            
                            if stock_data:
                                alert = {
                                    'symbol': stock_data['symbol'],
                                    'price': stock_data['price'],
                                    'change_percent': stock_data['change_percent'],
                                    'volume': stock_data.get('volume', 0),
                                    'trigger_type': 'news',
                                    'trigger_reason': title[:150],
                                    'news_url': link,
                                    'news_source': source_name
                                }
                                alerts.append(alert)
                                self.processed_news.add(news_id)
                                
                        except Exception as e:
                            logger.error(f"{source_name} item error: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"{source_name} scan error: {e}")
        
        return alerts
    
    def extract_ticker_from_text(self, text):
        """뉴스에서 티커 추출"""
        # (NASDAQ: AAPL) 형태
        pattern1 = r'\((?:NASDAQ|NYSE|NYSEAMERICAN):\s*([A-Z]{1,5})\)'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # $AAPL 형태
        pattern2 = r'\$([A-Z]{2,5})\b'
        match = re.search(pattern2, text)
        if match:
            return match.group(1)
        
        return None
    
    def is_important_news(self, text):
        """중요 뉴스 판별"""
        from config import Config
        
        text_lower = text.lower()
        
        # 긍정 키워드
        positive_match = any(kw.lower() in text_lower for kw in Config.POSITIVE_KEYWORDS)
        
        # 부정 키워드
        negative_match = any(kw.lower() in text_lower for kw in Config.NEGATIVE_KEYWORDS)
        
        return positive_match and not negative_match
    
    async def get_stock_data(self, session, symbol):
        """종목 데이터 조회 (Finnhub 사용)"""
        try:
            url = f"{self.finnhub_url}/quote"
            params = {
                'symbol': symbol,
                'token': self.api_key
            }
            
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
                
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    def deduplicate_alerts(self, alerts):
        """중복 제거 (같은 종목 + 같은 시간대)"""
        seen = {}
        unique = []
        
        for alert in alerts:
            key = alert['symbol']
            
            if key not in seen:
                seen[key] = alert
                unique.append(alert)
            else:
                # 더 높은 점수 또는 더 최근 뉴스 우선
                # 여기서는 단순히 첫 번째만 유지
                pass
        
        return unique