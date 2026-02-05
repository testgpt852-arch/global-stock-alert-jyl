import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
    
    @classmethod
    def validate(cls):
        required = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'GEMINI_API_KEY', 'FINNHUB_API_KEY', 'ALPHA_VANTAGE_KEY']
        missing = [k for k in required if not getattr(cls, k)]
        if missing: raise ValueError(f"누락된 API 키: {missing}")
    
    # [설정 변경됨]
    MIN_MARKET_CAP = 10_000_000
    MAX_MARKET_CAP = 100_000_000_000_000
    
    MIN_PRICE = 0.3      # 동전주 포함
    MAX_PRICE = 5000.0   # 100달러 제한 해제 (중요)
    
    MIN_VOLUME_INCREASE = 200
    
    MIN_PRICE_CHANGE = 10.0  # 10% 이상 급등만 알림 (알림 폭탄 방지)
    
    MIN_AI_SCORE = 7
    
# 뉴스 키워드 (최적화 버전)
    POSITIVE_KEYWORDS = [
        # 1. FDA/바이오 (가장 강력한 한방)
        'fda approval', 'fda approved', 'clinical trial', 'phase 3', 
        'primary endpoint met', 'statistically significant', # [추가] 임상 성공의 핵심 표현
        'fast track', 'orphan drug', 'breakthrough therapy',
        'licensing agreement', # [추가] 기술 수출 (돈 버는 뉴스)
        
        # 2. M&A 및 경영권 (즉각 급등)
        'merger', 'acquisition', 'buyout', 'takeover', 'tender offer', # [추가] 공개매수
        'strategic alternatives', # [추가] 매각 검토 (기대감)
        'acquired by', 'deal signed',
        
        # 3. 지분 및 투자 (큰손 유입)
        'strategic investment', 'acquired a stake', # [추가] 지분 취득
        'share buyback', 'repurchase program', # [추가] 자사주 매입
        'activist investor', # [추가] 행동주의 투자자 개입
        
        # 4. 실적 및 정부 계약 (돈 버는 뉴스)
        'earnings beat', 'record revenue', 'guidance raised',
        'contract won', 'awarded', 'government contract', # [추가] 정부 계약
        'subsidy', 'grant', # [추가] 보조금 수령
        'partnership', 'agreement', 'supply deal',
        
        # 5. 기타 호재
        'product launch', 'patent approved', 
        '승인', '계약', '수주', 'M&A', '인수', '합병', '공급'
    ]
    
    NEGATIVE_KEYWORDS = [
        # 금융 악재 (돈이 마르는 뉴스)
        'offering', 'direct offering', 'public offering', 'shelf offering', # [추가] 유상증자 종류 세분화
        'dilution', 'issuance', # [추가] 주식 발행(희석)
        
        # 기업 존속 위험
        'bankruptcy', 'chapter 11', 'delisting', 'deficiency notice', # [추가] 상폐 경고
        'going concern', # [추가] 계속기업 존속 불확실
        
        # 법적/규제 리스크
        'investigation', 'lawsuit', 'class action', 'fraud', 
        'subpoena', # [추가] 소환장
        'recall', 'warning letter', 'rejected', 'crl', # [추가] FDA 승인 거절(CRL)
        
        # 시장 악재
        'rumor', 'speculation', 'short seller', 'short report', # [추가] 공매도 리포트
        'reverse split', # [추가] 주식 병합 (폭락 징조)
        'suspended', 'halted', # 거래 정지
        '루머', '추정', '적자', '소송', '유상증자', '거래정지', '감자'

        # [추가] 의견/전망 거르기 (팩트만 받기 위해)
        'analyst says', 'analyst ratings', 'price target', # 애널리스트 말말말 제외
        'opinion', 'preview', 'outlook', 'forecast',       # 단순 전망 제외
        'summary', 'recap', 'market wrap',                 # 장 마감 시황 제외
        'why it moved', 'what to watch'                    # 주가 변동 해설 제외
    ]

    REDDIT_MIN_MENTIONS = 10
    REDDIT_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing', 'pennystocks']

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")