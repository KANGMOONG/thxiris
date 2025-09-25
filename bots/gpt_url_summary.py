import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI()

def fetch_article_text(url: str) -> str:
    """
    URL에서 본문 텍스트만 추출
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # 기본적으로 기사 본문 추출 (p태그)
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    text = "\n".join(paragraphs)

    return text if text else res.text[:3000]  # 내용 없으면 HTML 일부 반환


def summarize_text(article_text: str) -> str:
    """
    기사 내용을 GPT로 요약
    """
    prompt = f"""
다음 텍스트를 읽고
서론, 본론, 결론 구조로 요약해줘.
각 항목은 20자 이내로 작성하고
다음 형식으로 출력해줘:

-
-
-

텍스트:
\"\"\"{article_text}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=200  # 최신 파라미터 사용
    )

    return response.choices[0].message.content.strip()


def url_summary(chat):
    """
    ChatContext에서 URL 감지 → 요약
    """
    msg = chat.message.msg
    # URL 정규식
    url_pattern = re.compile(r'(https?://[^\s]+)')
    url_match = url_pattern.search(msg)

    if url_match:
        url = url_match.group(0)
        print("메시지가 URL입니다.", url)
        try:
            article_text = fetch_article_text(url)
            summary = summarize_text(article_text)
            print(summary)  # 요약 출력
        except Exception as e:
            print("오류 발생:", e)
    else:
        print("메시지가 URL이 아닙니다.", msg)
