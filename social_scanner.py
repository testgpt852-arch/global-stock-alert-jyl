import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from collections import Counter
import re
from config import Config

logger = logging.getLogger(__name__)

class SocialScanner:
    def __init__(self):
        self.reddit_base = "https://www.reddit.com"
        self.last_posts = set()
        
        # [핵심] WSB에서 자주 언급되는 인기 종목 리스트 (노이즈 방지용 화이트리스트)
        # 이 리스트에 있는 건 $ 없이도 인식, 없는 건 $가 붙어야만 인식 ($ABC)
        self.popular_tickers = {
            'NVDA', 'TSLA', 'AAPL', 'AMD', 'MSFT', 'AMZN', 'GOOGL', 'META', 'GME', 'AMC',
            'PLTR', 'SOFI', 'COIN', 'MSTR', 'MARA', 'RIOT', 'HOOD', 'DKNG', 'RIVN', 'LCID',
            'NIO', 'BABA', 'PDD', 'TQQQ', 'SQQQ', 'SOXL', 'SOXS', 'TSLL', 'NVDL', 'BITX',
            'SMCI', 'ARM', 'INTC', 'MU', 'QCOM', 'AVGO', 'NFLX', 'DIS', 'PYPL', 'SQ',
            'AFRM', 'UPST', 'CVNA', 'OPEN', 'Z', 'RDFN', 'PTON', 'ROKU', 'TDOC', 'ZM',
            'SNOW', 'DDOG', 'NET', 'CRWD', 'PANW', 'ZS', 'FTNT', 'NOW', 'CRM', 'ADBE',
            'ORCL', 'IBM', 'CSCO', 'TXN', 'ADI', 'LRCX', 'KLAC', 'AMAT', 'ASML', 'TSM',
            'ON', 'STM', 'WOLF', 'MP', 'ALB', 'LAC', 'LTHM', 'FCX', 'CLF', 'X',
            'NUE', 'STLD', 'AA', 'CENX', 'XOM', 'CVX', 'OXY', 'COP', 'EOG', 'PXD',
            'DVN', 'MRO', 'APA', 'KMI', 'WMB', 'ET', 'MPLX', 'EPD', 'PAA', 'LNG',
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V',
            'MA', 'PYPL', 'JNJ', 'UNH', 'LLY', 'MRK', 'ABBV', 'PFE', 'BMY', 'AMGN',
            'GILD', 'VRTX', 'REGN', 'MRNA', 'BNTX', 'NVAX', 'SPY', 'QQQ', 'IWM', 'DIA',
            'VIX', 'UVXY', 'UVIX', 'SVIX', 'TLT', 'TMF', 'TMV', 'SH', 'PSQ', 'DJT', 'RDDT'
        }

    async def scan(self):
        """소셜 미디어 트렌드 스캔"""
        alerts = []
        
        try:
            # WallStreetBets 스캔
            wsb_mentions = await self.scan_subreddit('wallstreetbets')
            
            # 언급량 기준 필터링
            for symbol, count in wsb_mentions.most_common(10):
                if count >= Config.REDDIT_MIN_MENTIONS:
                    logger.info(f"🔥 레딧 급등 포착: {symbol} ({count}회)")
                    
                    alert = {
                        'symbol': symbol,
                        'price': 0, # 가격은 나중에 채움
                        'change_percent': 0,
                        'volume': 0,
                        'trigger_type': 'social_trend',
                        'trigger_reason': f'🔥 Reddit 언급 폭발 ({count}회/1h)'
                    }
                    alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Social scan error: {e}")
        
        return alerts
    
    async def scan_subreddit(self, subreddit):
        """특정 서브레딧 스캔"""
        mentions = Counter()
        
        try:
            url = f"{self.reddit_base}/r/{subreddit}/new.json?limit=100" # 100개로 늘림
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return mentions
                    
                    data = await response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    # 1시간 이내 글만
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    
                    for post_data in posts:
                        try:
                            post = post_data['data']
                            
                            # 중복 체크
                            if post['id'] in self.last_posts: continue
                            
                            # 시간 체크
                            created_utc = post.get('created_utc', 0)
                            post_time = datetime.fromtimestamp(created_utc)
                            if post_time < cutoff_time: continue
                            
                            # 텍스트 합치기
                            title = post.get('title', '')
                            selftext = post.get('selftext', '')
                            full_text = f"{title} {selftext}"
                            
                            # 티커 추출
                            tickers = self.extract_tickers(full_text)
                            mentions.update(tickers)
                            
                            self.last_posts.add(post['id'])
                            
                        except Exception:
                            continue
                    
                    if len(self.last_posts) > 1000:
                        self.last_posts.clear()
                    
        except Exception as e:
            logger.error(f"Error scanning r/{subreddit}: {e}")
        
        return mentions
    
    def extract_tickers(self, text):
        """[수정됨] 노이즈 제거 강화"""
        text = text.upper()
        found_tickers = set()
        
        # 1. $가 붙은 티커 찾기 ($TSLA, $AAPL) -> 가장 확실함
        cashtags = re.findall(r'\$([A-Z]{2,5})', text)
        for tag in cashtags:
            # $가 붙어있으면 웬만하면 인정 (단, 너무 흔한 단어 제외)
            if tag not in {'THE', 'FOR', 'NEW', 'USA', 'USD'}:
                found_tickers.add(tag)
        
        # 2. $ 없이 단어만 있는 경우 -> 화이트리스트에 있는 것만 인정
        # (NVDA, GME 같은 유명한 건 $ 안 붙이고 쓰기 때문)
        words = re.findall(r'\b([A-Z]{2,5})\b', text)
        for word in words:
            if word in self.popular_tickers:
                found_tickers.add(word)
                
        return list(found_tickers)