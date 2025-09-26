import re
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from openai import OpenAI

# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 필요)
client = OpenAI()


def fetch_article_content(url: str, wait_time=3) -> dict:
    """
    웹페이지에서 제목과 본문 텍스트를 추출
    네이버 블로그 포함 (iframe 대응)
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # 매번 고유한 임시 user-data-dir 지정 → 세션 충돌 방지
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=options)
    title = ""
    body_text = ""

    try:
        driver.get(url)
        time.sleep(wait_time)

        # 제목 추출
        title = driver.title.strip()

        # 네이버 블로그 처리 (iframe 안으로 들어가야 함)
        if "blog.naver.com" in url:
            try:
                iframe = driver.find_element(By.ID, "mainFrame")
                driver.switch_to.frame(iframe)
                time.sleep(1)

                try:
                    article = driver.find_element(By.CLASS_NAME, "se-main-container")
                except:
                    article = driver.find_element(By.ID, "postViewArea")  # 구버전 블로그
                body_text = article.text.strip()
            except Exception as e:
                print("네이버 블로그 본문 추출 실패:", e)
        else:
            # 일반 웹사이트는 body 텍스트 추출
            body = driver.find_element(By.TAG_NAME, "body")
            body_text = body.text.strip()

    except Exception as e:
        print("본문 또는 제목 가져오기 오류:", e)
    finally:
        driver.quit()

    return {
        "title": title,
        "body": body_text[:4000]  # 최대 길이 제한
    }


def summarize_text(article: dict) -> str:
    """
    GPT로 기사 내용을 핵심 위주로 요약 (제목 포함)
    """
    title = article.get("title", "")
    body = article.get("body", "")

    if not body:
        return "- 본문 없음\n- \n- \n- "

    prompt = f"""
제목과 본문을 보고
기사 내용을 핵심만 요약해줘.
누가 뭘 어떻게 했는지 구체적으로.
기승전결이면 더 좋고, 오해 없게 요약해줘.

- 각 항목은 40자 이내, 음슴체로
- 출력은 '-' 다섯 줄

제목:
\"\"\"{title}\"\"\"

본문:
\"\"\"{body}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 필요시 gpt-4o 또는 gpt-3.5-turbo로 변경 가능
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=300
    )

    return response.choices[0].message.content.strip()


def url_summary(chat):
    """
    텍스트에서 URL을 추출하고 기사 요약 수행
    chat: 텍스트 문자열 (URL 포함)
    """
    msg=chat.message.msg
    #msg = chat
    url_pattern = re.compile(r'https?://[^\s]+')
    url_match = url_pattern.search(msg)

    if url_match:
        url = url_match.group(0)
        print("✅ 메시지에서 URL 발견:", url)
        try:
            article = fetch_article_content(url)
            summary = summarize_text(article)

            print("\n🔹 제목:", article.get("title", ""))
            print("🔹 요약 결과:")
            print(summary)
            return summary
        except Exception as e:
            print("❌ 처리 중 오류 발생:", e)
    else:
        print("❌ 메시지에 URL이 없습니다:", msg)
