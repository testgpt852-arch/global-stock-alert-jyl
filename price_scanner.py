import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import pytz 
from config import Config

logger = logging.getLogger(__name__)

class PriceScanner:
    def __init__(self, av_key=None, finnhub_key=None):
        self.last_scan_result = set()
        
        # 1. 정규장 급등 (Regular Market)
        self.url_regular = "https://finance.yahoo.com/markets/stocks/gainers/"
        
        # 2. 프리마켓 급등 (Pre-Market) - 토스(Toss)와 같은 데이터
        self.url_premarket = "https://finance.yahoo.com/markets/stocks/pre-market/"

    async def scan(self):
        """현재 시간에 맞는 시장 데이터를 가져옴"""
        
        # 한국 시간 기준 현재 시간 확인
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        target_urls = []
        
        # [시간대 자동 감지]
        # 프리마켓(데이마켓): 한국시간 오후 5시 ~ 밤 11시 30분
        # 이 시간대에는 야후 메인(Regular)이 멈춰있으므로 Pre-Market을 봐야 함
        if 16 <= now.hour < 23 or (now.hour == 23 and now.minute < 30):
            logger.info(f"🕒 [프리마켓] 장전 거래 데이터를 스캔합니다.")
            target_urls.append(("PRE", self.url_premarket))
        else:
            logger.info(f"🕒 [정규장] 실시간 거래 데이터를 스캔합니다.")
            target_urls.append(("REG", self.url_regular))
            # 정규장 초반에는 프리마켓 데이터도 유효할 수 있으므로 필요시 추가 가능
        
        all_alerts = []
        
        for market_type, url in target_urls:
            alerts = await self._fetch_data(url, market_type)
            all_alerts.extend(alerts)
            
        return all_alerts

    async def _fetch_data(self, url, market_type):
        alerts = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            # [오류 해결 핵심] max_field_size를 65536(64KB)으로 늘려 야후의 대용량 헤더를 받아냄
            async with aiohttp.ClientSession(
                headers=headers,
                max_field_size=65536, 
                max_line_size=65536
            ) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"접속 실패 ({url}): {response.status}")
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    rows = soup.select('table tbody tr')
                    
                    for row in rows:
                        try:
                            cols = row.select('td')
                            if len(cols) < 6: continue
                            
                            symbol_div = cols[0].select_one('.symbol') or cols[0]
                            symbol = symbol_div.get_text(strip=True).split(' ')[0]
                            
                            price_text = cols[1].get_text(strip=True).replace(',', '')
                            price = float(price_text)
                            
                            change_text = cols[3].get_text(strip=True).replace('%', '').replace('+', '').replace(',', '')
                            change_pct = float(change_text)
                            
                            vol_text = cols[5].get_text(strip=True)
                            volume = self.parse_volume(vol_text)
                            
                            trade_value_usd = price * volume
                            
                            # ===============================================
                            # 🦁 하이에나 모드 (토스 괴물 잡기)
                            # ===============================================
                            
                            # 1. 가격: $0.5 미만 휴지조각만 제외 (동전주 허용)
                            if price < 0.5: continue

                            # 2. 거래대금 조건
                            # 프리마켓은 유동성이 적으므로 30억($2M)만 터져도 1위급
                            threshold = 2000000 if market_type == "PRE" else 10000000
                            
                            if trade_value_usd < threshold: continue

                            # 3. 등락률: 최소 5% 이상
                            if change_pct < 5.0: continue

                            # 4. 메시지 작성
                            market_label = "☀️[프리]" if market_type == "PRE" else "🌕[정규]"
                            
                            if change_pct >= 100.0:
                                msg = f'{market_label} 2배 폭등! +{change_pct:.1f}%'
                            elif change_pct >= 50.0:
                                msg = f'{market_label} 미친 급등 +{change_pct:.1f}%'
                            elif change_pct >= 20.0:
                                msg = f'{market_label} 폭등 감지 +{change_pct:.1f}%'
                            else:
                                msg = f'{market_label} 급등 출발 +{change_pct:.1f}%'

                            # 중복 방지 (등락률 2% 변동 시 재알림)
                            scan_id = f"{symbol}_{int(change_pct/2)}" 
                            if scan_id in self.last_scan_result: continue
                                
                            alerts.append({
                                'symbol': symbol,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trade_value_usd': trade_value_usd,
                                'trigger_type': 'price_surge',
                                'trigger_reason': f"{msg} (거래대금 ${int(trade_value_usd/1000000)}M)"
                            })
                            self.last_scan_result.add(scan_id)
                            
                        except Exception: continue
            
            if len(self.last_scan_result) > 1000: self.last_scan_result.clear()
            
        except Exception as e:
            logger.error(f"Scan Error ({url}): {e}")
            
        return alerts

    def parse_volume(self, text):
        text = text.upper().replace(',', '')
        try:
            if 'B' in text: return float(text.replace('B', '')) * 1_000_000_000
            elif 'M' in text: return float(text.replace('M', '')) * 1_000_000
            elif 'K' in text: return float(text.replace('K', '')) * 1_000
            else: return float(text)
        except: return 0.0