import google.generativeai as genai
import asyncio
import logging
import json
import re

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    async def analyze_opportunity(self, stock_data):
        """투자 기회 AI 분석"""
        try:
            prompt = self._create_analysis_prompt(stock_data)
            
            # 비동기 API 호출
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # JSON 파싱
            analysis = self._parse_response(response.text)
            
            # 검증
            analysis = self._validate_analysis(analysis, stock_data)
            
            logger.info(f"✅ AI analysis complete for {stock_data['symbol']}: {analysis['score']}/10")
            
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._get_fallback_analysis(stock_data)
    
    def _create_analysis_prompt(self, stock):
        """분석 프롬프트 생성"""
        prompt = f"""
당신은 월가의 전설적인 퀀트 트레이더입니다.
다음 급등 신호를 분석하고 투자 가치를 평가하세요.

**종목 정보:**
- 티커: {stock['symbol']}
- 현재가: ${stock['price']:.2f}
- 변화율: {stock['change_percent']:+.2f}%
- 거래량: {stock.get('volume', 'N/A'):,}

**트리거:**
- 유형: {stock['trigger_type']}
- 사유: {stock['trigger_reason']}

**당신의 임무:**
1. 이 기회의 수익 가능성을 1-10점으로 평가
2. 실전 트레이딩 전략 수립
3. 리스크 분석

**출력 형식 (JSON만):**
```json
{{
  "score": 8,
  "summary": "FDA 승인 임박, 역사적 급등 패턴",
  "entry_price": 8.50,
  "target_price": 12.00,
  "stop_loss": 7.80,
  "upside": 40,
  "risk": 10,
  "risk_level": "MEDIUM",
  "position_size": 5,
  "reasoning": "과거 유사 사례 평균 +45% 상승"
}}
```

**평가 기준:**
- 9-10점: 텐버거 가능성 (즉시 풀매수)
- 7-8점: 강력한 기회 (적극 매수)
- 5-6점: 관망 (지켜보기)
- 1-4점: 무시

**중요:** 
- 보수적으로 평가하세요
- 리스크를 과소평가하지 마세요
- JSON 형식을 정확히 지켜주세요
"""
        return prompt
    
    def _parse_response(self, text):
        """AI 응답 파싱"""
        try:
            # JSON 블록 추출
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                json_str = text.split('```')[1].split('```')[0]
            else:
                # JSON 직접 추출 시도
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")
            
            analysis = json.loads(json_str.strip())
            return analysis
            
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            raise
    
    def _validate_analysis(self, analysis, stock_data):
        """분석 결과 검증 및 보정"""
        # 필수 필드 확인
        required_fields = [
            'score', 'summary', 'entry_price', 'target_price', 
            'stop_loss', 'upside', 'risk', 'risk_level', 
            'position_size', 'reasoning'
        ]
        
        for field in required_fields:
            if field not in analysis:
                raise ValueError(f"Missing field: {field}")
        
        # 값 범위 검증
        analysis['score'] = max(1, min(10, int(analysis['score'])))
        analysis['position_size'] = max(1, min(10, int(analysis['position_size'])))
        
        # 가격 검증 (현재가 기준)
        current_price = stock_data['price']
        
        if analysis['entry_price'] <= 0:
            analysis['entry_price'] = current_price
        
        if analysis['target_price'] <= current_price:
            analysis['target_price'] = current_price * 1.2
        
        if analysis['stop_loss'] >= current_price:
            analysis['stop_loss'] = current_price * 0.9
        
        # 수익률 재계산
        analysis['upside'] = ((analysis['target_price'] - current_price) / current_price) * 100
        analysis['risk'] = ((current_price - analysis['stop_loss']) / current_price) * 100
        
        return analysis
    
    def _get_fallback_analysis(self, stock_data):
        """AI 실패 시 기본 분석"""
        price = stock_data['price']
        change = stock_data['change_percent']
        
        # 변동률 기반 간단 점수
        if abs(change) >= 10:
            score = 8
        elif abs(change) >= 7:
            score = 7
        else:
            score = 6
        
        return {
            'score': score,
            'summary': f'{abs(change):.1f}% 급등 - AI 분석 실패',
            'entry_price': price,
            'target_price': price * 1.15,
            'stop_loss': price * 0.92,
            'upside': 15,
            'risk': 8,
            'risk_level': 'MEDIUM',
            'position_size': 3,
            'reasoning': 'AI 분석 오류 - 기본 전략 적용'
        }