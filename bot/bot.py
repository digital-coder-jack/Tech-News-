"""
Discord Tech News Bot
=====================

A minimal, production-ready Discord bot that fetches the latest tech news
and posts clean, formatted messages to Discord.

Commands
--------
  !news            -> latest top tech stories from Hacker News
  !news <n>        -> latest <n> stories (1-10)
  !rss             -> latest headlines from TechCrunch / The Verge RSS feeds
  !help            -> show available commands

Design goals
------------
  * Self-contained: no database, no separate backend required.
  * Cloud-ready: configured entirely via environment variables.
  * Stable: every network call is wrapped in error handling so the bot
    never crashes on a bad request or a flaky API.
  * Non-blocking: all HTTP work is async (aiohttp) so the event loop is
    never blocked. No infinite loops, no time.sleep().

Deployment (Render free tier, "Background Worker"):
    Build command:  pip install -r requirements.txt
    Start command:  python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional
from xml.etree import ElementTree

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration (environment variables only — never hardcode secrets)
# ---------------------------------------------------------------------------

# Load a local .env file when present. In the cloud (Render), environment
# variables are injected directly, so this is a harmless no-op there.
load_dotenv()

DISCORD_TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN")

# Optional backend URL. Not required for core functionality; kept for
# compatibility with the project spec / future extensions.
API_URL: str = os.getenv("API_URL", "").strip()

COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")

# How many stories to return by default / at most.
DEFAULT_NEWS_LIMIT = 5
MAX_NEWS_LIMIT = 10

# External endpoints.
HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

# Optional RSS feeds (no API key required).
RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
}

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=20)
USER_AGENT = "DiscordTechNewsBot/1.0 (+https://render.com)"

# Discord's hard limit on a single message.
DISCORD_MAX_CHARS = 2000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("technews-bot")

# ---------------------------------------------------------------------------
# Discord client setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content / commands.

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)


# ---------------------------------------------------------------------------
# News fetching helpers (all async, all wrapped in error handling)
# ---------------------------------------------------------------------------


async def _get_json(session: aiohttp.ClientSession, url: str):
    """GET a URL and parse JSON. Returns None on any failure."""
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception as exc:  # noqa: BLE001 - we never want this to crash the bot
        log.warning("JSON request failed for %s: %s", url, exc)
        return None


async def _get_text(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """GET a URL and return the body text. Returns None on any failure."""
    try:
        async with session.get(url, timeout=HTTP_TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.text()
    except Exception as exc:  # noqa: BLE001
        log.warning("Text request failed for %s: %s", url, exc)
        return None


async def fetch_hacker_news(limit: int = DEFAULT_NEWS_LIMIT) -> list[dict]:
    """
    Fetch the latest top tech stories from the Hacker News API.

    Returns a list of dicts: {title, score, by, url}. Returns an empty list
    if the API is unreachable (the caller handles the empty case gracefully).
    """
    limit = max(1, min(limit, MAX_NEWS_LIMIT))
    headers = {"User-Agent": USER_AGENT}

    async with aiohttp.ClientSession(headers=headers) as session:
        top_ids = await _get_json(session, HN_TOP_STORIES)
        if not top_ids:
            return []

        wanted_ids = top_ids[:limit]

        # Fetch all story items concurrently (non-blocking, no loops of awaits).
        tasks = [_get_json(session, HN_ITEM.format(id=sid)) for sid in wanted_ids]
        items = await asyncio.gather(*tasks)

    stories: list[dict] = []
    for item in items:
        if not item:
            continue
        story_id = item.get("id")
        stories.append(
            {
                "title": item.get("title", "Untitled"),
                "score": item.get("score", 0),
                "by": item.get("by", "unknown"),
                # Some HN posts have no external URL (Ask HN, etc.) -> link to HN.
                "url": item.get("url")
                or f"https://news.ycombinator.com/item?id={story_id}",
            }
        )
    return stories


async def fetch_rss(limit: int = DEFAULT_NEWS_LIMIT) -> list[dict]:
    """
    Fetch latest headlines from the configured RSS feeds.

    Returns a list of dicts: {title, source, url}. Parsing failures for a
    single feed are skipped, never raised.
    """
    limit = max(1, min(limit, MAX_NEWS_LIMIT))
    headers = {"User-Agent": USER_AGENT}
    results: list[dict] = []

    async with aiohttp.ClientSession(headers=headers) as session:
        for source, feed_url in RSS_FEEDS.items():
            raw = await _get_text(session, feed_url)
            if not raw:
                continue
            results.extend(_parse_rss(raw, source))

    return results[:limit]


def _parse_rss(raw_xml: str, source: str) -> list[dict]:
    """Parse RSS/Atom XML into a list of {title, source, url}."""
    out: list[dict] = []
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError as exc:
        log.warning("Failed to parse RSS from %s: %s", source, exc)
        return out

    # RSS 2.0: <rss><channel><item><title>/<link>
    for item in root.iter("item"):
        title = item.findtext("title")
        link = item.findtext("link")
        if title:
            out.append({"title": title.strip(), "source": source, "url": (link or "").strip()})

    # Atom: <feed><entry><title>/<link href="...">
    atom_ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.iter(f"{atom_ns}entry"):
        title_el = entry.find(f"{atom_ns}title")
        link_el = entry.find(f"{atom_ns}link")
        title = title_el.text if title_el is not None else None
        link = link_el.get("href") if link_el is not None else ""
        if title:
            out.append({"title": title.strip(), "source": source, "url": link.strip()})

    return out


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_hn_stories(stories: list[dict]) -> str:
    """Format Hacker News stories into a clean Discord message."""
    if not stories:
        return "⚠️ Couldn't fetch tech news right now. Please try again shortly."

    blocks = ["📰 **Latest Tech News — Hacker News**\n"]
    for s in stories:
        blocks.append(
            f"🔥 **{s['title']}**\n"
            f"Score: {s['score']} | Author: {s['by']}\n"
            f"Link: {s['url']}"
        )
    return "\n\n".join(blocks)


def format_rss_items(items: list[dict]) -> str:
    """Format RSS headlines into a clean Discord message."""
    if not items:
        return "⚠️ Couldn't fetch RSS headlines right now. Please try again shortly."

    blocks = ["📰 **Latest Tech Headlines — RSS**\n"]
    for it in items:
        blocks.append(f"🔥 **{it['title']}**\nSource: {it['source']}\nLink: {it['url']}")
    return "\n\n".join(blocks)


async def send_long(channel: discord.abc.Messageable, text: str) -> None:
    """Send text to a channel, splitting safely on Discord's 2000-char limit."""
    chunk = DISCORD_MAX_CHARS - 10
    for i in range(0, len(text), chunk):
        await channel.send(text[i : i + chunk])


def _parse_limit(arg: Optional[str]) -> int:
    """Parse an optional numeric argument into a valid story limit."""
    if not arg:
        return DEFAULT_NEWS_LIMIT
    try:
        return max(1, min(int(arg), MAX_NEWS_LIMIT))
    except (ValueError, TypeError):
        return DEFAULT_NEWS_LIMIT


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@bot.command(name="news")
async def news(ctx: commands.Context, count: Optional[str] = None):
    """!news [count] -> latest tech news from Hacker News."""
    limit = _parse_limit(count)
    async with ctx.typing():
        stories = await fetch_hacker_news(limit)
    await send_long(ctx.channel, format_hn_stories(stories))


@bot.command(name="rss")
async def rss(ctx: commands.Context, count: Optional[str] = None):
    """!rss [count] -> latest headlines from TechCrunch / The Verge."""
    limit = _parse_limit(count)
    async with ctx.typing():
        items = await fetch_rss(limit)
    await send_long(ctx.channel, format_rss_items(items))


@bot.command(name="help")
async def help_command(ctx: commands.Context):
    """!help -> show available commands."""
    msg = (
        "🤖 **Tech News Bot — Commands**\n\n"
        f"`{COMMAND_PREFIX}news` — latest tech news from Hacker News\n"
        f"`{COMMAND_PREFIX}news 10` — latest 10 stories (max 10)\n"
        f"`{COMMAND_PREFIX}rss` — latest headlines from TechCrunch / The Verge\n"
        f"`{COMMAND_PREFIX}help` — show this message"
    )
    await ctx.channel.send(msg)


# ---------------------------------------------------------------------------
# Events / error handling
# ---------------------------------------------------------------------------


@bot.event
async def on_ready():
    log.info("Logged in as %s (id=%s)", bot.user, getattr(bot.user, "id", "?"))
    log.info("Tech News Bot is ready. Prefix: %r", COMMAND_PREFIX)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Global command error handler so the bot never crashes."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands silently.
    log.exception("Command error in %s: %s", getattr(ctx.command, "name", "?"), error)
    try:
        await ctx.channel.send("⚠️ Something went wrong handling that command.")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not DISCORD_TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Configure it as an environment variable "
            "(see .env.example)."
        )
    # bot.run() manages the event loop and reconnections; it does not return
    # under normal operation and contains no busy/infinite loop of our own.
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
