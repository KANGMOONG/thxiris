from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import requests
from iris.decorators import *
from iris import ChatContext
import os, io
import time

pro_key = os.getenv("AIzaSyBbpYQFROJvzQnRxXmAkbe_1gjJpOR1R2w")


safety_settings=[
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_ONLY_HIGH",  # Block few
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_CIVIC_INTEGRITY",
        threshold="BLOCK_NONE",  # Block none
    ),
]

def get_img(chat: ChatContext):
    print(f"hello")