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
    에러 페이지나 봇 차단 감지 시 원본 URL 반환
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
        }
        
        # HEAD 요청으로 최종 URL 확인
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        final_url = resp.url

        # HEAD 실패하면 GET으로 재시도
        if resp.status_code >= 400 or final_url == url:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            final_url = resp.url

        # 🔹 에러 페이지나 봇 차단 감지
        error_indicators = [
            'error.html',
            'blocked',
            'forbidden',
            'access-denied',
            'se-cu.com/ndsoft',  # 특정 에러 페이지
            '404', '403', '500'
        ]
        
        for indicator in error_indicators:
            if indicator in final_url.lower():
                print(f"🚫 에러 페이지 감지: {final_url} → 원본 URL 사용")
                return url

        # 🔹 Naver bridge URL 처리
        if "link.naver.com/bridge" in final_url:
            qs = parse_qs(urlparse(final_url).query)
            if "url" in qs:
                decoded = unquote(qs["url"][0])
                print("🔹 Bridge URL → 실제 URL:", decoded)
                return decoded

        # 도메인이 완전히 바뀐 경우 (단축URL이 아닌 경우) 의심
        original_domain = urlparse(url).netloc
        final_domain = urlparse(final_url).netloc
        
        if original_domain != final_domain and not any(short in original_domain for short in ['bit.ly', 'tinyurl', 'naver.me', 't.co']):
            print(f"🚫 의심스러운 도메인 변경: {original_domain} → {final_domain}, 원본 URL 사용")
            return url

        return final_url
    except Exception as e:
        print(f"⚠️ 리다이렉트 URL 해석 실패: {e}")
        return url

def try_requests_first(url: str, timeout=5) -> dict | None:
    """
    requests + BeautifulSoup으로 간단한 기사 구조 빠르게 추출
    개선된 버전: 더 구체적인 본문 추출 시도
    """
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
        title_selectors = [
            'h1',
            '.article-title', 
            '.news-title',
            '.post-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                break
        
        if not title and soup.title:
            title = soup.title.get_text().strip()

        # 본문 추출 - 다양한 선택자 시도
        body_text = ""
        article_selectors = [
            'article',
            '.article-content',
            '.article-body', 
            '.news-content',
            '.post-content',
            '.content',
            '#article-view-content-div',
            '.view-content',
            '.article_txt',
            '.news_txt'
        ]
        
        for selector in article_selectors:
            article_elem = soup.select_one(selector)
            if article_elem:
                # 광고, 관련기사 등 불필요한 요소 제거
                for unwanted in article_elem.find_all(['script', 'style', 'iframe', 'ins']):
                    unwanted.decompose()
                
                # 관련기사, 광고 클래스 제거
                for unwanted_class in article_elem.find_all(class_=['ad', 'advertisement', 'related', 'recommend']):
                    unwanted_class.decompose()
                    
                body_text = article_elem.get_text(separator='\n').strip()
                if len(body_text) > 100:  # 충분한 길이의 본문이 있으면
                    break
        
        # 위 방법들로 본문을 찾지 못한 경우, 전체 페이지에서 추출
        if not body_text or len(body_text) < 100:
            # 불필요한 태그 제거
            for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                unwanted.decompose()
            
            body_text = soup.get_text(separator='\n')
        
        # 텍스트 정리
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        body_text = '\n'.join(lines)
        
        print(f"📄 추출된 제목: {title}")
        print(f"📝 본문 길이: {len(body_text)} 글자")
        print(f"🔍 본문 미리보기: {body_text[:200]}...")
        
        return {"title": title, "body": body_text[:4000]}
        
    except Exception as e:
        print(f"⚠️ requests로 본문 추출 실패: {e}")
        return None

def fetch_with_selenium(url: str, wait_time=5) -> dict:
    """
    Selenium으로 기사 본문 및 제목 추출 (개선된 버전)
    봇 차단 우회를 위한 추가 설정
    """
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
    
    # 더 현실적인 User-Agent 설정
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # 봇 감지 우회
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=options)
    
    # 봇 감지 우회 스크립트
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    title = ""
    body_text = ""

    try:
        print(f"🌐 Selenium으로 페이지 로드: {url}")
        driver.get(url)

        # 페이지 로드 대기
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 추가 대기 (동적 콘텐츠 로드)
        time.sleep(3)

        # 현재 URL 확인 (리다이렉트 감지)
        current_url = driver.current_url
        if 'error.html' in current_url or 'blocked' in current_url:
            print(f"🚫 에러 페이지로 리다이렉트됨: {current_url}")
            return {"title": "접근 차단됨", "body": "사이트에서 봇 접근을 차단하고 있습니다."}

        title = driver.title.strip()
        print(f"📄 페이지 제목: {title}")

        # 네이버 블로그 특별 처리
        if "blog.naver.com" in url:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
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
            # 일반 사이트 처리 - press9.kr 특화 선택자 추가
            article_selectors = [
                "#article-view-content-div",  # press9.kr 전용
                ".article_txt",               # press9.kr 전용
                ".news_txt",                  # press9.kr 전용  
                "article",
                ".article-content",
                ".article-body", 
                ".news-content",
                ".post-content",
                ".content",
                ".view-content",
                ".article_view",
                ".news_view"
            ]
            
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
            
            # 위 방법으로 본문을 찾지 못한 경우 - 페이지 소스 확인
            if not body_text or len(body_text) < 100:
                print("🔍 페이지 소스 분석 중...")
                page_source = driver.page_source
                
                # 페이지에 실제 기사 내용이 있는지 확인
                if len(page_source) < 1000:
                    print("⚠️ 페이지 소스가 너무 짧음 - 차단되었을 가능성")
                    return {"title": title or "차단됨", "body": "페이지 내용이 로드되지 않음"}
                
                # BeautifulSoup으로 재분석
                soup = BeautifulSoup(page_source, 'html.parser')
                for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
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

def fetch_article_content(url: str) -> dict:
    """
    requests로 먼저 시도 후 실패 시 selenium fallback
    (네이버 블로그는 모바일 URL로 자동 변환)
    봇 차단 감지 시 원본 URL로 직접 접근
    """
    original_url = url
    
    # 🔹 네이버 블로그 URL을 모바일 URL로 변환
    if "blog.naver.com" in url and not url.startswith("https://m."):
        url = url.replace("https://blog.naver.com", "https://m.blog.naver.com")

    print(f"🔍 1단계: requests로 시도 - {url}")
    article = try_requests_first(url)
    
    if article and article["body"].strip() and len(article["body"]) > 100:
        print("✅ requests로 성공적으로 추출")
        return article
    
    # requests 실패 시 원본 URL로도 시도
    if url != original_url:
        print(f"🔍 1-2단계: 원본 URL로 requests 재시도 - {original_url}")
        article = try_requests_first(original_url)
        if article and article["body"].strip() and len(article["body"]) > 100:
            print("✅ 원본 URL로 requests 성공")
            return article
    
    print("🔍 2단계: Selenium으로 재시도")
    selenium_result = fetch_with_selenium(original_url)  # 원본 URL 사용
    
    # Selenium도 실패하고 변환된 URL이 있다면 그것도 시도
    if (not selenium_result["body"] or len(selenium_result["body"]) < 100) and url != original_url:
        print("🔍 2-2단계: 변환된 URL로 Selenium 재시도")
        selenium_result = fetch_with_selenium(url)
    
    return selenium_result

def summarize_text(article: dict) -> str:
    """
    GPT로 기사 내용을 핵심 위주로 요약 (제목 포함)
    """
    title = article.get("title", "")
    body = article.get("body", "")

    if not body or len(body.strip()) < 50:
        return "- 본문 추출 실패\n- 사이트 접근 제한 가능성\n- Selenium 재시도 필요\n- "

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

def url_summary(chat) -> str | None:
    """
    텍스트에서 URL을 추출하고 기사 요약 수행
    chat: ChatContext 객체 또는 문자열
    """
    # chat이 문자열인 경우와 객체인 경우 모두 처리
    if isinstance(chat, str):
        msg = chat
    else:
        msg = chat.message.msg
    
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

            print(f"\n🔹 제목: {article.get('title', '')}")
            print("🔹 요약 결과:")
            print(summary)
            return summary
        except Exception as e:
            print(f"❌ 처리 중 오류 발생: {e}")
            return f"✅ 오류\n- URL 처리 실패\n- 오류: {str(e)[:30]}\n- 사이트 접근 제한 가능성\n- 수동 확인 필요\n- \n- "
    else:
        print("❌ 메시지에 URL이 없습니다:", msg)
        return None

# 테스트용 함수
def test_url(url: str):
    """단일 URL 테스트용 함수"""
    return url_summary(url)