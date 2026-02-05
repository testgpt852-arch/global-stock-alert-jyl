import aiohttp
import asyncio
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import re
from config import Config

logger = logging.getLogger(__name__)

class KRStockScanner:
    def __init__(self, telegram_bot, ai_analyzer):
        self.telegram = telegram_bot
        self.ai = ai_analyzer
        self.alerted_stocks = {}
        self.cooldown = 3600
        
    async def scan(self):
        """전체 스캔"""
        all_alerts = []
        try:
            results = await asyncio.gather(
                self.scan_naver_news(),
                self.scan_price_surge(),
                return_exceptions=True
            )
            for result in results:
                if isinstance(result, list):
                    for alert in result: alert['market'] = 'KR'
                    all_alerts.extend(result)
        except Exception: pass
        return all_alerts
    
    async def scan_naver_news(self):
        """네이버 뉴스 스캔 (구조 변경 대응)"""
        alerts = []
        try:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://finance.naver.com/'
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200: return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # [수정] 네이버 뉴스 리스트 찾는 3중 안전장치
                    # 1. dl.articleList 안의 dd.articleSubject (가장 일반적)
                    news_candidates = soup.select('dl.articleList dd.articleSubject a')
                    
                    # 2. 없으면 ul.realtimeNewsList 안의 dl > dd > a (실시간 리스트)
                    if not news_candidates:
                        news_candidates = soup.select('ul.realtimeNewsList dl dd.articleSubject a')
                        
                    # 3. 그래도 없으면 dt.articleSubject (썸네일 없는 기사)
                    if not news_candidates:
                        news_candidates = soup.select('dt.articleSubject a')

                    for news in news_candidates[:20]:
                        try:
                            title = news.get('title') or news.get_text(strip=True)
                            if not title: continue
                            
                            link = news['href']
                            if not link.startswith('http'): link = "https://finance.naver.com" + link
                            
                            # 키워드 검사
                            if self.is_important_kr_news(title):
                                alerts.append({
                                    'title': title,
                                    'news_url': link,
                                    'trigger_type': 'news',
                                    'trigger_reason': '📰 네이버 특징주 뉴스'
                                })
                        except: continue
        except Exception as e:
            logger.error(f"네이버 뉴스 오류: {e}")
        
        return alerts
    
    async def scan_price_surge(self):
        """급등주 스캔 (기존 유지)"""
        alerts = []
        try:
            url = "https://finance.naver.com/sise/sise_quant.naver"
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200: return alerts
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.type_2 tr')[2:22]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 12: continue
                            name_elem = cols[1].select_one('a')
                            if not name_elem: continue
                            
                            name = name_elem.get_text(strip=True)
                            code = re.search(r'code=(\d+)', name_elem['href']).group(1)
                            price = int(cols[2].get_text(strip=True).replace(',', ''))
                            change_pct = float(cols[4].get_text(strip=True).replace('%', '').replace('+', ''))
                            volume = int(cols[6].get_text(strip=True).replace(',', ''))
                            
                            if change_pct < 5.0: continue
                            if not (1000 <= price <= 500000): continue
                            if code in self.alerted_stocks:
                                if (datetime.now() - self.alerted_stocks[code]).seconds < self.cooldown: continue
                            
                            self.alerted_stocks[code] = datetime.now()
                            alerts.append({
                                'symbol': code,
                                'name': name,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trigger_type': 'price_surge',
                                'trigger_reason': f'🔥 거래량 폭발 급등 (+{change_pct:.1f}%)',
                                'news_url': f"https://finance.naver.com/item/main.naver?code={code}"
                            })
                        except: continue
        except Exception: pass
        return alerts
    
    def is_important_kr_news(self, title):
        has_pos = any(kw in title for kw in Config.POSITIVE_KEYWORDS)
        has_neg = any(kw in title for kw in Config.NEGATIVE_KEYWORDS)
        return has_pos and not has_neg