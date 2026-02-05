import aiohttp
import asyncio
from datetime import datetime, time
import pytz
import logging
from bs4 import BeautifulSoup
import re
from config import Config  # [추가] 설정을 가져오기 위해 import

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
        """네이버 뉴스 스캔"""
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
                    
                    # 뉴스 리스트 가져오기
                    news_list = soup.select('.newsList .articleSubject')[:20]
                    
                    for news in news_list:
                        try:
                            title = news.get_text(strip=True)
                            link = "https://finance.naver.com" + news.select_one('a')['href']
                            
                            # [수정] config.py의 키워드를 사용하여 검사
                            if not self.is_important_kr_news(title):
                                continue
                                
                            # (참고) 네이버 뉴스 페이지는 뉴스 제목만 있고 '어떤 종목'인지 바로 알기 어려운 구조라
                            # 여기서는 '시장 전체의 핫한 뉴스'를 감지하는 용도로 쓰거나,
                            # 제목에 종목명이 포함된 경우를 찾아야 하는데 로직이 복잡하여 일단 패스합니다.
                            # 만약 특정 키워드가 발견되면 '시장 속보'로 알림을 보낼 수도 있습니다.
                            
                        except:
                            continue
        except Exception as e:
            logger.error(f"네이버 뉴스 오류: {e}")
        
        return alerts
    
    async def scan_price_surge(self):
        """급등주 스캔 (거래량 상위 & 급등)"""
        alerts = []
        try:
            url = "https://finance.naver.com/sise/sise_quant.naver" # 거래량 상위
            
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200: return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    rows = soup.select('table.type_2 tr')[2:22] # 상위권만 스캔
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 12: continue
                            
                            name_elem = cols[1].select_one('a')
                            if not name_elem: continue
                            
                            name = name_elem.get_text(strip=True)
                            href = name_elem['href']
                            code_match = re.search(r'code=(\d+)', href)
                            if not code_match: continue
                            code = code_match.group(1)
                            
                            price = int(cols[2].get_text(strip=True).replace(',', ''))
                            change_pct = float(cols[4].get_text(strip=True).replace('%', '').replace('+', ''))
                            volume = int(cols[6].get_text(strip=True).replace(',', ''))
                            
                            # 필터링
                            if change_pct < 5.0: continue
                            if not (1000 <= price <= 500000): continue
                            
                            # 중복 방지 (간단 쿨다운)
                            if code in self.alerted_stocks:
                                last_time = self.alerted_stocks[code]
                                if (datetime.now() - last_time).seconds < self.cooldown:
                                    continue
                            
                            self.alerted_stocks[code] = datetime.now()

                            alert = {
                                'symbol': code,
                                'name': name,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trigger_type': 'price_surge',
                                'trigger_reason': f'🔥 거래량 폭발 급등 (+{change_pct:.1f}%)',
                                'news_url': f"https://finance.naver.com/item/main.naver?code={code}"
                            }
                            alerts.append(alert)
                            
                        except: continue
        except Exception as e:
            logger.error(f"급등주 스캔 오류: {e}")
        
        return alerts
    
    def is_important_kr_news(self, title):
        """[수정됨] Config 파일의 키워드를 불러와서 검사"""
        # Config에 있는 키워드 리스트를 가져옴
        positive_keywords = Config.POSITIVE_KEYWORDS
        negative_keywords = Config.NEGATIVE_KEYWORDS
        
        # 하나라도 포함되면 True
        has_pos = any(kw in title for kw in positive_keywords)
        # 하나라도 포함되면 False (필터링)
        has_neg = any(kw in title for kw in negative_keywords)
        
        return has_pos and not has_neg