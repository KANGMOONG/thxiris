from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from bots.gemini import get_gemini
from bots.pyeval import python_eval, real_eval
from bots.stock import create_stock_image
from bots.imagen import get_imagen
from bots.lyrics import get_lyrics, find_lyrics
from bots.replyphoto import reply_photo
from bots.text2image import draw_text
from bots.coin import get_coin_info

from iris.decorators import *
from helper.BanControl import ban_user, unban_user
from iris.kakaolink import IrisLink

from bots.detect_nickname_change import detect_nickname_change
import sys, threading

iris_url = sys.argv[1]
bot = Bot(iris_url)

@bot.on_event("message")
@is_not_banned
def on_message(chat: ChatContext):
    try:
        # ### 변경/추가: match 전에 command 값을 안전하게 추출/정리
        raw = getattr(chat.message, "command", None) \
              or getattr(chat.message, "text", None) \
              or getattr(chat.message, "content", None) \
              or ""                       # 안전하게 빈 문자열 기본값
        if isinstance(raw, (bytes, bytearray)):   # bytes면 디코딩
            raw = raw.decode(errors="ignore")
        cmd = str(raw).strip()                    # 문자열로 확정하고 양쪽 공백 제거
        print("DEBUG on_message cmd:", repr(cmd), type(cmd))  # ### 변경/추가: 디버그 출력

        # ### 변경/추가: match는 이제 cmd 변수로 수행
        if "불장은 불장이다" in raw:
        chat.reply("그치?")
        return
	
        match cmd:
           
            case "!hhi":
                chat.reply(f"Hello {chat.sender.name}")
                return

            case "!tt" | "!ttt" | "!프사" | "!프사링":
                reply_photo(chat, kl)
                return

            #make your own help.png or remove !iris
            case "!iris":
                chat.reply_media("res/help.png")
                return

            case "!gi" | "!i2i" | "!분석":
                get_gemini(chat)
                return

            case "!ipy":
                python_eval(chat)
                return

            case "!iev":
                real_eval(chat, kl)
                return

            case "!ban":
                ban_user(chat)
                return

            case "!unban":
                unban_user(chat)
                return

            case "!주식":
                create_stock_image(chat)
                return

            case "!ig":
                get_imagen(chat)
                return

            case "!가사찾기":
                find_lyrics(chat)
                return

            case "!노래가사":
                get_lyrics(chat)
                return

            case "!텍스트" | "!사진" | "!껄무새" | "!멈춰" | "!지워" | "!진행" | "!말대꾸" | "!텍스트추가":
                draw_text(chat)
                return

            case "!코인" | "!내코인" | "!바낸" | "!김프" | "!달러" | "!코인등록" | "!코인삭제":
                get_coin_info(chat)
                return

    except Exception as e:
        # ### 변경/추가: 전체 예외 스택을 출력하면 문제 원인 파악이 쉬워집니다
        import traceback
        traceback.print_exc()
        print("ERROR in on_message:", e)
        # 테스트 중이라면 채팅으로도 에러 알림(선택)
        # chat.reply(f"오류 발생: {e}")

#입장감지
@bot.on_event("new_member")
def on_newmem(chat: ChatContext):
    chat.reply(f"어서와라 {chat.sender.name}")
    pass

#퇴장감지
@bot.on_event("del_member")
def on_delmem(chat: ChatContext):
    chat.reply(f"잘가시고 {chat.sender.name}")
    pass


@bot.on_event("error")
def on_error(err: ErrorContext):
    print(err.event, "이벤트에서 오류가 발생했습니다", err.exception)
    #sys.stdout.flush()

if __name__ == "__main__":
    #닉네임감지를 사용하지 않는 경우 주석처리
    nickname_detect_thread = threading.Thread(target=detect_nickname_change, args=(bot.iris_url,))
    nickname_detect_thread.start()
    #카카오링크를 사용하지 않는 경우 주석처리
    kl = IrisLink(bot.iris_url)
    bot.run()
