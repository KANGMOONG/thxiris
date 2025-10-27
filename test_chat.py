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
    if chat.raw.get("user_id") == '7604855274274687031':
        chat.reply(chat.message.msg)
    print(chat.sender.name+' '+chat.message.msg)

if __name__ == "__main__":
    bot.run()
