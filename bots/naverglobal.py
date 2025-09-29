from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import time

def capture_naver_tsla_chart(output_file="tsla_chart_canvas.png"):
    url = "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=테슬라&ackey=so6hik7m"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1400,900")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        time.sleep(3)  # JS 렌더링 대기

        # Canvas 요소 모두 가져오기
        canvases = driver.find_elements(By.TAG_NAME, "canvas")
        if not canvases:
            raise ValueError("페이지 내 Canvas 요소를 찾을 수 없습니다.")

        # width=1260, height=400 Canvas 선택
        chart_canvas = None
        for c in canvases:
            if int(c.get_attribute("width")) == 1260 and int(c.get_attribute("height")) == 400:
                chart_canvas = c
                break
        
        if chart_canvas is None:
            raise ValueError("주식 차트 Canvas를 찾을 수 없습니다.")

        # 캡처 후 저장
        chart_png = chart_canvas.screenshot_as_png
        image = Image.open(io.BytesIO(chart_png))
        image.save(output_file)
        print(f"차트 캡처 완료: {output_file}")
    
    finally:
        driver.quit()

# 사용 예시
if __name__ == "__main__":
    capture_naver_tsla_chart()
