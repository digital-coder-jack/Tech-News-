import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", 0))
NEWS_POST_HOUR = int(os.getenv("NEWS_POST_HOUR", 9))
