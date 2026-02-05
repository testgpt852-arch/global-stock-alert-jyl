import aiohttp
import asyncio
from datetime import datetime, time
import pytz
import logging
from bs4 import BeautifulSoup
import re

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
                if isinstance(result, Exception):
                    continue
                if result:
                    for alert in result:
                        alert['market'] = 'KR'
                    all_alerts.extend(result)
            
        except Exception as e:
            logger.error(f"한국 스캔 오류: {e}")
        
        return all_alerts
    
    async def scan_naver_news(self):
        """네이버 뉴스"""
        alerts = []
        
        try:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
            
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_list = soup.select('.newsList .articleSubject')[:20]
                    
                    for news in news_list:
                        try:
                            title = news.get_text(strip=True)
                            
                            if not self.is_important_kr_news(title):
                                continue
                            
                            # 종목 추출 간소화 (실제로는 더 복잡)
                            # 여기서는 급등주에서 처리하도록 스킵
                            
                        except:
                            continue
                    
        except Exception as e:
            logger.error(f"네이버 뉴스 오류: {e}")
        
        return alerts
    
    async def scan_price_surge(self):
        """급등주"""
        alerts = []
        
        try:
            url = "https://finance.naver.com/sise/sise_quant.naver"
            
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    rows = soup.select('table.type_2 tr')[2:22]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 12:
                                continue
                            
                            name_elem = cols[1].select_one('a')
                            if not name_elem:
                                continue
                            
                            name = name_elem.get_text(strip=True)
                            href = name_elem['href']
                            code_match = re.search(r'code=(\d+)', href)
                            if not code_match:
                                continue
                            
                            code = code_match.group(1)
                            
                            price_text = cols[2].get_text(strip=True).replace(',', '')
                            price = int(price_text)
                            
                            change_text = cols[4].get_text(strip=True).replace('%', '').replace('+', '')
                            change_pct = float(change_text)
                            
                            volume_text = cols[6].get_text(strip=True).replace(',', '')
                            volume = int(volume_text) if volume_text else 0
                            
                            if change_pct < 5.0:
                                continue
                            
                            if not (1000 <= price <= 500000):
                                continue
                            
                            alert = {
                                'symbol': code,
                                'name': name,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trigger_type': 'price_surge',
                                'trigger_reason': f'급등 {change_pct:+.1f}%'
                            }
                            
                            alerts.append(alert)
                            
                        except:
                            continue
                    
        except Exception as e:
            logger.error(f"급등주 스캔 오류: {e}")
        
        return alerts
    
    def is_important_kr_news(self, title):
        keywords = ['승인', '계약', '수주', '특허', '흑자전환', 
                   'FDA', '임상', '신약', '제휴', '합병']
        negative = ['루머', '추정', '전망', '적자']
        
        has_pos = any(kw in title for kw in keywords)
        has_neg = any(kw in title for kw in negative)
        
        return has_pos and not has_neg