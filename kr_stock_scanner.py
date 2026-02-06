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
        self.cooldown = 7200 # 2시간 쿨다운
        
    async def scan(self):
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
        """네이버 뉴스 스캔 (기존 동일)"""
        alerts = []
        try:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200: return alerts
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    news_candidates = soup.select('dl.articleList dd.articleSubject a')
                    if not news_candidates: news_candidates = soup.select('ul.realtimeNewsList dl dd.articleSubject a')
                    if not news_candidates: news_candidates = soup.select('dt.articleSubject a')

                    for news in news_candidates[:15]:
                        try:
                            title = news.get('title') or news.get_text(strip=True)
                            if not title: continue
                            link = news['href']
                            if not link.startswith('http'): link = "https://finance.naver.com" + link
                            if link in self.alerted_stocks: continue
                            if self.is_important_kr_news(title):
                                self.alerted_stocks[link] = datetime.now()
                                alerts.append({'title': title, 'news_url': link, 'trigger_type': 'news', 'trigger_reason': '📰 특징주 뉴스'})
                        except: continue
        except Exception: pass
        return alerts
    
    async def scan_price_surge(self):
        """급등주 스캔 (시가총액 필터 적용)"""
        alerts = []
        try:
            url = "https://finance.naver.com/sise/sise_quant.naver"
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200: return alerts
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.type_2 tr')[2:100]
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 12: continue
                            name_elem = cols[1].select_one('a')
                            if not name_elem: continue
                            
                            name = name_elem.get_text(strip=True)
                            code_match = re.search(r'code=(\d+)', name_elem['href'])
                            if not code_match: continue
                            code = code_match.group(1)
                            
                            price_txt = cols[2].get_text(strip=True).replace(',', '')
                            price = int(price_txt) if price_txt.isdigit() else 0
                            
                            change_txt = cols[4].get_text(strip=True).replace('%', '').replace('+', '').strip()
                            change_pct = float(change_txt) if change_txt.replace('.','',1).isdigit() else 0.0
                            
                            vol_txt = cols[6].get_text(strip=True).replace(',', '')
                            volume = int(vol_txt) if vol_txt.isdigit() else 0
                            
                            # 거래대금 (억 단위)
                            trade_value_100m = (price * volume) / 100000000

                            # ============================================
                            # 🎯 1. 1차 필터 (기본 조건)
                            # ============================================
                            if price < 1000: continue        # 동전주 삭제
                            if price > 100000: continue      # 10만원 이상 황제주 삭제 (무거움)
                            if change_pct < 4.0: continue    # 4% 미만 짤짤이 삭제
                            if trade_value_100m < 50: continue # 50억 미만 거래대금 삭제 (확 상향)

                            # 쿨다운 체크
                            if code in self.alerted_stocks:
                                last_alert = self.alerted_stocks[code]
                                if (datetime.now() - last_alert).total_seconds() < self.cooldown:
                                    continue

                            # ============================================
                            # 🎯 2. 2차 필터 (시가총액 조회 - 무거운 놈 쳐내기)
                            # ============================================
                            market_cap_100m = await self.get_market_cap(code, session)
                            
                            # 시총 8,000억 이상이면 "너무 무겁다" 판단하여 패스
                            # (단, 거래대금이 2,000억 이상 터진 초대박 주도주는 예외적으로 허용)
                            if market_cap_100m > 8000 and trade_value_100m < 2000:
                                continue

                            # 알림 사유 작성
                            reason = f"💎 가벼운 급등주 (시총 {int(market_cap_100m)}억)\n💰 거래대금 {int(trade_value_100m)}억 터짐 (+{change_pct:.1f}%)"
                            
                            self.alerted_stocks[code] = datetime.now()
                            alerts.append({
                                'symbol': code,
                                'name': name,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trade_value_100m': trade_value_100m,
                                'trigger_type': 'price_surge',
                                'trigger_reason': reason,
                                'news_url': f"https://finance.naver.com/item/main.naver?code={code}"
                            })
                            
                        except Exception: continue
        except Exception: pass
        return alerts

    async def get_market_cap(self, code, session):
        """종목 상세 페이지에서 시가총액(억 단위) 파싱"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            async with session.get(url, timeout=5) as response:
                if response.status != 200: return 999999 # 에러나면 무거운 걸로 간주해서 스킵
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 시가총액 찾기 (네이버 금융 상세페이지 구조)
                mc_elem = soup.select_one('#_market_sum')
                if mc_elem:
                    mc_text = mc_elem.get_text(strip=True)
                    # "1조 2,345" -> 12345 (억 단위 변환)
                    mc_text = mc_text.replace(',', '').replace('조', '')
                    # 1조가 넘으면 '조'를 없애고 단위를 맞춰야 함.
                    # 하지만 네이버는 '1조 2345' 형태로 줌. 단순 replace하면 '1 2345'가 됨.
                    # 간단하게 텍스트 길이와 패턴으로 추정
                    
                    # 정확한 파싱 로직
                    val = 0
                    if '조' in mc_elem.get_text():
                        parts = mc_elem.get_text().split('조')
                        trillion = int(re.sub(r'\D', '', parts[0])) * 10000
                        billion = 0
                        if len(parts) > 1 and parts[1].strip():
                            billion = int(re.sub(r'\D', '', parts[1]))
                        val = trillion + billion
                    else:
                        val = int(re.sub(r'\D', '', mc_elem.get_text()))
                    return val
        except: pass
        return 999999 # 파싱 실패 시 안전하게 큰 값 반환 (알림 제외)

    def is_important_kr_news(self, title):
        has_pos = any(kw in title for kw in Config.POSITIVE_KEYWORDS)
        has_neg = any(kw in title for kw in Config.NEGATIVE_KEYWORDS)
        return has_pos and not has_neg