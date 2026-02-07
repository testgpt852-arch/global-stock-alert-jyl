# -*- coding: utf-8 -*-
from google import genai
from google.genai import types
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
            # [최신] google.genai 클라이언트
            self.client = genai.Client(api_key=self.api_key)
            
# [수정됨] 무료 계정에서 'limit: 0' 뜨는 Pro 모델 제거
        # 방금 성공한 '3 Flash Preview'를 1순위로 승격
        self.models = [
            'gemini-3-flash-preview',   # 1순위: 방금 성공한 모델 (가장 똑똑하고 빠름)
            'gemini-2.5-flash',         # 2순위: 든든한 국밥 같은 안정성
            'gemma-3-27b-it',           # 3순위: 백업용 오픈 모델
        ]

    async def _fetch_news_content(self, url):
        """뉴스 링크에 접속하여 본문 추출"""
        if not url or not url.startswith('http'):
            return "본문 수집 불가 (잘못된 URL)"
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as response:
                    if response.status != 200:
                        return f"본문 접근 실패 (상태코드: {response.status})"
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 광고/스크립트 제거
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                        
                    # 텍스트 추출
                    text = ' '.join([p.get_text() for p in soup.find_all('p')])
                    
                    if len(text) < 100:
                        text = soup.get_text(separator=' ', strip=True)
                        
                    # AI 입력 한계 고려 (약 3000자 제한)
                    return text[:3000] + "..." if len(text) > 3000 else text
                    
        except Exception as e:
            return f"본문 수집 중 에러: {str(e)}"

    async def analyze_opportunity(self, stock_data):
        """최신 라이브러리 + 지능 순위 모델 적용 분석"""
        
        symbol = stock_data.get('symbol', 'UNKNOWN')
        price = stock_data.get('price', 'N/A')
        change = stock_data.get('change_percent', 'N/A')
        volume = stock_data.get('volume', 'N/A')
        title = stock_data.get('title', 'N/A')
        reason = stock_data.get('trigger_reason', '')
        
        # 1. 뉴스 본문 수집
        news_url = stock_data.get('news_url') or stock_data.get('url')
        news_content = "링크 없음"
        
        if news_url:
            if 'news' in stock_data.get('trigger_type', '') or symbol == 'KR_NEWS':
                news_content = await self._fetch_news_content(news_url)
        
        # 2. 프롬프트 작성 (금융 전문가 페르소나)
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
        1. Read the 'News Body Context' carefully. Look for KEYWORDS: FDA approval, DOJ contract, Takeover, Earnings Beat.
        2. Evaluate if this is a real catalyst for >200% gain or just noise.
        3. Score (1-10) for short-term profit potential.
        
        [Output Format]
        Provide ONLY a JSON object:
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

        # 3. 모델 순차 실행 (똑똑한 순서대로)
        for model_name in self.models:
            try:
                # 최신 google.genai 방식 호출
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                text = response.text.strip()
                if text.startswith("```"):
                    text = text.replace("```json", "").replace("```", "")
                
                result = json.loads(text)
                
                # 성공 시 바로 리턴
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
                # 에러 발생 시 로그 남기고 다음 모델(차선책)로 넘어감
                logger.warning(f"⚠️ [{model_name}] 분석 실패: {e} -> 다음 모델 시도")
                continue
        
        # 모든 모델 실패 시
        logger.error("❌ 모든 AI 모델이 응답하지 않습니다.")
        return {
            "score": 0,
            "summary": "AI 분석 실패",
            "reasoning": "시스템 오류",
            "risk_level": "Unknown",
            "recommendation": "Wait",
            "entry_price": 0, "target_price": 0, "stop_loss": 0,
            "upside": 0, "risk": 0, "position_size": 0
        }