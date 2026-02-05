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
    
    # 필터 설정
    MIN_MARKET_CAP = 50_000_000
    MAX_MARKET_CAP = 5_000_000_000
    MIN_PRICE = 1.0
    MAX_PRICE = 100.0
    MIN_VOLUME_INCREASE = 200
    MIN_PRICE_CHANGE = 5.0
    
    # AI 설정
    MIN_AI_SCORE = 7
    
    # 뉴스 키워드
    POSITIVE_KEYWORDS = [
        'fda approval', 'clinical trial', 'merger', 'acquisition',
        'earnings beat', 'partnership', 'contract', 'patent',
        'breakthrough', 'launch', '승인', '계약', '수주'
    ]
    
    NEGATIVE_KEYWORDS = [
        'rumor', 'speculation', 'investigation', 'lawsuit',
        '루머', '추정', '적자'
    ]

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")