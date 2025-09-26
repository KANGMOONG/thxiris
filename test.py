import time
from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from iris.decorators import *
from helper.BanControl import ban_user, unban_user
from iris.kakaolink import IrisLink
from bots.check_test import checktest
from bots.gpt_url_summary import url_summary




from bots.detect_nickname_change import detect_nickname_change
import sys, threading, re



iris_url = sys.argv[1]
bot = Bot(iris_url)

@bot.on_event("message")
@is_not_banned
def on_message(chat: ChatContext):
    url=None
    if chat.raw.get('chat_id') in ['446920784776967', '278674834031691']:  #
        printsummary=url_summary(chat)
        if printsummary:  # None이나 빈 문자열이 아니면
         chat.reply(printsummary)
        else:
         print("❌ 일상메세지")
        

if __name__ == "__main__":
    #닉네임감지를 사용하지 않는 경우 주석처리
    nickname_detect_thread = threading.Thread(target=detect_nickname_change, args=(bot.iris_url,))
    nickname_detect_thread.start()
    #카카오링크를 사용하지 않는 경우 주석처리
    kl = IrisLink(bot.iris_url)
    bot.run()
