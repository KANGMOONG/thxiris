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
import shutil
import os

# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 필요)
client = OpenAI()

def resolve_redirect_url(url: str, timeout=10) -> str:
    """
    단축 URL(naver.me 등)을 실제 URL로 변환
    (link.naver.com/bridge 처리 포함)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 세션 사용으로 쿠키 유지
        session = requests.Session()
        session.headers.update(headers)
        
        # HEAD 요청으로 최종 URL 확인
        resp = session.head(url, timeout=timeout, allow_redirects=True)
        final_url = resp.url

        # HEAD 실패하면 GET으로 재시도
        if resp.status_code >= 400 or final_url == url:
            resp = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            final_url = resp.url
            resp.close()  # 스트림 닫기

        # 🔹 Naver bridge URL 처리
        if "link.naver.com/bridge" in final_url:
            qs = parse_qs(urlparse(final_url).query)
            if "url" in qs:
                decoded = unquote(qs["url"][0])
                print("🔹 Bridge URL → 실제 URL:", decoded)
                return decoded

        return final_url
    except requests.exceptions.Timeout:
        print("⚠️ 리다이렉트 URL 해석 시간초과")
        return url
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 리다이렉트 URL 해석 실패: {e}")
        return url
    except Exception as e:
        print(f"⚠️ 예상치 못한 오류: {e}")
        return url

def try_requests_first(url: str, timeout=10) -> dict | None:
    """
    requests + BeautifulSoup으로 간단한 기사 구조 빠르게 추출
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()  # HTTP 오류 발생시 예외 발생
        
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            print(f"⚠️ HTML이 아닌 콘텐츠 타입: {content_type}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 메타 태그에서 제목 우선 추출 시도
        title = ""
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            title = meta_title["content"].strip()
        elif soup.title:
            title = soup.title.text.strip()
        
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        body = soup.get_text(separator="\n", strip=True)
        
        # 빈 줄 정리
        body = re.sub(r'\n\s*\n', '\n', body)
        
        return {"title": title, "body": body[:4000]}
        
    except requests.exceptions.Timeout:
        print("⚠️ requests 요청 시간초과")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ requests로 본문 추출 실패: {e}")
        return None
    except Exception as e:
        print(f"⚠️ 예상치 못한 오류: {e}")
        return None

def fetch_with_selenium(url: str, wait_time=10) -> dict:
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
    options.add_argument("--disable-logging")
    options.add_argument("--disable-web-security")
    options.add_argument("--window-size=1920,1080")

    temp_dir = None
    driver = None

    try:
        temp_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={temp_dir}")

        driver = webdriver.Chrome(options=options)
        
        # 페이지 로딩 타임아웃 설정
        driver.set_page_load_timeout(wait_time)
        
        # 리소스 차단으로 속도 향상
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setBlockedURLs', {
            "urls": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.css", "*.woff", "*.ttf", "*.svg", "*.ico"]
        })

        title = ""
        body_text = ""

        driver.get(url)

        # DOM 로딩 대기
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        title = driver.title.strip()

        # 네이버 블로그 특별 처리
        if "blog.naver.com" in url:
            try:
                # iframe 대기 및 전환
                iframe_locator = (By.ID, "mainFrame")
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(iframe_locator)
                )
                iframe = driver.find_element(*iframe_locator)
                driver.switch_to.frame(iframe)
                
                # 콘텐츠 로딩 대기
                time.sleep(1)

                # 다양한 셀렉터 시도
                selectors = [
                    (By.CLASS_NAME, "se-main-container"),
                    (By.ID, "postViewArea"),
                    (By.CLASS_NAME, "post-view"),
                    (By.CLASS_NAME, "post_ct")
                ]
                
                article = None
                for selector in selectors:
                    try:
                        article = driver.find_element(*selector)
                        break
                    except:
                        continue
                
                if article:
                    body_text = article.text.strip()
                else:
                    # 전체 body에서 추출
                    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                    
            except Exception as e:
                print(f"⚠️ 네이버 블로그 iframe 추출 실패: {e}")
                # 기본 body 추출로 fallback
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                except:
                    pass
        else:
            # 일반 사이트 처리
            try:
                # article 태그가 있으면 우선 사용
                article = driver.find_element(By.TAG_NAME, "article")
                body_text = article.text.strip()
            except:
                # article 태그가 없으면 body 전체 사용
                body = driver.find_element(By.TAG_NAME, "body")
                body_text = body.text.strip()

    except Exception as e:
        print(f"❌ Selenium 본문 추출 오류: {e}")
    finally:
        if driver:
            driver.quit()
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    return {"title": title, "body": body_text[:4000]}

def fetch_article_content(url: str) -> dict:
    """
    requests로 먼저 시도 후 실패 시 selenium fallback
    (네이버 블로그는 모바일 URL로 자동 변환)
    """
    print(f"🔍 기사 내용 추출 시작: {url}")
    
    # 🔹 네이버 블로그 URL을 모바일 URL로 변환
    original_url = url
    if "blog.naver.com" in url and not url.startswith("https://m."):
        url = url.replace("https://blog.naver.com", "https://m.blog.naver.com")
        print(f"🔄 모바일 URL로 변환: {url}")

    # requests 먼저 시도
    print("🚀 requests로 시도 중...")
    article = try_requests_first(url)
    
    if article and article["body"] and len(article["body"].strip()) > 100:
        print("✅ requests로 성공적으로 추출")
        return article
    
    # requests 실패시 selenium 사용
    print("🔄 Selenium으로 재시도...")
    result = fetch_with_selenium(original_url)  # 원본 URL 사용
    
    if result and result["body"]:
        print("✅ Selenium으로 성공적으로 추출")
    else:
        print("❌ 모든 방법 실패")
    
    return result

def summarize_text(article: dict) -> str:
    """
    GPT로 기사 내용을 핵심 위주로 요약 (제목 포함)
    """
    title = article.get("title", "")
    body = article.get("body", "")

    if not body or len(body.strip()) < 50:
        return "✅ 요약\n- 본문이 너무 짧거나 없음\n- 내용을 추출할 수 없음\n- 다른 방법으로 접근 필요\n- \n- \n- "

    # 본문이 너무 길면 앞부분만 사용
    if len(body) > 3000:
        body = body[:3000] + "..."

    prompt = f"""
다음 제목과 본문을 보고 기사 내용을 핵심만 요약해주세요.

요구사항:
- 누가, 무엇을, 언제, 어디서, 왜, 어떻게 했는지 구체적으로
- 각 항목은 30자 이내로 간결하게
- 음슴체 사용 (예: "~함", "~임")
- 정확한 사실만 포함

출력 형식:
✅ 요약
- (첫 번째 핵심 내용)
- (두 번째 핵심 내용)
- (세 번째 핵심 내용)
- (네 번째 핵심 내용)
- (다섯 번째 핵심 내용)
- (여섯 번째 핵심 내용)

제목: "{title}"

본문: "{body}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=400,
            temperature=0.3  # 일관성 있는 요약을 위해 낮은 온도 설정
        )

        summary = response.choices[0].message.content.strip()
        
        # 형식 검증
        if not summary.startswith("✅ 요약"):
            summary = "✅ 요약\n" + summary
            
        return summary
        
    except Exception as e:
        print(f"❌ GPT 요약 생성 실패: {e}")
        return f"✅ 요약\n- 요약 생성 중 오류 발생\n- 제목: {title[:30]}\n- 내용 길이: {len(body)}자\n- 수동 확인 필요\n- \n- "

def url_summary(chat) -> str | None:
    """
    텍스트에서 URL을 추출하고 기사 요약 수행
    chat: ChatContext 객체 또는 문자열
    """
    # chat 객체 처리
    if hasattr(chat, 'message') and hasattr(chat.message, 'msg'):
        msg = chat.message.msg
    elif isinstance(chat, str):
        msg = chat
    else:
        print("❌ 잘못된 chat 객체 형식")
        return None
    
    # URL 패턴 개선 (더 정확한 매칭)
    url_pattern = re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        re.IGNORECASE
    )
    url_match = url_pattern.search(msg)

    if not url_match:
        print("❌ 메시지에 URL이 없습니다:", msg)
        return None

    url = url_match.group(0).rstrip('.,;!?)')  # 문장부호 제거
    print("✅ 메시지에서 URL 발견:", url)

    try:
        # 🔹 단축 URL(리다이렉트) 풀기 + 브리지 URL 처리
        resolved_url = resolve_redirect_url(url)
        print("🔹 최종 URL:", resolved_url)

        # 기사 내용 추출
        article = fetch_article_content(resolved_url)
        
        if not article or not article.get("body"):
            print("❌ 기사 내용을 추출할 수 없습니다")
            return "✅ 요약\n- 기사 내용 추출 실패\n- 사이트 접근 불가능\n- 수동으로 확인 필요\n- \n- \n- "

        # GPT로 요약 생성
        summary = summarize_text(article)

        print(f"\n🔹 제목: {article.get('title', 'N/A')}")
        print(f"🔹 본문 길이: {len(article.get('body', ''))}자")
        print("🔹 요약 결과:")
        print(summary)
        
        return summary

    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        return f"✅ 요약\n- 처리 중 오류 발생: {str(e)[:30]}\n- 네트워크 문제 가능성\n- 잠시 후 재시도 권장\n- \n- \n- "

# 테스트용 함수
def test_url_summary(test_url: str):
    """
    테스트용 함수
    """
    print(f"🧪 테스트 URL: {test_url}")
    result = url_summary(test_url)
    print("=" * 50)
    print(result)
    return result