# Discord Tech News Bot

A minimal, production-ready Discord bot that fetches the latest tech news and
posts clean, formatted messages to Discord. Self-contained (no database, no
separate backend) and deployable on the **Render free tier**.

## Features

- `!news` — latest top tech stories from the **Hacker News API** (primary source)
- `!news 10` — fetch a specific number of stories (1–10)
- `!rss` — latest headlines from **TechCrunch** and **The Verge** RSS feeds
- `!help` — list commands
- Fully async (non-blocking), robust error handling — never crashes on a bad request
- Configured entirely via **environment variables** (no hardcoded secrets)

## Message format

```
🔥 TITLE
Score: X | Author: Y
Link: URL
```

## Project structure

```
bot/
 ├── bot.py            # the bot (commands + HN/RSS fetching)
 ├── requirements.txt  # dependencies
 ├── render.yaml       # Render Blueprint (Background Worker)
 ├── .env.example      # sample env vars (copy to .env locally)
 └── README.md
```

## Environment variables

| Variable         | Required | Description                                          |
|------------------|----------|------------------------------------------------------|
| `DISCORD_TOKEN`  | ✅ Yes   | Discord bot token (Developer Portal → Bot)           |
| `API_URL`        | ❌ No    | Optional backend URL (unused by core features)       |
| `COMMAND_PREFIX` | ❌ No    | Command prefix, default `!`                          |

> Enable the **Message Content Intent** for your bot in the Discord Developer
> Portal (Bot → Privileged Gateway Intents).

## Run locally

```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your real DISCORD_TOKEN in .env
python bot.py
```

## Deploy on Render (24/7, free tier)

1. Push this repo to GitHub.
2. In Render, **New → Background Worker** (a worker, not a web service — the
   bot has no HTTP port).
3. Settings:
   - **Root Directory:** `bot`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. Add an environment variable **`DISCORD_TOKEN`** (your secret token).
5. Deploy. Logs will show `Logged in as ...` when it's live.

Alternatively, use the included `render.yaml` Blueprint (**New → Blueprint**).
