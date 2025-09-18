# check_key.py
import os
from google import generativeai as genai

# 1. 환경변수 값 확인
api_key = os.getenv("GEMINI_KEY")
print("API Key from env:", api_key)

# 2. SDK에 적용 테스트
try:
    genai.configure(api_key=api_key)
    print("✅ API Key successfully loaded and configured.")
except Exception as e:
    print("❌ Error configuring API:", e)
