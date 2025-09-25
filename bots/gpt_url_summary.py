import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from openai import OpenAI

# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 필요)
client = OpenAI()

def fetch_article_text(url: str, wait_time=3) -> str:
    """
    Selenium으로 URL 접속 후 본문 텍스트 추출
    모든 URL에 대해 최대한 안정적으로 본문 가져오기
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    # user-data-dir 제거 → 기존 세션 충돌 방지

    driver = webdriver.Chrome(options=options)
    text = ""
    try:
        driver.get(url)
        time.sleep(wait_time)  # 페이지 로드 대기

        # 전체 body 텍스트 가져오기
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text

    except Exception as e:
        print("본문 가져오기 오류:", e)
    finally:
        driver.quit()

    return text[:4000]  # 너무 길면 앞부분만

def summarize_text(article_text: str) -> str:
    """
    GPT로 기사 내용을 서론/본론/결론 구조로 요약
    """
    if not article_text:
        return "- 본문 없음\n- \n- "

    prompt = f"""
다음 텍스트를 읽고
핵심위주로 요약해줘.
각 항목은 40자 이내로 작성하고
출력은 '-' 네 줄만 나오게 해줘:

-
-
-
-

텍스트:
\"\"\"{article_text}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=200
    )

    return response.choices[0].message.content.strip()

def url_summary(chat):
    """
    ChatContext에서 URL 감지 → 본문 추출 → GPT 요약
    """
    msg = chat.message.msg
    url_pattern = re.compile(r'https?://[^\s]+')
    url_match = url_pattern.search(msg)

    if url_match:
        url = url_match.group(0)
        print("메시지가 URL입니다.", url)
        try:
            article_text = fetch_article_text(url)
            summary = summarize_text(article_text)
            print(summary)
        except Exception as e:
            print("오류 발생:", e)
    else:
        print("메시지가 URL이 아닙니다.", msg)
