import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from iris import ChatContext
from iris.decorators import *

def url_summary(chat):
# 1️⃣ OpenAI API 키 로드
 api_key = os.getenv("OPENAI_API_KEY")
 client = OpenAI(api_key=api_key)

# 2️⃣ 요약할 URL
 url = chat.message.msg

# 3️⃣ HTML 가져와서 본문 텍스트 추출
 def fetch_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 기사 본문이 <p> 태그 안에 있다고 가정
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        return text
    except Exception as e:
        print("URL 불러오기 실패:", e)
        return ""

# 4️⃣ GPT-5 nano로 서론·본론·결론 100자 내 요약
 def summarize_text(article_text):
    if not article_text:
        return "본문 내용을 가져오지 못했습니다."

    prompt = (
        "다음 글을 읽고 서론, 본론, 결론 구조로 100자 내로 요약해줘:\n\n"
        f"{article_text}\n\n"
        "형식: - ...,  - ...,  - ..."
    )

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )

    return response.choices[0].message["content"]

# 5️⃣ 실행
 article_text = fetch_article_text(url)
 summary = summarize_text(article_text)
 print(summary)
