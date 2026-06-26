import discord
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime

from config import DISCORD_TOKEN, API_URL, NEWS_CHANNEL_ID, NEWS_POST_HOUR

# ── Setup ──────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

# help_command=None so we can make our own !help
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ── Helpers ────────────────────────────────────────────────────────────────────
async def fetch_news_summary(limit: int = 10) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/news/?limit={limit}",
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("summary")
    except Exception as e:
        print(f"[bot] fetch_news_summary error: {e}")
    return None


async def send_long(channel, header: str, body: str):
    """Send a message in chunks if it exceeds Discord's 2000 char limit."""
    full = header + body
    if len(full) <= 2000:
        await channel.send(full)
    else:
        await channel.send(header)
        for chunk in [body[i : i + 1900] for i in range(0, len(body), 1900)]:
            await channel.send(chunk)


# ── Daily auto-post task ───────────────────────────────────────────────────────
@tasks.loop(minutes=1)
async def post_daily_news():
    now = datetime.utcnow()

    # run only at exact hour
    if now.hour != NEWS_POST_HOUR or now.minute != 0:
        return

    try:
        channel = bot.get_channel(NEWS_CHANNEL_ID)

        if not channel:
            print(f"[bot] Channel {NEWS_CHANNEL_ID} not found.")
            return

        await channel.send("⏳ Fetching today's tech news, hang tight...")

        summary = await fetch_news_summary(limit=10)

        if not summary:
            await channel.send("⚠️ Couldn't fetch news today. I'll try again tomorrow!")
            return

        header = "📰 **Daily Tech News Digest**\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        await send_long(channel, header, summary)

    except Exception as e:
        print(f"[bot] News task error: {e}")
# ── Events ─────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[bot] Prefix: !  |  Daily news: {NEWS_POST_HOUR:02d}:00 UTC → channel {NEWS_CHANNEL_ID}")

    if not post_daily_news.is_running():
        post_daily_news.start()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user.mentioned_in(message)
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()

    # @mention or DM → chat with AI (skip if it's a command)
    if (is_dm or is_mentioned) and content and not content.startswith("!"):
        async with message.channel.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{API_URL}/chat/",
                        json={"message": content},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            reply = data.get("reply", "No response.")
                            await message.channel.send(reply[:2000])
                        else:
                            await message.channel.send("⚠️ Backend error. Try again!")
            except aiohttp.ClientConnectorError:
                await message.channel.send("⚠️ Can't reach the backend. Is it running?")
            except Exception as e:
                print(f"[bot] Mention error: {e}")

    # IMPORTANT: must be last so prefix commands still work
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Silently ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing argument. Type `!help` to see usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Invalid argument. Type `!help` to see usage.")
    else:
        print(f"[bot] Command error: {error}")


# ── Commands ───────────────────────────────────────────────────────────────────

@bot.command(name="news")
async def news_cmd(ctx, limit: int = 5):
    """Get top tech news on demand. Usage: !news or !news 10"""
    if not (1 <= limit <= 15):
        await ctx.send("⚠️ Limit must be between 1 and 15.")
        return

    status_msg = await ctx.send(f"⏳ Fetching top **{limit}** tech stories...")
    summary = await fetch_news_summary(limit=limit)
    await status_msg.delete()

    if summary:
        header = f"📰 **Top {limit} Tech Stories**\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        await send_long(ctx.channel, header, summary)
    else:
        await ctx.send("⚠️ Failed to fetch news. Try again in a moment!")


@bot.command(name="ask")
async def ask_cmd(ctx, *, question: str):
    """Ask the AI anything. Usage: !ask What is Docker?"""
    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}/chat/",
                    json={"message": question},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get("reply", "No response.")
                        await ctx.send(f"🤖 **Answer:**\n{reply[:1900]}")
                    else:
                        await ctx.send("⚠️ Backend error. Try again!")
        except aiohttp.ClientConnectorError:
            await ctx.send("⚠️ Can't reach the backend. Is it running?")
        except Exception as e:
            print(f"[bot] !ask error: {e}")
            await ctx.send("⚠️ Something went wrong.")


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
        raise ValueError("DISCORD_TOKEN is not set in .env file.")
    bot.run(DISCORD_TOKEN)
