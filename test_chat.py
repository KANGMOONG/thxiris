import time
import sys
from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from iris.decorators import *
from iris.kakaolink import IrisLink

iris_url = sys.argv[1]
bot = Bot(iris_url)

@bot.on_event("message")
def on_message(chat: ChatContext):
    print(chat.message.msg)

if __name__ == "__main__":
    bot.run()
