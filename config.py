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
    
    # 필수 키 검증
    @classmethod
    def validate(cls):
        required = [
            'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 
            'GEMINI_API_KEY', 'FINNHUB_API_KEY', 
            'ALPHA_VANTAGE_KEY'
        ]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"누락된 API 키: {missing}")
    
    # 필터 설정 [수정됨: 돈 되는 주식 놓치지 않게 범위 대폭 확대]
    MIN_MARKET_CAP = 10_000_000 # 시총 제한 낮춤 (잡주 급등 포착)
    MAX_MARKET_CAP = 10_000_000_000_000
    MIN_PRICE = 0.5    # 동전주도 포함
    MAX_PRICE = 3000.0 # [중요] 100달러 제한 해제 (KELYB 같은 급등주 포착용)
    MIN_VOLUME_INCREASE = 200
    MIN_PRICE_CHANGE = 5.0 # 5% 이상 변동 시 알림
    
    # AI 설정
    MIN_AI_SCORE = 7
    
    # 뉴스 키워드 [보완됨]
    POSITIVE_KEYWORDS = [
        # FDA/바이오 (가장 강력한 호재)
        'fda approval', 'fda approved', 'clinical trial', 'phase 3', 'phase 2',
        'fast track', 'orphan drug', 'breakthrough therapy', 'primary endpoint met',
        'cure', 'treatment approved', '승인', '임상 3상', '임상 성공',
        
        # M&A 및 호재
        'merger', 'acquisition', 'buyout', 'takeover', 'acquired by',
        'earnings beat', 'record revenue', 'guidance raised', 'share buyback',
        'partnership', 'contract won', 'deal signed', 'agreement', 'strategic alliance',
        'product launch', 'patent approved', 'awarded', 'selected by',
        '계약', '수주', 'M&A', '인수', '합병', '특허', '공급'
    ]
    
    NEGATIVE_KEYWORDS = [
        'rumor', 'speculation', 'investigation', 'lawsuit', 'class action',
        'recall', 'warning letter', 'offering', 'dilution', 'suspended',
        'delisting', 'bankruptcy', 'chapter 11', 'rejected', 'failed',
        '루머', '추정', '적자', '소송', '유상증자', '거래정지'
    ]

    # Reddit 설정
    REDDIT_MIN_MENTIONS = 10
    REDDIT_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing', 'pennystocks', 'biotechplays']

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")