import google.generativeai as genai
from config import Config
import sys

def test_connection_without_quota():
    print("\n🧪 [AI 연결 테스트] 할당량(Quota) 미사용 모드")
    print("=" * 50)

    # 1. API 키 확인
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        print("❌ 오류: config.py에 GEMINI_API_KEY가 없습니다.")
        return

    masked_key = api_key[:5] + "*" * 10 + api_key[-5:]
    print(f"🔑 API Key 확인됨: {masked_key}")

    try:
        # 2. 구글 서버 접속 시도
        genai.configure(api_key=api_key)
        print("📡 Google Gemini 서버에 접속 중... (질문 안 함)")

        # 3. 모델 목록 조회 (이 기능은 생성이 아니라 '조회'라서 무료/무제한입니다)
        models = list(genai.list_models())
        
        # 생성(generateContent)이 가능한 모델만 필터링
        chat_models = [m.name.replace('models/', '') for m in models if 'generateContent' in m.supported_generation_methods]

        if chat_models:
            print("\n✅ [연결 성공] 구글 서버와 정상적으로 통신했습니다!")
            print(f"📝 현재 내 키로 사용 가능한 모델 수: {len(chat_models)}개")
            
            # 우리가 쓰려는 모델이 목록에 있는지 확인
            my_targets = ['gemini-2.5-flash', 'gemini-3-flash', 'gemma-3-27b']
            
            print("\n🔍 [주요 모델 상태 확인]")
            for target in my_targets:
                if target in chat_models:
                    print(f"  ✅ {target}: OK (사용 가능)")
                else:
                    # 최신 모델은 리스트에 늦게 뜨기도 하지만, 연결 성공했으면 보통 됩니다.
                    print(f"  ⚠️ {target}: 목록 미노출 (하지만 연결은 성공)")
        else:
            print("\n⚠️ 연결은 됐는데, 사용 가능한 모델이 하나도 안 보입니다. (API 키 권한 문제 가능성)")

    except Exception as e:
        print(f"\n❌ [연결 실패] 에러가 발생했습니다:")
        print(f"👉 {e}")
        print("\nTip: '403' 에러면 키가 틀린 것이고, 'ConnectTimeout'이면 인터넷 문제입니다.")

    print("=" * 50)

if __name__ == "__main__":
    test_connection_without_quota()