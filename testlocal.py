# test_runner.py

# 실제 사용하는 함수 불러오기
from bots.gpt_url_summary import url_summary  # my_module.py 에 정의돼 있어야 함

def main(testinput):
    # gpt_url_summary가 return을 안 하고 print만 한다면,
    # 아래처럼 처리하거나 return 받도록 수정 필요
    testoutput = url_summary(testinput)
    print("결과:", testoutput)

if __name__ == "__main__":
    # 여기에 테스트 인풋 직접 넣기
    testinput = "https://example.com/some-article"
    main(testinput)
