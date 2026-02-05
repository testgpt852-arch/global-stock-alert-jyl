import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from collections import Counter
import re

logger = logging.getLogger(__name__)

class SocialScanner:
    def __init__(self):
        self.reddit_base = "https://www.reddit.com"
        self.last_posts = set()  # 중복 방지
        
    async def scan(self):
        """소셜 미디어 트렌드 스캔"""
        alerts = []
        
        try:
            # WallStreetBets 스캔
            wsb_mentions = await self.scan_subreddit('wallstreetbets')
            
            # 급증 종목 찾기
            from config import Config
            for symbol, count in wsb_mentions.most_common(10):
                if count >= Config.REDDIT_MIN_MENTIONS:
                    
                    # 실제 가격 정보는 나중에 채워짐
                    alert = {
                        'symbol': symbol,
                        'price': 0,
                        'change_percent': 0,
                        'volume': 0,
                        'trigger_type': 'social_trend',
                        'trigger_reason': f'Reddit 급등 언급 {count}회 (1시간)'
                    }
                    
                    alerts.append(alert)
                    logger.info(f"🔥 {symbol} trending on Reddit: {count} mentions")
            
        except Exception as e:
            logger.error(f"Social scan error: {e}")
        
        return alerts
    
    async def scan_subreddit(self, subreddit):
        """특정 서브레딧 스캔"""
        mentions = Counter()
        
        try:
            # Reddit JSON API (인증 불필요)
            url = f"{self.reddit_base}/r/{subreddit}/new.json"
            headers = {'User-Agent': 'StockScanner/1.0'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Reddit API error: {response.status}")
                        return mentions
                    
                    data = await response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    
                    for post_data in posts[:50]:  # 최근 50개
                        try:
                            post = post_data['data']
                            
                            # 중복 체크
                            post_id = post['id']
                            if post_id in self.last_posts:
                                continue
                            
                            # 시간 체크
                            post_time = datetime.fromtimestamp(post['created_utc'])
                            if post_time < cutoff_time:
                                continue
                            
                            # 티커 추출
                            title = post.get('title', '')
                            selftext = post.get('selftext', '')
                            text = f"{title} {selftext}"
                            
                            tickers = self.extract_tickers(text)
                            mentions.update(tickers)
                            
                            self.last_posts.add(post_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing post: {e}")
                            continue
                    
                    # 메모리 관리
                    if len(self.last_posts) > 500:
                        self.last_posts.clear()
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout scanning r/{subreddit}")
        except Exception as e:
            logger.error(f"Error scanning r/{subreddit}: {e}")
        
        return mentions
    
    def extract_tickers(self, text):
        """텍스트에서 주식 티커 추출"""
        # $AAPL 또는 AAPL 형태
        pattern = r'\$?([A-Z]{2,5})\b'
        matches = re.findall(pattern, text.upper())
        
        # 일반 영어 단어 제외
        exclude_words = {
            'THE', 'AND', 'OR', 'NOT', 'BUT', 'FOR', 'ARE', 'WAS', 'WERE',
            'YOLO', 'DD', 'TA', 'CEO', 'CFO', 'IPO', 'ATH', 'ATL',
            'MOON', 'HOLD', 'LONG', 'SHORT', 'CALL', 'PUT', 'BUY', 'SELL',
            'GOOD', 'BEST', 'HUGE', 'HUGE', 'FROM', 'THIS', 'THAT',
            'WHAT', 'WHEN', 'WHERE', 'WHO', 'WHY', 'HOW',
            'JUST', 'LIKE', 'MAKE', 'TIME', 'YEAR', 'WEEK', 'HAVE'
        }
        
        tickers = []
        for match in matches:
            if match not in exclude_words and 2 <= len(match) <= 5:
                tickers.append(match)
        
        return tickers