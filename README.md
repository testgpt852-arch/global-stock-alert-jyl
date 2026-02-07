# 🚀 10억 만들기 글로벌 주식 알림 시스템

**텐배거급 급등주를 24시간 자동 포착하는 AI 기반 알림 시스템**

---

## 🎯 **핵심 기능**

### **기본 스캔**
- ✅ **글로벌 뉴스 스캔** (Yahoo Finance + GlobeNewswire + PR Newswire)
- ✅ **실시간 가격 급등** (프리마켓 + 정규장 자동 전환)
- ✅ **소셜 트렌드** (Reddit WallStreetBets)
- ✅ **한국 주식** (네이버 뉴스 + 급등주)

### **고급 스캔 (🆕 신규)**
- 🆕 **내부자 거래 추적** (SEC Form 4)
- 🆕 **숏스퀴즈 감지** (Finviz 고공매도 종목)
- 🆕 **고래 추적** (13D/G/A 대량 지분 공시)
- 🆕 **옵션/다크풀 검증** (yfinance 2차 검증)
- 🆕 **자동 백테스팅** (과거 알림 성과 분석)

### **AI 분석**
- 📊 **Gemini 3.0 Pro/Flash** (뉴스 본문 정밀 분석)
- 🎯 **200% 급등 패턴 필터링** (70개 키워드)
- 💰 **진입가/목표가/손절가** 자동 계산

---

## ⚡ **시작하기**

### **1. 환경 변수 설정**

Railway 또는 로컬 `.env` 파일에 다음 변수 추가:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GEMINI_API_KEY=your_gemini_api_key
FINNHUB_API_KEY=your_finnhub_key (선택)
ALPHA_VANTAGE_KEY=your_alpha_vantage_key (선택)
```

**API 키 발급:**
- Telegram Bot: [@BotFather](https://t.me/botfather)
- Gemini API: [Google AI Studio](https://aistudio.google.com/apikey)
- Finnhub (선택): [finnhub.io](https://finnhub.io)
- Alpha Vantage (선택): [alphavantage.co](https://www.alphavantage.co)

---

### **2. Railway 배포**

#### **A. GitHub 연동**
```bash
# 1. GitHub 저장소 생성
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/global-stock-alert.git
git push -u origin main

# 2. Railway에서 GitHub 연결
# railway.app → New Project → Deploy from GitHub
```

#### **B. 환경 변수 설정**
```
Railway Dashboard → Variables → Raw Editor

TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
GEMINI_API_KEY=...
```

#### **C. 자동 배포**
- GitHub에 Push하면 자동 배포됨
- Logs에서 실시간 확인 가능

---

### **3. 로컬 테스트**

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. .env 파일 생성
echo "TELEGRAM_TOKEN=your_token" > .env
echo "TELEGRAM_CHAT_ID=your_chat_id" >> .env
echo "GEMINI_API_KEY=your_key" >> .env

# 4. 실행
python main.py
```

---

## 📊 **시스템 구조**

```
┌──────────────────────────────────────────────┐
│         1차 스캔 (여러 소스 동시 탐색)          │
├──────────────────────────────────────────────┤
│ • 뉴스 스캐너 (Yahoo/GlobeNewswire/PR)        │
│ • 가격 스캐너 (프리마켓/정규장)                │
│ • 소셜 스캐너 (Reddit)                        │
│ • 내부자 스캐너 (Form 4)                      │
│ • 숏스퀴즈 스캐너 (Finviz)                    │
│ • 고래 스캐너 (13D/G)                         │
└──────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────┐
│        2차 검증 (급등주만 정밀 검문)           │
├──────────────────────────────────────────────┤
│ • 옵션 거래량 폭발 체크 (yfinance)            │
│ • 다크풀/Block Trade 감지 (3-Sigma)          │
└──────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────┐
│           AI 분석 (Gemini 3.0)              │
├──────────────────────────────────────────────┤
│ • 뉴스 본문 크롤링 (3000자)                   │
│ • 키워드 매칭 (70개 패턴)                     │
│ • 1-10점 점수 산출                           │
│ • 진입가/목표가/손절가 계산                   │
└──────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────┐
│      텔레그램 알림 + 백테스팅 기록             │
└──────────────────────────────────────────────┘
```

---

## 🎯 **필터링 기준**

### **미국 주식**
```python
시가총액: $10M ~ $100T
가격: $0.5 ~ $5000
등락률: +5% 이상
거래대금: $2M+ (프리마켓) / $10M+ (정규장)
AI 점수: 7점 이상 (고급 신호는 4점+)
```

### **한국 주식**
```python
시가총액: 500억원 이하 우선
가격: 1,000원 ~ 100,000원
등락률: +4% 이상
거래대금: 50억원 이상
```

---

## 🔧 **커스터마이징**

### **키워드 추가**
`config.py` 파일 수정:

```python
POSITIVE_KEYWORDS = [
    'your_keyword',
    '신규 패턴',
    ...
]
```

### **AI 점수 기준 변경**
`config.py`:

```python
MIN_AI_SCORE = 7  # 기본값 (4~10 조정 가능)
```

### **스캔 주기 변경**
`main.py`:

```python
scan_interval = 30  # 기본 30초 (15~120 권장)
```

---

## 📈 **백테스팅**

시스템이 자동으로 알림 성과를 기록합니다.

```python
# 7일 후 성과 확인
tracker = PerformanceTracker()
report = await tracker.backtest(days=7)
print(report)
```

**출력 예시:**
```
📊 백테스팅 결과 (7일 전 알림)

총 알림: 45개
성공 (20%+ 상승): 28개
성공률: 62.2%
평균 수익률: +34.5%

고점수(8+) 알림: 12개
고점수 성공률: 83.3%
```

---

## 💰 **비용**

| 항목 | 무료 한도 | 유료 전환 시 |
|------|----------|-------------|
| Railway | $5/월 (500시간) | $5/월 추가 |
| Gemini API | 무료 (분당 15회) | 필요 없음 |
| Finnhub | 무료 (분당 60회) | 필요 없음 |
| yfinance | 완전 무료 | 무료 |

**총 비용: $0 ~ $5/월**

---

## ⚠️ **주의사항**

1. **투자 책임**: 이 시스템은 참고용이며, 투자 손실은 사용자 책임입니다.
2. **API 제한**: 무료 API는 요청 제한이 있으므로 스캔 주기를 너무 짧게 설정하지 마세요.
3. **AI 한계**: Gemini API도 가끔 실패할 수 있습니다. 멀티모델 폴백이 작동합니다.

---

## 📞 **문제 해결**

### **"Unknown symbol" 오류**
→ `kr_stock_scanner.py`에서 `symbol` 키 누락. 최신 버전 확인.

### **"google-genai not found"**
→ `pip install google-genai` (google-generativeai 아님)

### **Railway 메모리 부족**
→ `scan_interval`을 60초로 늘리기.

---

## 📜 **라이선스**

MIT License - 자유롭게 사용 및 수정 가능

---

## 🙏 **크레딧**

- **Claude 3.7 Sonnet** (시스템 설계)
- **Gemini 2.5 Flash** (AI 분석 엔진)
- **Anthropic + Google** (AI 모델 제공)

---

**행운을 빕니다! 🚀💰**
