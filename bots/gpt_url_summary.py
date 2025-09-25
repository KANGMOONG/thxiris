import re
import requests
from bs4 import BeautifulSoup  # 웹페이지 텍스트 추출용 (pip install beautifulsoup4)
from openai import OpenAI

# OpenAI 클라이언트 생성 (환경변수 OPENAI_API_KEY 필요)
client = OpenAI()

def fetch_article_text(url: str) -> str:
    """
    URL에서 기사/본문 텍스트를 가져오는 함수
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        # 가장 간단히 <body> 텍스트 전체 추출
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception as e:
        print("기사 텍스트 가져오기 실패:", e)
        return ""

def summarize_text(article_text: str) -> str:
    """
    OpenAI GPT 모델을 이용해 텍스트 요약
    """
    if not article_text:
        return "요약할 텍스트가 없습니다."

    response = client.chat.completions.create(
        model="gpt-4o",  # 사용 중인 모델명
        messages=[
            {"role": "system", "content": "아래 텍스트 서론,본론,결론 구조로 3줄 한국어로 간결하게 요약해줘."},
            {"role": "user", "content": article_text}
        ],
        # max_tokens → max_completion_tokens로 교체
        max_completion_tokens=500
    )

    return response.choices[0].message.content.strip()

def url_summary(chat):
    """
    chat.message.msg에서 URL을 감지 후
    본문을 가져와 요약을 출력
    """
    msg = chat.message.msg
    url_pattern = re.compile(r'https?://[^\s]+')

    if url_pattern.search(msg):
        url = url_pattern.search(msg).group()
        print("메시지가 URL입니다.", url)

        # 기사 내용 가져오기
        article_text = fetch_article_text(url)
        # 요약 생성
        summary = summarize_text(article_text)
        print("요약 결과:", summary)
    else:
        print("URL이 감지되지 않았습니다:", msg)
