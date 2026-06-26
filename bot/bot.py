import discord
from discord.ext import commands, tasks
from datetime import time

from config import DISCORD_TOKEN, NEWS_CHANNEL_ID, NEWS_POST_HOUR
from groq_service import ask_groq, summarize_news
from news_service import fetch_tech_news

# ── Setup ──────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ── Helper ─────────────────────────────────────────────────────────────────────
async def send_long(channel, header: str, body: str):
    """Split and send messages exceeding Discord's 2000 char limit."""
    full = header + body
    if len(full) <= 2000:
        await channel.send(full)
    else:
        await channel.send(header)
        for chunk in [body[i : i + 1900] for i in range(0, len(body), 1900)]:
            await channel.send(chunk)


# ── Daily auto-post ────────────────────────────────────────────────────────────
@tasks.loop(time=time(hour=NEWS_POST_HOUR, minute=0))
async def post_daily_news():
    if not NEWS_CHANNEL_ID:
        print("[bot] NEWS_CHANNEL_ID not set — skipping.")
        return

    channel = bot.get_channel(NEWS_CHANNEL_ID)
    if not channel:
        print(f"[bot] Channel {NEWS_CHANNEL_ID} not found.")
        return

    await channel.send("⏳ Fetching today's tech news, hang tight...")

    try:
        news_items = fetch_tech_news(limit=10)
        summary = summarize_news(news_items)
        header = "📰 **Daily Tech News Digest**\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        await send_long(channel, header, summary)
    except Exception as e:
        print(f"[bot] Daily news error: {e}")
        await channel.send("⚠️ Couldn't fetch news today. I'll try again tomorrow!")


@post_daily_news.before_loop
async def before_news():
    await bot.wait_until_ready()


# ── Events ─────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[bot] Daily news: {NEWS_POST_HOUR:02d}:00 UTC → channel {NEWS_CHANNEL_ID}")
    post_daily_news.start()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user.mentioned_in(message)
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()

    # @mention or DM → chat with AI
    if (is_dm or is_mentioned) and content and not content.startswith("!"):
        async with message.channel.typing():
            reply = ask_groq(content)
            await message.channel.send(reply[:2000])

    # Always process commands too
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing argument. Type `!help` to see usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Invalid argument. Type `!help` to see usage.")
    else:
        print(f"[bot] Command error: {error}")


# ── Commands ───────────────────────────────────────────────────────────────────

@bot.command(name="news")
async def news_cmd(ctx, limit: int = 5):
    """Get top tech news right now. Usage: !news or !news 10"""
    if not (1 <= limit <= 15):
        await ctx.send("⚠️ Limit must be between 1 and 15.")
        return

    status_msg = await ctx.send(f"⏳ Fetching top **{limit}** tech stories...")

    try:
        news_items = fetch_tech_news(limit=limit)
        summary = summarize_news(news_items)
        await status_msg.delete()
        header = f"📰 **Top {limit} Tech Stories**\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        await send_long(ctx.channel, header, summary)
    except Exception as e:
        print(f"[bot] !news error: {e}")
        await status_msg.edit(content="⚠️ Failed to fetch news. Try again!")


@bot.command(name="ask")
async def ask_cmd(ctx, *, question: str):
    """Ask the AI anything. Usage: !ask What is Docker?"""
    async with ctx.typing():
        reply = ask_groq(question)
        await ctx.send(f"🤖 **Answer:**\n{reply[:1900]}")


@bot.command(name="help")
async def help_cmd(ctx):
    """Show all available commands."""
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here's everything I can do:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="📰 `!news [limit]`",
        value="Get top tech news **right now**.\n`!news` → 5 stories  |  `!news 10` → 10 stories",
        inline=False,
    )
    embed.add_field(
        name="🤖 `!ask <question>`",
        value="Ask me anything about tech or coding.\n`!ask What is Docker?`",
        inline=False,
    )
    embed.add_field(
        name="💬 `@mention` or DM",
        value="Mention me for a free-form conversation.\n`@BotName explain async/await`",
        inline=False,
    )
    embed.add_field(
        name="📅 Auto Daily News",
        value=f"I automatically post a news digest every day at **{NEWS_POST_HOUR:02d}:00 UTC**.",
        inline=False,
    )
    embed.set_footer(text="Powered by Groq AI + Hacker News")
    await ctx.send(embed=embed)


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN is not set in environment variables.")
    bot.run(DISCORD_TOKEN)
