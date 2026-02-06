import google.generativeai as genai
import logging
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("❌ Gemini API Key가 설정되지 않았습니다.")
        else:
            genai.configure(api_key=self.api_key)
            
        # 최신 모델 리스트 (사용자 지정)
        self.models = [
            'gemini-2.5-flash',      # 1순위: 밸런스 최강
            'gemini-2.5-flash-lite', # 2순위: 속도
            'gemini-3-flash',        # 3순위: 성능
            'gemma-3-27b',           # 4순위: 백업
        ]

    async def _fetch_news_content(self, url):
        """뉴스 링크에 직접 접속하여 본문 텍스트를 긁어옴"""
        if not url or not url.startswith('http'):
            return "본문 수집 불가 (잘못된 URL)"
            
        try:
            # 봇 차단 방지용 헤더
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status != 200:
                        return f"본문 접근 실패 (상태코드: {response.status})"
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 불필요한 스크립트/스타일 제거
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                        
                    # 본문 텍스트 추출 (p 태그 위주)
                    text = ' '.join([p.get_text() for p in soup.find_all('p')])
                    
                    # 너무 짧으면 전체 텍스트 긁기
                    if len(text) < 100:
                        text = soup.get_text(separator=' ', strip=True)
                        
                    # AI 토큰 절약을 위해 길이 제한 (약 2000자)
                    return text[:2000] + "..." if len(text) > 2000 else text
                    
        except Exception as e:
            return f"본문 수집 중 에러: {str(e)}"

    async def analyze_opportunity(self, stock_data):
        """주식/뉴스 데이터 종합 분석 (본문 크롤링 + 호환성 패치 적용)"""
        
        symbol = stock_data.get('symbol', 'UNKNOWN')
        price = stock_data.get('price', 'N/A')
        change = stock_data.get('change_percent', 'N/A')
        volume = stock_data.get('volume', 'N/A')
        title = stock_data.get('title', 'N/A')
        reason = stock_data.get('trigger_reason', '')
        
        # [기능 1] 뉴스 링크가 있으면 본문을 긁어옴
        news_url = stock_data.get('news_url') or stock_data.get('url')
        news_content = "링크 없음"
        
        if news_url:
            # 뉴스 트리거이거나 KR_NEWS인 경우 본문 수집
            if 'news' in stock_data.get('trigger_type', '') or symbol == 'KR_NEWS':
                news_content = await self._fetch_news_content(news_url)
        
        # 프롬프트 구성 (본문 포함)
        prompt = f"""
        Act as a Wall Street Hedge Fund Manager. Analyze this stock opportunity.
        
        [Target Info]
        - Ticker: {symbol}
        - Price: {price}
        - Change: {change}%
        - Volume: {volume}
        - Headline: {title}
        - Reason: {reason}
        
        [News Body Context]
        {news_content}

        [Task]
        1. Read the 'News Body Context' carefully. Does it contain real substance (contracts, numbers, approvals)?
        2. Give a score (1-10) based on short-term profit potential.
        3. Suggest a trading strategy.
        
        [Output Format]
        Provide ONLY a JSON object (No Markdown):
        {{
            "score": <number 1-10>,
            "summary": "<One line catchy summary in Korean>",
            "reasoning": "<Detailed analysis based on BODY TEXT in Korean, under 3 sentences>",
            "risk_level": "<Low/Medium/High/Extreme>",
            "recommendation": "<Buy/Wait/Sell>",
            "entry_price": <number or 0>,
            "target_price": <number or 0>,
            "stop_loss": <number or 0>,
            "upside": <expected upside percentage number>,
            "risk": <expected risk percentage number>,
            "position_size": <recommended percentage 5-100>
        }}
        """

        for model_name in self.models:
            try:
                model = genai.GenerativeModel(model_name)
                
                # [기능 2] 구버전 라이브러리 호환성 패치
                try:
                    response = await model.generate_content_async(
                        prompt, 
                        generation_config={"response_mime_type": "application/json"}
                    )
                except Exception as e:
                    # 라이브러리 버전 이슈로 에러 발생 시 일반 모드로 재시도
                    if "Unknown field" in str(e) or "response_mime_type" in str(e):
                        logger.warning(f"⚠️ 구버전 라이브러리 감지: {model_name} 일반 모드 사용")
                        response = await model.generate_content_async(prompt)
                    else:
                        raise e

                # 응답 파싱
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.replace("```json", "").replace("```", "")
                
                result = json.loads(text)
                
                return {
                    "score": result.get("score", 5),
                    "summary": result.get("summary", "분석 완료"),
                    "reasoning": result.get("reasoning", "데이터 부족"),
                    "risk_level": result.get("risk_level", "High"),
                    "recommendation": result.get("recommendation", "Wait"),
                    "entry_price": result.get("entry_price", 0),
                    "target_price": result.get("target_price", 0),
                    "stop_loss": result.get("stop_loss", 0),
                    "upside": result.get("upside", 0),
                    "risk": result.get("risk", 0),
                    "position_size": result.get("position_size", 10)
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Model [{model_name}] failed: {e}. Trying next...")
                continue
        
        logger.error("❌ All AI models failed.")
        return {
            "score": 0,
            "summary": "AI 분석 실패",
            "reasoning": "AI 연결 오류",
            "risk_level": "Unknown",
            "recommendation": "Wait",
            "entry_price": 0, "target_price": 0, "stop_loss": 0,
            "upside": 0, "risk": 0, "position_size": 0
        }