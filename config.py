import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')  # 선택사항 (현재 사용 안 함)
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')  # 선택사항 (현재 사용 안 함)
    
    @classmethod
    def validate(cls):
        # 필수 API 키만 검증 (Finnhub, Alpha Vantage는 현재 사용 안 함)
        required = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'GEMINI_API_KEY']
        missing = [k for k in required if not getattr(cls, k)]
        if missing: raise ValueError(f"누락된 API 키: {missing}")
    
    # 필터 설정
    MIN_MARKET_CAP = 10_000_000
    MAX_MARKET_CAP = 100_000_000_000_000
    
    MIN_PRICE = 0.3
    MAX_PRICE = 5000.0
    
    MIN_VOLUME_INCREASE = 200
    MIN_PRICE_CHANGE = 10.0
    MIN_AI_SCORE = 7
    
    # 200% 급등 키워드 (퍼플렉시티 데이터 기반)
    POSITIVE_KEYWORDS = [
        # === 1. FDA/바이오 (35% - 가장 강력) ===
        'fda approval', 'fda approved', 'fda clearance', 'fda grants',
        'regulatory approval', 'marketing authorization', 'ce mark',
        'surprise fda nod', 'unexpected approval',
        
        # 임상 성공
        'clinical trial', 'phase 3', 'phase 2', 'phase 1',
        'primary endpoint met', 'statistically significant', 'superior efficacy',
        'positive data', 'positive results', 'met primary endpoint',
        'trial success', 'successful trial', 'pivotal trial',
        
        # 희귀질환/특수 지위
        'orphan drug', 'breakthrough therapy', 'fast track',
        'priority review', 'accelerated approval',
        'rare disease', 'first-in-class', 'best-in-class',
        
        # 확대 프로그램
        'expanded access', 'compassionate use',
        'emergency use authorization', 'eua',
        
        # 라이센싱
        'licensing agreement', 'license deal', 'global rights',
        'exclusive license', 'milestone payment',
        
        # === 2. M&A (25% - 즉각 급등) ===
        'merger', 'acquisition', 'buyout', 'takeover',
        'tender offer', 'all-cash offer',
        'acquired by', 'to be acquired', 'agrees to acquire',
        'definitive agreement', 'merger agreement',
        'strategic alternatives', 'exploring strategic options',
        'going private', 'take private',
        
        # === 3. 정부/국가 전략 (20%) ===
        'government contract', 'doj contract', 'defense contract',
        'awarded contract', 'contract win', 'contract award',
        'government stake', 'sovereign investment',
        'national security', 'critical minerals', 'strategic resource',
        'subsidy', 'grant awarded', 'government funding',
        
        # === 4. IPO/SPAC (15%) ===
        'ipo', 'initial public offering', 'debut',
        'spac merger', 'business combination', 'merger completion',
        'de-spac', 'nasdaq debut', 'nyse debut',
        'oversubscribed', 'upsized offering',
        
        # === 5. 파트너십/전략적 제휴 ===
        'partnership', 'strategic partnership', 'collaboration',
        'nvidia partnership', 'nvidia isaac',
        'joint venture', 'co-development',
        'supply agreement', 'supply deal', 'offtake agreement',
        
        # === 6. 실적 서프라이즈 (5%) ===
        'earnings beat', 'revenue beat', 'guidance raised',
        'record revenue', 'record earnings', 'record sales',
        'blowout quarter', 'massive beat',
        'upgraded guidance', 'raised outlook',
        
        # === 7. 무역/정책 ===
        'tariff', 'trade policy', 'import ban',
        'china ban', 'alternative supplier', 'supply chain shift',
        
        # === 8. 암호화폐/블록체인 ===
        'ethereum treasury', 'bitcoin treasury', 'crypto strategy',
        'vitalik buterin', 'board chairman', 'eth holdings',
        
        # === 9. 한국 키워드 ===
        '승인', '허가', '계약', '수주', '특허',
        '임상', '성공', '합병', '인수', 'M&A',
        '정부 계약', '국방', '방산', '수출',
        '흑자전환', '실적', '신약', '제휴'
    ]
    
    NEGATIVE_KEYWORDS = [
        # === 1. 자금 조달 (희석) ===
        'offering', 'direct offering', 'public offering',
        'registered direct offering', 'shelf offering',
        'secondary offering', 'follow-on offering',
        'at-the-market offering', 'atm offering',
        'dilution', 'dilutive', 'share issuance',
        'stock issuance', 'warrant exercise',
        
        # === 2. 기업 존속 위험 ===
        'bankruptcy', 'chapter 11', 'chapter 7',
        'delisting', 'nasdaq delisting', 'deficiency notice',
        'going concern', 'substantial doubt',
        'wind down', 'liquidation',
        
        # === 3. 법적/규제 리스크 ===
        'investigation', 'sec investigation', 'doj investigation',
        'lawsuit', 'class action', 'securities fraud',
        'subpoena', 'criminal charges',
        'recall', 'product recall', 'safety recall',
        'warning letter', 'fda warning', 'crl',
        'rejected', 'denial', 'failed to meet',
        
        # === 4. 주식 구조 악재 ===
        'reverse split', 'reverse stock split',
        'stock split', 'share consolidation',
        
        # === 5. 거래 중단 ===
        'suspended', 'trading halt', 'halted',
        'circuit breaker', 'volatility halt',
        
        # === 6. 의견/전망 (노이즈) ===
        'analyst says', 'analyst ratings', 'analyst opinion',
        'price target', 'upgraded', 'downgraded',
        'opinion', 'preview', 'outlook', 'forecast',
        'summary', 'recap', 'market wrap',
        'why it moved', 'what to watch', 'what happened',
        
        # === 7. 공매도 ===
        'short seller', 'short report', 'short interest',
        'hindenburg', 'citron', 'muddy waters',
        
        # === 8. 한국 악재 ===
        '루머', '추정', '전망', '예상',
        '적자', '소송', '유상증자', '감자',
        '거래정지', '상장폐지', '분식회계'
    ]

    REDDIT_MIN_MENTIONS = 10
    REDDIT_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing', 'pennystocks']

try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ 설정 오류: {e}")
