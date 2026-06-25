"""
Discord bot for the AI Tech News Engine.

Features:
  - Posts a daily AI-summarized tech news digest to a configured channel.
  - Replies to @mentions / DMs by asking the backend chat endpoint.

Configuration is read entirely from environment variables (see config.py),
so it runs unchanged on Railway as a long-running worker service.
"""
import asyncio
from datetime import datetime, time, timezone

import aiohttp
import discord
from discord.ext import tasks

from config import (
    DISCORD_TOKEN,
    API_URL,
    NEWS_CHANNEL_ID,
    NEWS_POST_HOUR,
)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def _fetch_news_digest(limit: int = 10) -> str:
    """Call the backend engine to get a ready-to-post digest."""
    url = f"{API_URL.rstrip('/')}/news/?limit={limit}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("summary", "No news available right now.")
    except Exception as e:
        print(f"[bot] Failed to fetch news digest: {e}")
        return "⚠️ Couldn't fetch the tech news digest right now."


async def _ask_backend(message: str) -> str:
    """Forward a user message to the backend chat endpoint."""
    url = f"{API_URL.rstrip('/')}/chat/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json={"message": message},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("reply", "🤔 No reply.")
    except Exception as e:
        print(f"[bot] Failed to reach chat endpoint: {e}")
        return "⚠️ Sorry, I couldn't process that right now."


async def _send_long(channel: discord.abc.Messageable, text: str) -> None:
    """Send text to a channel, splitting on Discord's 2000-char limit."""
    for i in range(0, len(text), 1990):
        await channel.send(text[i : i + 1990])


@tasks.loop(time=time(hour=NEWS_POST_HOUR, minute=0, tzinfo=timezone.utc))
async def daily_news():
    """Post the daily digest at NEWS_POST_HOUR (UTC)."""
    if not NEWS_CHANNEL_ID:
        return
    channel = client.get_channel(NEWS_CHANNEL_ID)
    if channel is None:
        print(f"[bot] News channel {NEWS_CHANNEL_ID} not found.")
        return
    digest = await _fetch_news_digest()
    header = f"📰 **Daily Tech News — {datetime.now(timezone.utc):%Y-%m-%d}**\n\n"
    await _send_long(channel, header + digest)


@client.event
async def on_ready():
    print(f"[bot] Logged in as {client.user} (id={client.user.id})")
    if not daily_news.is_running():
        daily_news.start()


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    is_dm = message.guild is None
    is_mention = client.user in message.mentions

    if not (is_dm or is_mention):
        return

    # Strip the bot mention from the content.
    content = message.content
    if client.user:
        content = content.replace(f"<@{client.user.id}>", "").replace(
            f"<@!{client.user.id}>", ""
        ).strip()

    if not content:
        await message.channel.send("👋 Ask me anything about tech, or mention me with a question!")
        return

    async with message.channel.typing():
        reply = await _ask_backend(content)
    await _send_long(message.channel, reply)


def main():
    if not DISCORD_TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Configure it as an environment variable."
        )
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
