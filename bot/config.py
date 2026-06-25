import os

from dotenv import load_dotenv

# Loads a local .env when present (local dev). On Railway, env vars are
# injected directly, so load_dotenv() is a harmless no-op there.
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# The Discord channel ID where daily news will be posted.
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", "0") or "0")

# Hour (UTC) to post daily news, e.g. 9 = 9:00 AM UTC.
NEWS_POST_HOUR = int(os.getenv("NEWS_POST_HOUR", "9") or "9")
