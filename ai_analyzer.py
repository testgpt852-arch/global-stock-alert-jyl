import google.generativeai as genai
import logging
import json
import asyncio
from config import Config

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("❌ Gemini API Key가 설정되지 않았습니다.")
        else:
            genai.configure(api_key=self.api_key)
            
        # [핵심 수정] 사용자님이 지정하신 '지원 가능한 최신 모델'로 전면 교체
        self.models = [
            'gemini-3-flash',        # 1순위: 가장 강력한 최신 모델
            'gemini-2.5-flash',      # 2순위: 안정적인 고성능 모델
            'gemini-2.5-flash-lite', # 3순위: 속도와 비용 효율성 모델
            'gemma-3-27b',           # 4순위: 고성능 오픈 모델 (백업용)
        ]

    async def analyze_opportunity(self, stock_data):
        """주식/뉴스 데이터 종합 분석 (오류 방지 및 최신 모델 적용)"""
        
        # [안전장치] 데이터가 없으면 '정보 없음'으로 처리하여 KeyError 방지
        # 뉴스 데이터에는 price가 없을 수 있으므로 .get() 필수
        symbol = stock_data.get('symbol', 'UNKNOWN')
        price = stock_data.get('price', 'N/A')
        change = stock_data.get('change_percent', 'N/A')
        volume = stock_data.get('volume', 'N/A')
        title = stock_data.get('title', 'N/A') # 뉴스 제목
        reason = stock_data.get('trigger_reason', '')

        # AI에게 보낼 프롬프트 작성
        prompt = f"""
        Act as a Wall Street Hedge Fund Manager. Analyze this stock opportunity.
        
        [Target Info]
        - Ticker: {symbol}
        - Price: {price}
        - Change: {change}%
        - Volume: {volume}
        - News/Issue: {title}
        - Detected Reason: {reason}

        [Task]
        1. Analyze the sentiment of the news or price movement.
        2. Give a score (1-10) based on short-term profit potential.
           (News is usually 4-7, Huge breakout is 7-9, Tenbagger material is 9-10)
        3. Suggest a trading strategy (Entry, Target, Stop Loss).
           *If price is 'N/A', estimate purely based on news sentiment.*
        
        [Output Format]
        Provide ONLY a JSON object:
        {{
            "score": <number 1-10>,
            "summary": "<One line catchy summary in Korean>",
            "reasoning": "<Detailed analysis in Korean, under 3 sentences>",
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

        # 모델 순차 시도 (Retry Logic)
        for model_name in self.models:
            try:
                model = genai.GenerativeModel(model_name)
                response = await model.generate_content_async(
                    prompt, 
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 응답 파싱
                text = response.text.strip()
                # 가끔 마크다운 코드블럭(```json ... ```)이 섞여올 때 제거
                if text.startswith("```"):
                    text = text.replace("```json", "").replace("```", "")
                
                result = json.loads(text)
                
                # 필수 필드 검증 및 기본값 채우기
                return {
                    "score": result.get("score", 5),
                    "summary": result.get("summary", "분석 불가"),
                    "reasoning": result.get("reasoning", "데이터 부족으로 분석할 수 없습니다."),
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
                # 모델 하나가 실패해도 다음 모델로 넘어감 (로그만 남김)
                # 예: 429 Quota Exceeded나 모델 없음 오류 시 다음 타자로 자동 교체
                logger.warning(f"⚠️ Model [{model_name}] failed: {e}. Trying next...")
                continue
        
        # 모든 모델 실패 시 기본값 반환 (절대 죽지 않음)
        logger.error("❌ All AI models failed.")
        return {
            "score": 0,
            "summary": "AI 분석 실패",
            "reasoning": "모든 AI 모델이 응답하지 않습니다. (API 할당량 또는 서버 문제)",
            "risk_level": "Unknown",
            "recommendation": "Wait",
            "entry_price": 0, "target_price": 0, "stop_loss": 0,
            "upside": 0, "risk": 0, "position_size": 0
        }