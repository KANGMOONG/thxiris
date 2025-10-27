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
#from bots.test_img import get_img
from bots.kospidaq import kospidaq
from bots.nasdaq import nasdaq
from bots.ThreeIdoit import Threeidiots
from bots.ThreeIdoit import wldadel
from bots.favoritecoin import favorite_coin_info
from bots.stock import create_gold_image

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
    #print(chat.raw.get(user_id))
    #if chat.user_id == '6677876040401202432':
    #    chat.reply(chat.message.msg)
    
    try:
        match chat.message.command:
            case "!병림픽" :
                Threeidiots(chat)
            
            case "!개" :
                wldadel(chat)

            case "!증시":
                kospidaq(chat)
            
            case "!미":
                nasdaq(chat)

            case "!hhi":
                chat.reply(f"Hello {chat.sender.name}")

            case "!1단계" | "!2단계" | "!3단계" | "!절망시리즈" | "!퍽":
                reply_photo(chat, kl)

            case "!gi" | "!i2i" | "!분석":
                get_gemini(chat)
            
            case "!ipy":
                python_eval(chat)
            
            case "!iev":
                real_eval(chat, kl)
            
            case "!ban":
                ban_user(chat)
            
            case "!unban":
                unban_user(chat)

            case "!주식":
                create_stock_image(chat)

            case "!금" :
                create_gold_image(chat)
            
            case "!코인" | "!바낸" | "!김프" | "!달러" :
                get_coin_info(chat)

            case "!즐찾등록" | "!즐찾삭제" | "!즐":
                favorite_coin_info(chat)

            
    except Exception as e :
        print(e)

#입장감지
@bot.on_event("new_member")
def on_newmem(chat: ChatContext):
    print(chat.room.id)
    if str(chat.room.id) =='18437327656490923' :   # 18437327656490923
        chat.reply(f"어서와라 {chat.sender.name}")
        chat.reply_media("res/welcome2.jpeg")
    else :
        chat.reply(f"어서와라 {chat.sender.name}")
        chat.reply_media("res/welcome.jpeg")

#퇴장감지
@bot.on_event("del_member")
def on_delmem(chat: ChatContext):
    chat.reply(f"잘가시고 {chat.sender.name}")


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
