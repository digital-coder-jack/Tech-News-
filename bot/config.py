import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# The Discord channel ID where daily news will be posted
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", 0))

# Hour (UTC) to post daily news, e.g. 9 = 9:00 AM UTC
NEWS_POST_HOUR = int(os.getenv("NEWS_POST_HOUR", 9))