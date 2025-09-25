import os
import google.generativeai as genai

# 환경 변수에서 API 키 읽기
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY 환경변수가 설정되어 있지 않습니다.")

# API 키 설정
genai.configure(api_key=API_KEY)

# 모델 선택
model = genai.GenerativeModel("gemini-1.5-flash")

# 테스트 프롬프트
prompt = "안녕! 지금 이 응답은 Gemini API를 통해 받은거야?"

# API 호출
response = model.generate_content(prompt)

# 결과 출력
print("프롬프트:", prompt)
print("응답:", response.text)
