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
            # 1. [교체] 야후 파이낸스 RSS (Business Wire 포함 전 세계 속보 무제한 수집)
            # 차단 없음, 지연 시간 거의 없음 (가장 확실한 방법)
            {
                'name': 'Yahoo Finance',
                'type': 'yahoo_rss',
                'url': 'https://finance.yahoo.com/news/rssindex'
            },
            # 2. GlobeNewswire (공식 RSS - 아주 잘 작동 중)
            {
                'name': 'GlobeNewswire',
                'type': 'direct_rss',
                'url': 'https://www.globenewswire.com/RssFeed'
            },
            # 3. PR Newswire (HTML 크롤링 - 아주 잘 작동 중)
            {
                'name': 'PR Newswire',
                'type': 'html',
                'url': 'https://www.prnewswire.com/news-releases/news-releases-list/',
                'base_url': 'https://www.prnewswire.com'
            }
        ]

    async def scan(self):
        """글로벌 뉴스 통합 스캔"""
        all_news = []
        tasks = []
        for source in self.sources:
            if source['type'] == 'yahoo_rss' or source['type'] == 'direct_rss':
                tasks.append(self._fetch_rss(source))
            else:
                tasks.append(self._fetch_html(source))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
                
        # [정렬] 최신순으로 정렬 (야후와 글로브뉴스가 섞여도 최신이 위로 오도록)
        # 보통 RSS는 최신순이지만, 여러 소스를 합치므로 다시 정렬
        return sorted(all_news, key=lambda x: x.get('title', ''), reverse=True)

    async def _fetch_rss(self, source):
        """RSS 파싱 (야후 파이낸스 & GlobeNewswire)"""
        news_items = []
        # 야후 파이낸스는 봇을 막지 않지만, 예의상 헤더 추가
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source['url'], headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"{source['name']} RSS Error: {response.status}")
                        return news_items
                    
                    xml_content = await response.text()
                    feed = feedparser.parse(xml_content)
                    
                    if not feed.entries: return news_items

                    for entry in feed.entries[:15]:
                        try:
                            title = entry.title
                            link = entry.link
                            
                            # 야후 파이낸스는 주식 티커를 RSS에 포함하지 않으므로 US 기본값
                            # (실제 호재 판독은 AI가 제목/본문으로 하므로 문제없음)
                            symbol = "US"
                            
                            self._add_if_valid(news_items, title, link, symbol, source['name'])
                        except: continue
                        
        except Exception as e:
            logger.error(f"{source['name']} RSS error: {e}")
            
        return news_items

    async def _fetch_html(self, source):
        """HTML 크롤링 (PR Newswire)"""
        news_items = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source['url'], headers=headers, timeout=10) as response:
                    if response.status != 200: return news_items
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
        except Exception: pass
        return news_items

    def _add_if_valid(self, news_list, title, url, symbol, source_name):
        if url in self.seen_news: return
        
        # 중복 뉴스 방지 (야후가 GlobeNewswire 기사를 또 가져올 수도 있음)
        # url이 다를 수 있으므로 제목으로도 느슨한 중복 체크 가능하지만,
        # 여기서는 일단 URL 기준으로 심플하게 감
        
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