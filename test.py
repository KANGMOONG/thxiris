import os
from dotenv import load_dotenv
import google.generativeai as genai

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY 환경변수가 설정되어 있지 않습니다. .env 파일을 확인하세요.")

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
