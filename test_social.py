import asyncio
from social_scanner import SocialScanner

async def test_reddit_hype():
    print("🕵️‍♂️ Reddit(월스트리트벳) 잠입 수사 중... (약 3~5초 소요)")
    
    scanner = SocialScanner()
    
    # 설정 파일 무시하고 직접 데이터를 긁어옵니다.
    # 최근 1시간 이내에 올라온 글만 분석합니다.
    mentions = await scanner.scan_subreddit('wallstreetbets')
    
    if not mentions:
        print("📭 데이터 수집 실패 (일시적 오류거나 언급된 종목이 없음)")
        print("👉 팁: social_scanner.py 파일이 같은 폴더에 있어야 합니다.")
        return

    print(f"\n🔥 지금 미국 개미들이 미쳐있는 종목 Top 20 🔥")
    print("-" * 45)
    print(f"{'순위':<6} {'종목코드':<10} {'언급량 (1시간 내)':<15}")
    print("-" * 45)
    
    # 언급량 순으로 정렬해서 상위 20개 출력
    top_mentions = mentions.most_common(20)
    
    if not top_mentions:
        print("👀 특이사항 없음: 최근 1시간 동안 언급된 주식 티커가 없습니다.")
    
    for rank, (symbol, count) in enumerate(top_mentions, 1):
        # 언급량이 많을수록 불꽃 이모지 추가
        fire = "🔥🔥🔥" if count >= 10 else "🔥" if count >= 5 else ""
        print(f"{rank:<6} {symbol:<10} {count:<5}회 {fire}")

    print("-" * 45)
    print("💡 해석: 상위권에 낯선 종목이 있다면, 그게 바로 오늘의 '밈 주식' 후보입니다.")

if __name__ == "__main__":
    try:
        asyncio.run(test_reddit_hype())
    except Exception as e:
        print(f"❌ 오류 발생: {e}")