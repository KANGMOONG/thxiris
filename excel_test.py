import time
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
from bots.test_img import get_img

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
        match chat.message.command:
            
            case "!hhi":
                chat.reply(f"Hello {chat.sender.name}")

    except Exception as e :
        print(e)


if __name__ == "__main__":
    #닉네임감지를 사용하지 않는 경우 주석처리
    nickname_detect_thread = threading.Thread(target=detect_nickname_change, args=(bot.iris_url,))
    nickname_detect_thread.start()
    #카카오링크를 사용하지 않는 경우 주석처리
    kl = IrisLink(bot.iris_url)
    bot.run()
