import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Your backend URL (Vercel)
API_URL = os.getenv("API_URL")

# Discord channel where news will be posted
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", "0"))

# Hour (UTC) when daily news should be posted
NEWS_POST_HOUR = int(os.getenv("NEWS_POST_HOUR", "9"))
