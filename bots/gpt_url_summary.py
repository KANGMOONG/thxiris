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

# 트위터 Bearer Token
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
                return url
        # Naver bridge 처리
        if "link.naver.com/bridge" in final_url:
            qs = parse_qs(urlparse(final_url).query)
            if "url" in qs:
                decoded = unquote(qs["url"][0])
                return decoded
        # 의심스러운 도메인 변경
        original_domain = urlparse(url).netloc
        final_domain = urlparse(final_url).netloc
        if original_domain != final_domain and not any(short in original_domain for short in ['bit.ly', 'tinyurl', 'naver.me', 't.co']):
            return url
        return final_url
    except Exception as e:
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
        if not resp.ok or "text/html" not in resp.headers.get("Content-Type", ""):
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        title = ""
        for selector in ['h1','.article-title','.news-title','.post-title','title']:
            elem = soup.select_one(selector)
            if elem and elem.get_text().strip():
                title = elem.get_text().strip()
                break
        if not title and soup.title:
            title = soup.title.get_text().strip()
        body_text = ""
        for selector in ['article','.article-content','.article-body','.news-content','.post-content','.content','#article-view-content-div','.view-content','.article_txt','.news_txt']:
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
        return {"title": title, "body": body_text[:4000]}
    except:
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
        driver.get(url)
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        title = driver.title.strip()
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
                        break
            except:
                continue
        if not body_text or len(body_text) < 100:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for unwanted in soup.find_all(['script','style','nav','header','footer','aside']):
                unwanted.decompose()
            body_text = soup.get_text(separator='\n')
            lines = [line.strip() for line in body_text.split('\n') if line.strip() and len(line.strip())>10]
            body_text = '\n'.join(lines)
    except:
        pass
    finally:
        driver.quit()
    return {"title": title, "body": body_text[:4000]}

# -------------------------------
# 트위터 본문 추출
# -------------------------------
def fetch_twitter_content(url: str) -> dict | None:
    try:
        match = re.search(r"(?:twitter|x)\.com/[^/]+/status/(\d+)", url)
        if not match: return None
        tweet_id = match.group(1)
        if not TWITTER_BEARER_TOKEN: return None
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}","User-Agent":"v2TweetLookupPython"}
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}?expansions=author_id&tweet.fields=created_at,lang&user.fields=username,name"
        resp = requests.get(api_url, headers=headers, timeout=5)
        if not resp.ok: return None
        data = resp.json()
        tweet_data = data.get("data","")
        includes = data.get("includes","")
        text = tweet_data.get("text","")
        created_at = tweet_data.get("created_at","")
        author = ""
        if "users" in includes:
            user = includes["users"][0]
            author = f"{user.get('name')} (@{user.get('username')})"
        title = f"트위터 글 by {author} ({created_at})"
        return {"title": title, "body": text.strip()}
    except:
        return None

# -------------------------------
# 기사/웹 페이지 내용 가져오기
# -------------------------------
def fetch_article_content(url: str) -> dict:
    if "twitter.com" in url or "x.com" in url:
        tw = fetch_twitter_content(url)
        if tw: return tw
    original_url = url
    if "blog.naver.com" in url and not url.startswith("https://m."):
        url = url.replace("https://blog.naver.com","https://m.blog.naver.com")
    article = try_requests_first(url)
    if article and article["body"] and len(article["body"]) > 100: return article
    if url != original_url:
        article = try_requests_first(original_url)
        if article and article["body"] and len(article["body"]) > 100: return article
    return fetch_with_selenium(original_url)

# -------------------------------
# GPT 요약
# -------------------------------
def summarize_text(article: dict) -> str:
    title = article.get("title","")
    body = article.get("body","")
    if not body or len(body.strip())<50:
        return "- 본문 추출 실패"
    prompt = f"""
제목과 본문을 보고
기사 내용을 핵심만 요약해줘.
누가 뭘 어떻게 했는지, 장소와 주체, 대상 구체적으로 말해줘야
내용의 혼동이 없음.
기승전결이면 더 좋고, 정확하게 요약해줘.

- 각 항목은 30자 이내, 음슴체
- 출력은 '✅ 요약'을 제일 첫줄로 시작하고, 그 아래로 총 6줄로 각 열 시작마다 '-'를 붙여주고 자연스럽고 깔끔하게 요약
- 각 열 끝에 공백 없게

제목:
\"\"\"{title}\"\"\" 

본문:
\"\"\"{body}\"\"\" 
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_completion_tokens=300
        )
        return response.choices[0].message.content.strip()
    except:
        return f"✅ 요약\n- 제목: {title[:30]}\n- 본문 길이: {len(body)}글자\n- GPT 요약 실패\n- 직접 확인 필요\n- \n- "

# -------------------------------
# 메시지에서 URL 찾아 요약
# -------------------------------
def url_summary(chat) -> str | None:
    # ChatContext나 문자열 대응
    if isinstance(chat,str):
        msg = chat
    else:
        msg = getattr(chat,'message',None)
        if msg:
            msg = getattr(msg,'msg',None)
        if not msg:
            print("❌ 메시지 문자열 추출 실패")
            return None

    # URL 정규식 (http/https 없어도 TLD 기반 포함)
    url_pattern = re.compile(r'(https?://[^\s)]+|[^\s]+\.[a-z]{2,6}[^\s)]*)', re.IGNORECASE)
    url_match = url_pattern.search(msg)
    if url_match:
        url = url_match.group(0).rstrip(').,!?')  # 괄호나 마침표 제거
        resolved_url = resolve_redirect_url(url)
        try:
            article = fetch_article_content(resolved_url)
            summary = summarize_text(article)
            return summary
        except:
            return f"✅ 오류\n- URL 처리 실패\n- 수동 확인 필요\n- "
    return None

# -------------------------------
# 테스트용
# -------------------------------
def test_url(url: str):
    return url_summary(url)
