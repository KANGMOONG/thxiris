import re
import time
import tempfile
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs, unquote
from openai import OpenAI

# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 필요)
client = OpenAI()

def resolve_redirect_url(url: str, timeout=3) -> str:
    """
    단축 URL(naver.me 등)을 실제 URL로 변환
    (link.naver.com/bridge 처리 포함)
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # HEAD 요청으로 최종 URL 확인
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        final_url = resp.url

        # HEAD 실패하면 GET으로 재시도
        if resp.status_code >= 400 or final_url == url:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            final_url = resp.url

        # 🔹 Naver bridge URL 처리
        if "link.naver.com/bridge" in final_url:
            qs = parse_qs(urlparse(final_url).query)
            if "url" in qs:
                decoded = unquote(qs["url"][0])
                print("🔹 Bridge URL → 실제 URL:", decoded)
                return decoded

        return final_url
    except Exception as e:
        print("⚠️ 리다이렉트 URL 해석 실패:", e)
        return url

def try_requests_first(url: str, timeout=3) -> dict | None:
    """
    requests + BeautifulSoup으로 간단한 기사 구조 빠르게 추출
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if not resp.ok or "text/html" not in resp.headers.get("Content-Type", ""):
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.text.strip() if soup.title else ""
        body = soup.get_text(separator="\n")
        return {"title": title, "body": body[:4000]}
    except Exception as e:
        print("⚠️ requests로 본문 추출 실패:", e)
        return None

def fetch_with_selenium(url: str, wait_time=3) -> dict:
    """
    Selenium으로 기사 본문 및 제목 추출 (네이버 블로그 포함)
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")

    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=options)

    # 리소스 차단
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.css", "*.woff", "*.ttf", "*.svg"]
    })

    title = ""
    body_text = ""

    try:
        driver.get(url)

        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        title = driver.title.strip()

        if "blog.naver.com" in url:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                iframe = driver.find_element(By.ID, "mainFrame")
                driver.switch_to.frame(iframe)
                time.sleep(0.5)

                try:
                    article = driver.find_element(By.CLASS_NAME, "se-main-container")
                except:
                    article = driver.find_element(By.ID, "postViewArea")
                body_text = article.text.strip()
            except Exception as e:
                print("⚠️ 네이버 블로그 iframe 추출 실패:", e)
        else:
            body = driver.find_element(By.TAG_NAME, "body")
            body_text = body.text.strip()

    except Exception as e:
        print("❌ Selenium 본문 추출 오류:", e)
    finally:
        driver.quit()

    return {"title": title, "body": body_text[:4000]}

def fetch_article_content(url: str) -> dict:
    """
    requests로 먼저 시도 후 실패 시 selenium fallback
    (네이버 블로그는 모바일 URL로 자동 변환)
    """
    # 🔹 네이버 블로그 URL을 모바일 URL로 변환
    if "blog.naver.com" in url and not url.startswith("https://m."):
        url = url.replace("https://blog.naver.com", "https://m.blog.naver.com")

    article = try_requests_first(url)
    if article and article["body"].strip():
        return article
    return fetch_with_selenium(url)

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
누가 뭘 어떻게 했는지, 장소와 주체, 대상 구체적으로 말해줘야
내용의 혼동이 없음.
기승전결이면 더 좋고, 정확하게 요약해줘.

- 각 항목은 30자 이내, 음슴체로
- 출력은 '✅ 요약'을 제일 첫줄로 시작하고, 그 아래로 '-' 6줄로 깔끔하게 요약

제목:
\"\"\"{title}\"\"\"

본문:
\"\"\"{body}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=300
    )

    return response.choices[0].message.content.strip()

def url_summary(chat) -> str | None:
    """
    텍스트에서 URL을 추출하고 기사 요약 수행
    chat: ChatContext 객체
    """
    #msg = chat.message.msg
    msg=chat
    url_pattern = re.compile(r'https?://[^\s]+')
    url_match = url_pattern.search(msg)

    if url_match:
        url = url_match.group(0)
        print("✅ 메시지에서 URL 발견:", url)

        # 🔹 단축 URL(리다이렉트) 풀기 + 브리지 URL 처리
        resolved_url = resolve_redirect_url(url)
        print("🔹 실제 URL:", resolved_url)

        try:
            article = fetch_article_content(resolved_url)
            summary = summarize_text(article)

            print("\n🔹 제목:", article.get("title", ""))
            print("🔹 요약 결과:")
            print(summary)
            return summary
        except Exception as e:
            print("❌ 처리 중 오류 발생:", e)
            return None
    else:
        print("❌ 메시지에 URL이 없습니다:", msg)
        return None
