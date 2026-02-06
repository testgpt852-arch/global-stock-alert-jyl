# -*- coding: utf-8 -*-
import asyncio
import os
from google import genai
from config import Config

# 최신 라이브러리 사용
client = genai.Client(api_key=Config.GEMINI_API_KEY)

def list_all_models():
    print("\n📋 [내 API 키로 쓸 수 있는 진짜 모델 명단]")
    print("=" * 60)
    
    try:
        # 1. 모델 목록 조회
        # pager(페이지) 형태로 오므로 리스트로 변환
        all_models = list(client.models.list())
        
        # 2. 보기 좋게 정렬 및 필터링
        # 이름에 'gemini'나 'gemma'가 들어간 것만 추려서 보여줌
        targets = [m for m in all_models if 'gemini' in m.name or 'gemma' in m.name]
        targets.sort(key=lambda x: x.name, reverse=True) # 최신순 정렬(대략적)

        found_gemini_3 = False
        
        for m in targets:
            # 모델 ID에서 'models/' 접두사 제거 (보기 편하게)
            clean_name = m.name.replace('models/', '')
            
            # 설명 출력
            print(f"🔹 ID: {clean_name}")
            
            if 'gemini-3' in clean_name:
                print(f"   ✨ (오! 여기 Gemini 3가 숨어있었네요!)")
                found_gemini_3 = True
            if 'gemma-3' in clean_name:
                print(f"   ✨ (Gemma 3도 여기 있습니다!)")

        print("=" * 60)
        
        if not found_gemini_3:
            print("⚠️ 목록에 'gemini-3'가 안 보인다면, 아직 API 키에 권한이 없거나 배포 전입니다.")
            print("   (대신 gemini-2.5-flash-preview 등을 찾아보세요)")

    except Exception as e:
        print(f"❌ 목록 조회 실패: {e}")

if __name__ == "__main__":
    list_all_models()