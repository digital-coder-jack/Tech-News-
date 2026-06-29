import discord
from discord.ext import tasks
from datetime import time
import asyncio
import os
from dotenv import load_dotenv

from news_service import fetch_tech_news
from groq_service import summarize_news

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", 0))
NEWS_POST_HOUR = int(os.getenv("NEWS_POST_HOUR", 9))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def send_long(channel, header: str, body: str):
    """Split and send messages exceeding Discord's 2000 char limit."""
    full = header + body
    if len(full) <= 2000:
        await channel.send(full)
    else:
        await channel.send(header)
        for chunk in [body[i:i + 1900] for i in range(0, len(body), 1900)]:
            await channel.send(chunk)


@tasks.loop(time=time(hour=NEWS_POST_HOUR, minute=0))
async def post_daily_news():
    channel = client.get_channel(NEWS_CHANNEL_ID)
    if not channel:
        print(f"[bot] Channel {NEWS_CHANNEL_ID} not found.")
        print(f"[bot] Bot is currently in these servers: {[g.name for g in client.guilds]}")
        return

    print(f"[bot] Posting news to #{channel.name}...")
    await channel.send("⏳ Fetching today's tech news, hang tight...")

    try:
        # Run blocking requests in a thread so Discord heartbeat never freezes
        news_items = await asyncio.to_thread(fetch_tech_news, 10)
        summary = await asyncio.to_thread(summarize_news, news_items)

        header = "📰 **Daily Tech News Digest**\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        await send_long(channel, header, summary)
        print("[bot] News posted successfully.")
    except Exception as e:
        print(f"[bot] Error posting news: {e}")
        await channel.send("⚠️ Couldn't fetch news today. I'll try again tomorrow!")


@post_daily_news.before_loop
async def before_news():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"[bot] Logged in as {client.user}")
    print(f"[bot] Currently in these servers: {[g.name for g in client.guilds]}")
    print(f"[bot] Will post news at {NEWS_POST_HOUR:02d}:00 UTC → channel {NEWS_CHANNEL_ID}")
    post_daily_news.start()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN is not set.")
    client.run(DISCORD_TOKEN)
