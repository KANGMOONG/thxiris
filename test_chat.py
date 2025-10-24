from iris import ChatContext, Bot
import sys
from iris.bot.models import ErrorContext

iris_url = sys.argv[1]
bot = Bot(iris_url)

@bot.on_event("message")
@is_not_banned
def on_message(chat: ChatContext):
    print(chat.message.msg)