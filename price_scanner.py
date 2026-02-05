import aiohttp
import asyncio
import logging
import re  # [추가됨] 텍스트에서 숫자만 추출하기 위한 도구
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)

class PriceScanner:
    def __init__(self, av_key=None, finnhub_key=None):
        self.url = "https://finance.yahoo.com/markets/stocks/gainers/"
        self.last_scan_result = set()

    async def scan(self):
        """야후 파이낸스 실시간 급등주 크롤링 (인덱스 3번 파싱 버전)"""
        alerts = []
        
        # print(f"\n--- 스캔 시작: {self.url} ---")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            async with aiohttp.ClientSession(max_field_size=32768, max_line_size=32768) as session:
                async with session.get(self.url, headers=headers, timeout=10) as response:
                    
                    if response.status != 200:
                        logger.error(f"Yahoo Connection Error: {response.status}")
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    table = soup.find('table')
                    if not table:
                        return alerts
                        
                    rows = table.find('tbody').find_all('tr')
                    
                    for row in rows:
                        try:
                            cols = row.find_all('td')
                            # 인덱스 6(거래량)까지 필요하므로 최소 7개 확인
                            if len(cols) < 7:
                                continue
                            
                            # --- 데이터 추출 ---
                            
                            # 1. 심볼 (인덱스 0)
                            symbol_text = cols[0].get_text(strip=True)
                            symbol = symbol_text.split(' ')[0].strip()
                            
                            # 2. 현재가 (인덱스 3: "426.58+78.62..." 형태)
                            raw_price_text = cols[3].get_text(strip=True)
                            # 정규식으로 '숫자.숫자' 또는 '숫자' 패턴 중 맨 앞의 것만 찾음
                            match = re.match(r"([\d,.]+)", raw_price_text)
                            if not match:
                                continue
                            price_str = match.group(1).replace(',', '')
                            
                            # 3. 등락률 (인덱스 5: "+22.59%" 형태)
                            change_str = cols[5].get_text(strip=True).replace(',', '').replace('%', '').replace('+', '')
                            
                            # 4. 거래량 (인덱스 6: "670,929" 형태)
                            vol_str = cols[6].get_text(strip=True).replace(',', '')

                            # --- 숫자 변환 ---
                            try:
                                price = float(price_str)
                                change_pct = float(change_str)
                                
                                # 거래량 M/B/k 처리
                                if 'M' in vol_str:
                                    volume = float(vol_str.replace('M', '')) * 1_000_000
                                elif 'B' in vol_str:
                                    volume = float(vol_str.replace('B', '')) * 1_000_000_000
                                elif 'k' in vol_str.lower():
                                    volume = float(vol_str.lower().replace('k', '')) * 1_000
                                else:
                                    volume = float(vol_str) if vol_str.replace('.', '').isdigit() else 0
                                    
                                volume = int(volume)
                                
                            except ValueError:
                                # 숫자 변환 실패 시 스킵
                                continue

                            # --- 필터링 로직 ---
                            
                            # 1. 가격 범위
                            if not (Config.MIN_PRICE <= price <= Config.MAX_PRICE):
                                continue
                                
                            # 2. 변동률 (설정값보다 작으면 제외)
                            if change_pct < Config.MIN_PRICE_CHANGE:
                                continue

                            # 3. 중복 방지
                            scan_id = f"{symbol}_{int(price)}"
                            if scan_id in self.last_scan_result:
                                continue

                            alerts.append({
                                'symbol': symbol,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': volume,
                                'trigger_type': 'market_mover',
                                'trigger_reason': f'🔥 실시간 급등 Top 20 ({change_pct:+.2f}%)'
                            })
                            
                            self.last_scan_result.add(scan_id)
                            
                        except Exception:
                            continue
            
            # 캐시 비우기
            if len(self.last_scan_result) > 500:
                self.last_scan_result.clear()
                
        except Exception as e:
            logger.error(f"Yahoo scan error: {e}")
        
        return alerts