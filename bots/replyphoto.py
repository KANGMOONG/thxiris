from iris import ChatContext
from iris.decorators import *

def reply_photo(chat: ChatContext, kl):
    match chat.message.command:
        case "!1단계":
            send_tiger(chat)
        case "!2단계":
            send_tiger2(chat)
        case "!3단계":
            send_tiger3(chat)
        case "!절망시리즈":
            send_triple_tiger(chat)
        case "!프사":
            send_avatar(chat)
        case "!프사링":
            send_avatar_kakaolink(chat, kl)

def send_tiger(chat: ChatContext):
    chat.reply_media("res/1step.jpeg")
def send_tiger2(chat: ChatContext):
    chat.reply_media("res/2step.jpeg")
def send_tiger3(chat: ChatContext):
    chat.reply_media("res/3step.jpeg")
def send_triple_tiger(chat: ChatContext):
    chat.reply_media([open("res/1step.jpeg", "rb"), open("res/2step.jpeg", "rb"), open("res/3step.jpeg","rb")])

@is_reply
def send_avatar(chat: ChatContext):
    avatar = chat.get_source().sender.avatar.img
    chat.reply_media(avatar)
    
@is_reply
def send_avatar_kakaolink(chat: ChatContext, kl):
    avatar = chat.get_source().sender.avatar
    kl.send(
        receiver_name=chat.room.name,
        template_id=3139,
        template_args={
            "IMAGE_WIDTH" : avatar.img.width,
            "IMAGE_HEIGHT" : avatar.img.height,
            "IMAGE_URL" : avatar.url
            },
    )


{
    "template_id": 3139,
    "template_args": {
        'ANDROID_EXECUTION_URL': '',
        'COMMENT_COUNT': '', 
        'DESCRIPTION': '', 
        'FIRST_BUTTON_ANDROID_EXECUTION_URL': '', 
        'FIRST_BUTTON_IOS_EXECUTION_URL': '', 
        'FIRST_BUTTON_MOBILE_WEB_URL': '', 
        'FIRST_BUTTON_TITLE': '', 
        'FIRST_BUTTON_WEB_URL': '', 
        'IMAGE_COUNT': '',
        'IMAGE_HEIGHT': '', 
        'IMAGE_URL': '', 
        'IMAGE_WIDTH': '', 
        'IOS_EXECUTION_URL': '', 
        'ITEM1': '', 
        'ITEM1_OP': '', 
        'ITEM2': '', 
        'ITEM2_OP': '', 
        'ITEM3': '', 
        'ITEM3_OP': '', 
        'ITEM4': '', 
        'ITEM4_OP': '', 
        'ITEM5': '', 
        'ITEM5_OP': '', 
        'ITL_AL': '', 
        'LIKE_COUNT': '', 
        'MOBILE_WEB_URL': '', 
        'PROFILE_IMAGE_URL': '', 
        'PROFILE_TEXT1': '', 
        'PROFILE_TEXT2': '', 
        'SHARED_COUNT': '', 
        'SUBSCRIBER_COUNT': '', 
        'SUM': '', 
        'SUM_OP': '', 
        'TITLE': '', 
        'TITLE_IMAGE_CATEGORY': '', 
        'TITLE_IMAGE_TEXT': '', 
        'TITLE_IMAGE_URL': '', 
        'VIEW_COUNT': '', 
        'WEB_URL': ''
    }
}
