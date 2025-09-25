import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI()

def fetch_article_text(url: str) -> str:
    """
    URL에서 본문 텍스트만 추출 (네이버 뉴스 포함)
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # 네이버 뉴스 본문 (기사마다 클래스명이 다르지만 articleBodyContents가 대부분)
    candidates = [
        "#newsct_article",               # 최근 네이버 뉴스 본문 영역 id
        ".go_trans._article_content",    # 이전 버전 클래스명
        ".article_body",                 # 일부 언론사 클래스명
        "article",                       # 일반 article 태그
        "p"                              # fallback
    ]

    text = ""
    for selector in candidates:
        selected = soup.select(selector)
        if selected:
            paragraphs = [s.get_text(" ", strip=True) for s in selected]
            text = "\n".join(paragraphs)
            break

    if not text:  # 아무것도 못 찾으면 전체 텍스트 fallback
        text = soup.get_text(" ", strip=True)

    # 너무 길면 앞부분만
    return text[:4000]



def summarize_text(article_text: str) -> str:
    """
    기사 내용을 GPT로 요약
    """
    prompt = f"""
다음 텍스트를 읽고
서론, 본론, 결론 구조로 요약해줘.
각 항목은 40자 이내로 작성하고
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
