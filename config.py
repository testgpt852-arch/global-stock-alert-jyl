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
        # FDA/의료
        'fda approval', 'fda approved', 'clinical trial', 'phase 3',
        'breakthrough', 'cure', 'treatment approved', '승인',
        
        # M&A
        'merger', 'acquisition', 'buyout', 'takeover', 'acquired by',
        
        # 실적
        'earnings beat', 'revenue growth', 'profit surge',
        'guidance raised', 'record earnings',
        
        # 계약/파트너십
        'partnership', 'contract won', 'deal signed', 'agreement', '계약', '수주',
        
        # 제품
        'product launch', 'new product', 'patent approved',
        
        # 투자
        'investment', 'funding round', 'raised capital'
    ]
    
    NEGATIVE_KEYWORDS = [
        # 루머/추측
        'rumor', 'speculation', 'could', 'may', 'might',
        'analyst says', 'analyst thinks', '루머', '추정'
        
        # 부정 이슈
        'investigation', 'lawsuit', 'recall', 'warning',
        'delay', 'failed', 'rejected', 'declined', '적자',
    ]

    # Reddit 설정
    REDDIT_MIN_MENTIONS = 10  # 최소 언급 횟수
    REDDIT_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing']

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")