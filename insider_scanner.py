# -*- coding: utf-8 -*-
import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class InsiderScanner:
    def __init__(self):
        # SEC EDGAR RSS (공식 무료)
        self.rss_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.seen_filings = set()
        
    async def scan(self):
        """Form 4 내부자 거래 스캔"""
        alerts = []
        
        try:
            # Form 4 = 임원/대주주 거래 신고
            params = {
                'action': 'getcurrent',
                'type': '4',  # Form 4
                'company': '',
                'dateb': '',
                'owner': 'include',
                'start': '0',
                'count': '100',
                'output': 'atom'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (InsiderBot/1.0; contact@example.com)'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.rss_url,
                    params=params,
                    headers=headers,
                    timeout=15
                ) as response:
                    if response.status != 200:
                        logger.warning(f"SEC Form 4 접근 실패: {response.status}")
                        return alerts
                    
                    xml = await response.text()
                    soup = BeautifulSoup(xml, 'xml')
                    entries = soup.find_all('entry')[:40]
                    
                    for entry in entries:
                        try:
                            title = entry.find('title').text
                            link = entry.find('link')['href']
                            updated = entry.find('updated').text
                            
                            # 중복 체크
                            if link in self.seen_filings:
                                continue
                            
                            # 최근 6시간 이내만
                            filing_time = datetime.fromisoformat(
                                updated.replace('Z', '+00:00')
                            )
                            now = datetime.now(filing_time.tzinfo)
                            
                            if (now - filing_time).total_seconds() > 21600:  # 6시간
                                continue
                            
                            # 티커 추출
                            ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
                            if not ticker_match:
                                continue
                            
                            ticker = ticker_match.group(1)
                            
                            # Form 4는 매수/매도 구분이 어려우므로 일단 전부 알림
                            # (AI가 나중에 분석)
                            self.seen_filings.add(link)
                            
                            logger.info(f"👔 내부자 거래: {ticker}")
                            
                            alerts.append({
                                'symbol': ticker,
                                'price': 0,
                                'change_percent': 0,
                                'volume': 0,
                                'trigger_type': 'insider_trading',
                                'trigger_reason': '👔 임원/대주주 매매 신고 (Form 4)',
                                'news_url': link,
                                'title': title,
                                'priority': 7  # AI 점수 참고용
                            })
                            
                        except Exception as e:
                            logger.debug(f"Form 4 파싱 오류: {e}")
                            continue
                    
                    # 메모리 관리
                    if len(self.seen_filings) > 500:
                        self.seen_filings.clear()
                        
        except Exception as e:
            logger.error(f"내부자 스캔 오류: {e}")
        
        return alerts
