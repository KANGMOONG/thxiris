from iris import ChatContext
from iris.decorators import *
import re  # 정규식 모듈

def excel(chat: ChatContext):
    msg = chat.message.msg  # 메시지 꺼내기

    # URL 패턴 (http, https, ftp, www, 도메인 등 전부 감지)
    url_pattern = re.compile(
        r'''(?xi)
        \b(                             # 단어 경계
            (?:[a-z][a-z0-9-]{0,61}[a-z0-9]\.)+[a-z]{2,}  # 도메인
            (?:[/?#][^\s]*)?             # 경로/쿼리 있을 수도 있음
        )\b
        '''
    )

    if url_pattern.search(msg):
        print("메시지가 URL입니다.")
        # URL일 때 실행할 코드
    else:
        print("메시지가 URL이 아닙니다.")
        # URL이 아닐 때 실행할 코드
