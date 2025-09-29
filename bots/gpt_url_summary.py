import os
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

# 🔹 트위터 Bearer Token
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# -------------------------------
# 단축 URL 처리
# -------------------------------
def resolve_redirect_url(url: str, timeout=3) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
        }
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        final_url = resp.url
        if resp.status_code >= 400 or final_url == url:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            final_url = resp.url
        # 에러 페이지 감지
        error_indicators = ['error.html','blocked','forbidden','access-denied','se-cu.com/ndsoft','404','403','500']
        for indicator in error_indicators:
            if indicator in final_url.lower():
                print(f"🚫 에러 페이지 감지: {final_url} → 원본 URL 사용")
                return url
        # Naver bridge 처리
        if "link.naver.com/bridge" in final_url:
            qs = parse_qs(urlparse(final_url).query)
            if "url" in qs:
                decoded = unquote(qs["url"][0])
                print("🔹 Bridge URL → 실제 URL:", decoded)
                return decoded
        # 의심스러운 도메인 변경
        original_domain = urlparse(url).netloc
        final_domain = urlparse(final_url).netloc
        if original_domain != final_domain and not any(short in original_domain for short in ['bit.ly', 'tinyurl', 'naver.me', 't.co']):
            print(f"🚫 의심스러운 도메인 변경: {original_domain} → {final_domain}, 원본 URL 사용")
            return url
        return final_url
    except Exception as e:
        print(f"⚠️ 리다이렉트 URL 해석 실패: {e}")
        return url

# -------------------------------
# requests + BeautifulSoup 본문 추출
# -------------------------------
def try_requests_first(url: str, timeout=5) -> dict | None:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if not resp.ok:
            print(f"⚠️ HTTP 상태 코드: {resp.status_code}")
            return None
        if "text/html" not in resp.headers.get("Content-Type", ""):
            print("⚠️ HTML 콘텐츠가 아님")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # 제목 추출
        title = ""
        title_selectors = ['h1','.article-title','.news-title','.post-title','title']
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text().strip():
                title = elem.get_text().strip()
                break
        if not title and soup.title:
            title = soup.title.get_text().strip()
        # 본문 추출
        body_text = ""
        article_selectors = ['article','.article-content','.article-body','.news-content','.post-content','.content','#article-view-content-div','.view-content','.article_txt','.news_txt']
        for selector in article_selectors:
            article_elem = soup.select_one(selector)
            if article_elem:
                for unwanted in article_elem.find_all(['script','style','iframe','ins']):
                    unwanted.decompose()
                for unwanted_class in article_elem.find_all(class_=['ad','advertisement','related','recommend']):
                    unwanted_class.decompose()
                body_text = article_elem.get_text(separator='\n').strip()
                if len(body_text) > 100:
                    break
        if not body_text or len(body_text) < 100:
            for unwanted in soup.find_all(['script','style','nav','header','footer','aside','iframe']):
                unwanted.decompose()
            body_text = soup.get_text(separator='\n')
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        body_text = '\n'.join(lines)
        print(f"📄 추출된 제목: {title}")
        print(f"📝 본문 길이: {len(body_text)} 글자")
        print(f"🔍 본문 미리보기: {body_text[:200]}...")
        return {"title": title, "body": body_text[:4000]}
    except Exception as e:
        print(f"⚠️ requests로 본문 추출 실패: {e}")
        return None

# -------------------------------
# Selenium 본문 추출
# -------------------------------
def fetch_with_selenium(url: str, wait_time=5) -> dict:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    title = ""
    body_text = ""
    try:
        print(f"🌐 Selenium으로 페이지 로드: {url}")
        driver.get(url)
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        current_url = driver.current_url
        if 'error.html' in current_url or 'blocked' in current_url:
            print(f"🚫 에러 페이지로 리다이렉트됨: {current_url}")
            return {"title": "접근 차단됨", "body": "사이트에서 봇 접근을 차단하고 있습니다."}
        title = driver.title.strip()
        print(f"📄 페이지 제목: {title}")
        # 네이버 블로그
        if "blog.naver.com" in url:
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "mainFrame")))
                iframe = driver.find_element(By.ID, "mainFrame")
                driver.switch_to.frame(iframe)
                time.sleep(1)
                try:
                    article = driver.find_element(By.CLASS_NAME, "se-main-container")
                except:
                    article = driver.find_element(By.ID, "postViewArea")
                body_text = article.text.strip()
                print(f"📝 네이버 블로그 본문 길이: {len(body_text)}")
            except Exception as e:
                print(f"⚠️ 네이버 블로그 iframe 추출 실패: {e}")
        else:
            article_selectors = ["#article-view-content-div",".article_txt",".news_txt","article",".article-content",".article-body",".news-content",".post-content",".content",".view-content",".article_view",".news_view"]
            for selector in article_selectors:
                try:
                    if selector.startswith('.'):
                        elements = driver.find_elements(By.CLASS_NAME, selector[1:])
                    elif selector.startswith('#'):
                        elements = driver.find_elements(By.ID, selector[1:])
                    else:
                        elements = driver.find_elements(By.TAG_NAME, selector)
                    if elements:
                        body_text = elements[0].text.strip()
                        if len(body_text) > 100:
                            print(f"📝 선택자 '{selector}'로 본문 추출 성공: {len(body_text)}글자")
                            break
                except:
                    continue
            if not body_text or len(body_text) < 100:
                print("🔍 페이지 소스 분석 중...")
                page_source = driver.page_source
                if len(page_source) < 1000:
                    print("⚠️ 페이지 소스가 너무 짧음 - 차단 가능성")
                    return {"title": title or "차단됨", "body": "페이지 내용이 로드되지 않음"}
                soup = BeautifulSoup(page_source, 'html.parser')
                for unwanted in soup.find_all(['script','style','nav','header','footer','aside']):
                    unwanted.decompose()
                body_text = soup.get_text(separator='\n')
                lines = [line.strip() for line in body_text.split('\n') if line.strip() and len(line.strip()) > 10]
                body_text = '\n'.join(lines)
                print(f"📝 전체 페이지에서 추출: {len(body_text)}글자")
    except Exception as e:
        print(f"❌ Selenium 본문 추출 오류: {e}")
    finally:
        driver.quit()
    return {"title": title, "body": body_text[:4000]}

# -------------------------------
# 트위터 본문 추출
# -------------------------------
def fetch_twitter_content(url: str) -> dict | None:
    try:
        match = re.search(r"(?:twitter|x)\.com/[^/]+/status/(\d+)", url)
        if not match:
            print("⚠️ 트위터 URL에서 tweet_id 추출 실패")
            return None
        tweet_id = match.group(1)
        if not TWITTER_BEARER_TOKEN:
            print("⚠️ TWITTER_BEARER_TOKEN 환경변수 없음")
            return None
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}","User-Agent":"v2TweetLookupPython"}
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}?expansions=author_id&tweet.fields=created_at,lang&user.fields=username,name"
        resp = requests.get(api_url, headers=headers, timeout=5)
        if not resp.ok:
            print(f"⚠️ 트위터 API 오류: {resp.status_code} {resp.text}")
            return None
        data = resp.json()
        tweet_data = data.get("data", {})
        includes = data.get("includes", {})
        text = tweet_data.get("text", "")
        created_at = tweet_data.get("created_at", "")
        author = ""
        if "users" in includes:
            user = includes["users"][0]
            author = f"{user.get('name')} (@{user.get('username')})"
        title = f"트위터 글 by {author} ({created_at})"
        body = text.strip()
        print(f"🐦 트위터 본문 추출 성공: {len(body)}자")
        return {"title": title, "body": body}
    except Exception as e:
        print(f"❌ 트위터 본문 추출 실패: {e}")
        return None

# -------------------------------
# 기사/웹 페이지 내용 가져오기
# -------------------------------
def fetch_article_content(url: str) -> dict:
    # 트위터 URL 우선 처리
    if "twitter.com" in url or "x.com" in url:
        tw = fetch_twitter_content(url)
        if tw:
            return tw
    original_url = url
    if "blog.naver.com" in url and not url.startswith("https://m."):
        url = url.replace("https://blog.naver.com","https://m.blog.naver.com")
    print(f"🔍 1단계: requests로 시도 - {url}")
    article = try_requests_first(url)
    if article and article["body"].strip() and len(article["body"]) > 100:
        print("✅ requests로 성공적으로 추출")
        return article
    if url != original_url:
        print(f"🔍 1-2단계: 원본 URL로 requests 재시도 - {original_url}")
        article = try_requests_first(original_url)
        if article and article["body"].strip() and len(article["body"]) > 100:
            print("✅ 원본 URL로 requests 성공")
            return article
    print("🔍 2단계: Selenium으로 재시도")
    selenium_result = fetch_with_selenium(original_url)
    if (not selenium_result["body"] or len(selenium_result["body"]) < 100) and url != original_url:
        print("🔍 2-2단계: 변환된 URL로 Selenium 재시도")
        selenium_result = fetch_with_selenium(url)
    return selenium_result

# -------------------------------
# GPT 요약
# -------------------------------
def summarize_text(article: dict) -> str:
    title = article.get("title","")
    body = article.get("body","")
    if not body or len(body.strip()) < 50:
        return "- 본문 추출 실패\n- 사이트 접근 제한 가능성\n- Selenium 재시도 필요\n- "
    prompt = f"""
제목과 본문을 보고
기사 내용을 핵심만 요약해줘.
누가 뭘 어떻게 했는지, 장소와 주체, 대상 구체적으로 말해줘야
내용의 혼동이 없음.
기승전결이면 더 좋고, 정확하게 요약해줘.

- 각 항목은 28자 이내, 음슴체
- 출력은 '✅ 요약'을 제일 첫줄로 시작하고, 그 아래로 총 6줄로 각 열 시작마다 '-'를 붙여주고 자연스럽고 깔끔하게 요약

제목:
\"\"\"{title}\"\"\"

본문:
\"\"\"{body}\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ GPT 요약 실패: {e}")
        return f"✅ 요약\n- 제목: {title[:30]}\n- 본문 길이: {len(body)}글자\n- GPT 요약 실패\n- 직접 확인 필요\n- \n- "

# -------------------------------
# 메시지에서 URL 찾아 요약
# -------------------------------
def url_summary(chat) -> str | None:
    if isinstance(chat,str):
        msg = chat
    else:
        msg = chat.message.msg
    url_pattern = re.compile(r'https?://[^\s]+')
    url_match = url_pattern.search(msg)
    if url_match:
        url = url_match.group(0)
        print("✅ 메시지에서 URL 발견:", url)
        resolved_url = resolve_redirect_url(url)
        print("🔹 실제 URL:", resolved_url)
        try:
            article = fetch_article_content(resolved_url)
            summary = summarize_text(article)
            print(f"\n🔹 제목: {article.get('title','')}")
            print("🔹 요약 결과:")
            print(summary)
            return summary
        except Exception as e:
            print(f"❌ 처리 중 오류 발생: {e}")
            return f"✅ 오류\n- URL 처리 실패\n- 오류: {str(e)[:30]}\n- 사이트 접근 제한 가능성\n- 수동 확인 필요\n- \n- "
    else:
        print("❌ 메시지에 URL이 없습니다:", msg)
        return None

# -------------------------------
# 테스트용
# -------------------------------
def test_url(url: str):
    return url_summary(url)
