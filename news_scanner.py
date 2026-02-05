import aiohttp
import asyncio
import logging
import feedparser
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)

class NewsScanner:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.seen_news = set()
        
        self.sources = [
            # 1. Business Wire (RSS 방식 + 헤더 우회)
            {
                'name': 'Business Wire',
                'type': 'rss',
                # 가장 포괄적인 'Breaking News' 피드
                'url': 'https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVtGW0xNSw=='
            },
            # 2. GlobeNewswire (사용자님이 찾아주신 /RssFeed 적용)
            {
                'name': 'GlobeNewswire',
                'type': 'rss',
                'url': 'https://www.globenewswire.com/RssFeed'
            },
            # 3. PR Newswire (HTML 크롤링)
            {
                'name': 'PR Newswire',
                'type': 'html',
                'url': 'https://www.prnewswire.com/news-releases/news-releases-list/',
                'base_url': 'https://www.prnewswire.com'
            }
        ]

    async def scan(self):
        """미국 3대 뉴스 통합 스캔"""
        all_news = []
        tasks = []
        for source in self.sources:
            if source['type'] == 'rss':
                tasks.append(self._fetch_rss(source))
            else:
                tasks.append(self._fetch_html(source))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
        return all_news

    async def _fetch_rss(self, source):
        """RSS 피드 파싱 (봇 차단 우회 기능 추가)"""
        news_items = []
        
        # [핵심] RSS 요청 시에도 브라우저 헤더를 사용해야 차단 안 당함
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        try:
            # 1. aiohttp로 먼저 원본 데이터를 다운로드 (헤더 적용)
            async with aiohttp.ClientSession() as session:
                async with session.get(source['url'], headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"{source['name']} RSS Error: Status {response.status}")
                        return news_items
                    
                    xml_content = await response.text()
                    
                    # 2. 다운받은 텍스트를 feedparser에게 먹여줌
                    feed = feedparser.parse(xml_content)
                    
                    if not feed.entries:
                        return news_items

                    for entry in feed.entries[:15]:
                        try:
                            title = entry.title
                            link = entry.link
                            
                            # RSS는 보통 티커가 없으므로 기본값
                            symbol = "US"
                            
                            self._add_if_valid(news_items, title, link, symbol, source['name'])
                        except: continue
                        
        except Exception as e:
            logger.error(f"{source['name']} RSS error: {e}")
            
        return news_items

    async def _fetch_html(self, source):
        """HTML 크롤링 (PR Newswire 용)"""
        news_items = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source['url'], headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return news_items
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    articles = soup.select('.card-list .card')[:15]
                    for article in articles:
                        try:
                            title_elem = article.select_one('h3')
                            if not title_elem: continue
                            
                            a_tag = title_elem.find('a')
                            if a_tag:
                                title = a_tag.get_text(strip=True)
                                link = a_tag['href']
                            else:
                                title = title_elem.get_text(strip=True)
                                link = article.find('a')['href']
                            
                            if link and not link.startswith('http'): 
                                link = source['base_url'] + link
                                
                            self._add_if_valid(news_items, title, link, "US", source['name'])
                        except: continue

        except Exception as e:
            logger.error(f"{source['name']} HTML error: {e}")
            
        return news_items

    def _add_if_valid(self, news_list, title, url, symbol, source_name):
        if url in self.seen_news: return
        
        is_positive = any(k in title.lower() for k in Config.POSITIVE_KEYWORDS)
        is_negative = any(k in title.lower() for k in Config.NEGATIVE_KEYWORDS)
        
        if is_positive and not is_negative:
            self.seen_news.add(url)
            news_list.append({
                'symbol': symbol,
                'title': title,
                'url': url,
                'trigger_type': 'news_sentiment',
                'trigger_reason': f'📰 {source_name} 호재 발견',
                'source': source_name
            })
            if len(self.seen_news) > 1000: self.seen_news.clear()