# -*- coding: utf-8 -*-
import sys
from config import Config

def test_connection_only():
    print("\n🧪 [AI 연결 확인] 할당량(Quota) 절약 모드")
    print("=" * 60)

    # 1. 라이브러리 설치 여부 확인
    try:
        from google import genai
    except ImportError:
        print("❌ [오류] 'google-genai' 라이브러리가 설치되지 않았습니다.")
        print("👉 터미널에 다음 명령어를 입력하세요: pip install google-genai")
        return

    # 2. API 키 확인
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        print("❌ [설정 오류] config.py에 GEMINI_API_KEY가 없습니다.")
        return
    
    masked_key = api_key[:5] + "*" * 10 + api_key[-5:]
    print(f"🔑 API Key: {masked_key}")

    # 3. 모델 목록 조회 (이 기능은 생성이 아니라 '조회'라서 무료입니다)
    try:
        client = genai.Client(api_key=api_key)
        print("📡 구글 서버에 모델 목록 요청 중...")
        
        # 모델 리스트 가져오기
        all_models = list(client.models.list())
        
        print("✅ [연결 성공] 서버와 정상 통신 중입니다!")
        
        # 4. 우리가 코드(ai_analyzer.py)에서 쓰기로 한 모델들이 있는지 확인
        target_models = [
            'gemini-3-pro-preview',     # 1순위: 현존 최강 지능 (Generation 3 Pro)
            'gemini-2.5-pro',           # 2순위: 검증된 고지능 (Generation 2.5 Pro)
            'gemini-3-flash-preview',   # 3순위: 차세대 밸런스 (Generation 3 Flash)
            'gemini-2.5-flash',         # 4순위: 표준 모델
            'gemma-3-27b-it',           # 5순위: 최후의 보루 (Gemma 최상위)
        ]
        
        # 모델명에서 'models/' 접두사 떼고 저장
        available_names = [m.name.split('/')[-1] for m in all_models]
        
        print("\n🔍 [사용할 모델 상태 체크]")
        all_ready = True
        for target in target_models:
            if target in available_names:
                print(f"  ✅ {target}: 준비 완료 (OK)")
            else:
                print(f"  ⚠️ {target}: 목록에 없음 (권한 부족 또는 이름 변경됨)")
                all_ready = False
        
        if all_ready:
            print("\n🎉 완벽합니다! 모든 모델을 사용할 준비가 되었습니다.")
        else:
            print("\n⚠️ 일부 모델이 보이지 않지만, '준비 완료'된 모델들로 자동 작동합니다.")
                
    except Exception as e:
        print(f"\n❌ [연결 실패] 원인: {e}")
        if "403" in str(e):
            print("💡 힌트: API 키가 잘못되었거나 권한이 없습니다.")
        elif "Connection" in str(e):
            print("💡 힌트: 인터넷 연결을 확인하세요.")

    print("=" * 60)

if __name__ == "__main__":
    test_connection_only()