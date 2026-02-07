# -*- coding: utf-8 -*-
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ShortSqueezeScanner:
    def __init__(self):
        # Finviz 고공매도 종목 스크리너
        self.url = "https://finviz.com/screener.ashx?v=111&f=sh_short_o30"
        
    async def scan(self):
        """숏스퀴즈 가능성 종목 스캔"""
        alerts = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"Finviz 접근 실패: {response.status}")
                        return alerts
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 테이블 파싱
                    table = soup.find('table', class_='screener_table') or soup.find('table', id='screener-table')
                    
                    if not table:
                        logger.warning("Finviz 테이블을 찾을 수 없음")
                        return alerts
                    
                    rows = table.find_all('tr')[1:21]  # 헤더 제외, 상위 20개
                    
                    for row in rows:
                        try:
                            cols = row.find_all('td')
                            if len(cols) < 12:
                                continue
                            
                            # 1번 컬럼: 티커
                            symbol = cols[1].text.strip()
                            
                            # 6번 컬럼: 가격
                            price_text = cols[6].text.strip()
                            price = float(price_text) if price_text.replace('.', '', 1).isdigit() else 0
                            
                            # 9번 컬럼: 공매도 비율
                            short_text = cols[9].text.strip().replace('%', '')
                            short_float = float(short_text) if short_text.replace('.', '', 1).isdigit() else 0
                            
                            # 10번 컬럼: 등락률
                            change_text = cols[10].text.strip().replace('%', '').replace('+', '')
                            change_pct = float(change_text) if change_text.replace('.', '', 1).replace('-', '', 1).isdigit() else 0
                            
                            # 필터: 공매도 30%+ AND 상승 중
                            if short_float < 30:
                                continue
                            
                            if change_pct < 3:  # 최소 3% 상승
                                continue
                            
                            alerts.append({
                                'symbol': symbol,
                                'price': price,
                                'change_percent': change_pct,
                                'volume': 0,
                                'trigger_type': 'short_squeeze',
                                'trigger_reason': f'💎 숏스퀴즈 징후 (공매도 {short_float:.0f}% + {change_pct:+.1f}%↑)',
                                'short_float': short_float,
                                'priority': 8  # 높은 우선순위
                            })
                            
                            logger.info(f"💎 숏스퀴즈: {symbol} (공매도 {short_float}%)")
                            
                        except Exception as e:
                            logger.debug(f"행 파싱 오류: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"숏스퀴즈 스캔 오류: {e}")
        
        return alerts
