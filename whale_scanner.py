# -*- coding: utf-8 -*-
import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class WhaleScanner:
    def __init__(self):
        # SEC EDGAR RSS (공식 무료)
        self.sec_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.seen_filings = set()
        
        # 유명 고래 화이트리스트 (이들의 공시는 즉시 알림)
        self.famous_whales = {
            'ICAHN': '🐋 Carl Icahn (전설의 행동주의)',
            'ACKMAN': '🐋 Bill Ackman (Pershing Square)',
            'EINHORN': '🐋 David Einhorn (Greenlight)',
            'STARBOARD': '🐋 Starboard Value',
            'ELLIOTT': '🐋 Elliott Management',
            'VALUEACT': '🐋 ValueAct Capital',
            'JANA': '🐋 Jana Partners',
            'THIRD POINT': '🐋 Third Point (Dan Loeb)',
            'PERSHING': '🐋 Pershing Square'
        }
        
    async def scan(self):
        """13D/G/A 대량 지분 공시 스캔"""
        alerts = []
        
        try:
            # SC 13D, 13G, 13D/A, 13G/A 모두 포착
            params = {
                'action': 'getcurrent',
                'type': '',  # 빈 값으로 모든 타입
                'company': '',
                'dateb': '',
                'owner': 'include',
                'start': '0',
                'count': '100',
                'output': 'atom'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (WhaleBotPro/2.0; contact@example.com)'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.sec_url, 
                    params=params, 
                    headers=headers, 
                    timeout=15
                ) as response:
                    if response.status != 200:
                        logger.warning(f"SEC 접근 실패: {response.status}")
                        return alerts
                    
                    xml = await response.text()
                    soup = BeautifulSoup(xml, 'xml')
                    entries = soup.find_all('entry')[:50]
                    
                    for entry in entries:
                        try:
                            title = entry.find('title').text
                            link = entry.find('link')['href']
                            updated = entry.find('updated').text
                            
                            # 중복 체크
                            if link in self.seen_filings:
                                continue
                            
                            # 최근 12시간 이내만
                            filing_time = datetime.fromisoformat(
                                updated.replace('Z', '+00:00')
                            )
                            now = datetime.now(filing_time.tzinfo)
                            
                            if (now - filing_time).total_seconds() > 43200:  # 12시간
                                continue
                            
                            # 13D/G 필터링
                            form_type = None
                            priority = 0
                            
                            if "SC 13D/A" in title:
                                form_type = "🔥 SC 13D/A (지분 추가 매수!)"
                                priority = 10  # 최우선
                            elif "SC 13D" in title:
                                form_type = "⚡ SC 13D (공격적 매수)"
                                priority = 9
                            elif "SC 13G/A" in title:
                                form_type = "📈 SC 13G/A (지분 변동)"
                                priority = 7
                            elif "SC 13G" in title:
                                form_type = "📊 SC 13G (5% 지분 신고)"
                                priority = 6
                            else:
                                continue
                            
                            # 티커 추출
                            ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
                            if not ticker_match:
                                continue
                            
                            ticker = ticker_match.group(1)
                            
                            # 유명 고래 체크
                            whale_name = None
                            for whale_key, whale_desc in self.famous_whales.items():
                                if whale_key in title.upper():
                                    whale_name = whale_desc
                                    priority += 3  # 유명 고래는 가산점
                                    break
                            
                            self.seen_filings.add(link)
                            
                            # 트리거 메시지 생성
                            trigger_msg = form_type
                            if whale_name:
                                trigger_msg = f"{whale_name}\n{form_type}"
                            
                            logger.info(f"🐋 고래 출현: {ticker} - {form_type}")
                            
                            alerts.append({
                                'symbol': ticker,
                                'price': 0,
                                'change_percent': 0,
                                'volume': 0,
                                'trigger_type': 'whale_alert',
                                'trigger_reason': trigger_msg,
                                'news_url': link,
                                'title': title,
                                'priority': priority  # AI 점수 가산용
                            })
                            
                        except Exception as e:
                            logger.debug(f"공시 파싱 오류: {e}")
                            continue
                    
                    # 메모리 관리
                    if len(self.seen_filings) > 500:
                        self.seen_filings.clear()
                        
        except Exception as e:
            logger.error(f"고래 스캔 오류: {e}")
        
        return alerts
