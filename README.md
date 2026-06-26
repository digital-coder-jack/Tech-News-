# 🤖 AI Tech News Engine + Discord Bot

A FastAPI backend that powers an **AI Tech News Engine** and a Discord bot.
The engine ingests raw tech news from **multiple sources** (Hacker News,
TechCrunch, The Verge, and other RSS feeds), then **filters, deduplicates,
ranks, and summarizes** it into a strict Discord-friendly digest
(powered by Groq + LLaMA 3.3, with a deterministic fallback).

---

## 🧠 What the engine does

1. **Filter** out irrelevant, duplicate, or low-quality news.
2. **Keep** only high-impact tech topics (AI, startups, programming,
   cybersecurity, big tech, hardware launches).
3. **Rank** by importance & relevance (HN score, keyword density,
   cross-source coverage).
4. **Summarize** each item in a strict format and merge near-duplicates,
   noting them as *"reported across multiple sources"*.

### Strict output format

```
🔥 TITLE
Source: (Hacker News / TechCrunch / Verge / etc.)
Summary: 2-3 clear lines explaining the news impact
Link: URL
---
```

The engine never invents news or links — it uses **only** the provided/fetched
input data.

---

## 📁 Project Structure

```
├── api/                    # Vercel serverless entry point (re-exports FastAPI app)
│   └── index.py
├── backend/                # FastAPI service (deploy as Railway service #1)
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Loads env vars
│   │   │   └── prompts.py      # AI Tech News Engine prompt + chat prompt
│   │   ├── routes/
│   │   │   ├── chat.py         # POST /chat/
│   │   │   └── news.py         # GET /news/ , POST /news/process
│   │   ├── services/
│   │   │   ├── groq_service.py # Groq AI calls + strict-format fallback
│   │   │   └── news_service.py # Multi-source fetch + filter/dedup/rank
│   │   └── main.py             # FastAPI app
│   ├── requirements.txt
│   └── run.py                  # Binds to $PORT (Railway-aware)
├── bot/                    # Discord bot (deploy as Railway service #2)
│   ├── bot.py                  # Long-running Discord worker
│   ├── config.py               # Bot env vars (env-driven)
│   ├── requirements.txt
│   ├── railway.json            # Bot service config (start: python bot.py)
│   └── nixpacks.toml           # Bot build config
├── requirements.txt        # Backend deps (root, used by Railway & Vercel)
├── railway.json            # Backend service config (Railway)
├── nixpacks.toml           # Backend build config (Railway)
├── Procfile                # Backend start command (Railway)
├── vercel.json             # Vercel build + routing config
├── .vercelignore           # Files excluded from the Vercel bundle (e.g. bot/)
├── .env.example
├── .gitignore
└── README.md
```

---

## 🛠️ API Endpoints

| Method | Endpoint        | Description                                            |
|--------|-----------------|--------------------------------------------------------|
| `GET`  | `/`             | Health check + endpoint list                           |
| `GET`  | `/news/?limit=` | Fetch from all sources → filter/rank/summarize digest  |
| `POST` | `/news/process` | Run the engine on **your own raw news data**           |
| `POST` | `/chat/`        | Send a message, get an AI reply                        |

### Example: process raw news

```bash
curl -X POST http://127.0.0.1:8000/news/process \
  -H 'Content-Type: application/json' \
  -d '{
        "items": [
          {"title": "OpenAI launches GPT-5", "source": "TechCrunch", "url": "https://techcrunch.com/gpt5", "summary": "Major reasoning leap."},
          {"title": "Lakers win NBA finals", "source": "ESPN", "url": "https://espn.com/x"}
        ],
        "limit": 10
      }'
```

The sports item is dropped; the tech item is returned in the strict format.

---

## 🚂 Deploy to Railway

This repo is **Railway-ready**. Railway runs long-running processes, so it can
host **both** the backend API and the Discord bot. Deploy them as **two
services** inside one Railway project.

### Service #1 — Backend API

1. Push the repo to GitHub.
2. In Railway, **New Project → Deploy from GitHub repo** and select this repo.
3. Railway auto-detects Python (via root `requirements.txt` + `nixpacks.toml`)
   and uses the root `railway.json` / `Procfile` start command:
   ```
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables in **Service → Variables**:
   - `GROQ_API_KEY` — optional (engine still returns a clean digest without it).
5. Click **Generate Domain** (Settings → Networking) to get a public URL.
   Railway injects `PORT` automatically — the app binds to it.

Test after deploy:
```
GET  https://<your-backend>.up.railway.app/
GET  https://<your-backend>.up.railway.app/news/?limit=8
POST https://<your-backend>.up.railway.app/news/process
```

### Service #2 — Discord Bot (optional)

1. In the **same Railway project**, click **New → GitHub Repo** (same repo).
2. In that service's **Settings → Root Directory**, set it to `bot`.
   Railway will then use `bot/railway.json` + `bot/nixpacks.toml`
   (start command: `python bot.py`).
3. Add environment variables:
   - `DISCORD_TOKEN` — your bot token (required).
   - `API_URL` — the backend's Railway URL from Service #1.
   - `NEWS_CHANNEL_ID` — channel ID for the daily digest.
   - `NEWS_POST_HOUR` — UTC hour to post (default `9`).

The bot is a worker (no public port needed). It posts the daily digest and
replies to @mentions / DMs by calling the backend.

> Tip: You can also deploy the backend alone and skip the bot service if you
> only need the HTTP API.

---

## ▲ Deploy to Vercel

The repo is also **Vercel-ready** for the **backend HTTP API**. Vercel runs the
FastAPI app as a Python **serverless function** via `api/index.py` (which
re-exports the same `app` from `backend/app/main.py`), and `vercel.json` routes
all requests to it.

> ⚠️ **Bot not supported on Vercel.** The Discord bot (`bot/`) is a
> long-running worker and cannot run on Vercel's serverless platform. Use
> Railway (or any always-on host) for the bot. Vercel hosts the **API only**.

### Steps

1. Push the repo to GitHub.
2. In Vercel, **Add New… → Project** and import this repo.
3. Leave the build settings at their defaults — Vercel detects `vercel.json`
   and the `@vercel/python` runtime automatically. Root `requirements.txt`
   provides the dependencies.
4. Add environment variables in **Settings → Environment Variables**:
   - `GROQ_API_KEY` — optional (engine still returns a clean digest without it).
5. Click **Deploy**.

Test after deploy:
```
GET  https://<your-project>.vercel.app/
GET  https://<your-project>.vercel.app/news/?limit=8
POST https://<your-project>.vercel.app/news/process
POST https://<your-project>.vercel.app/chat/
```

### Vercel CLI (optional)

```bash
npm i -g vercel
vercel          # preview deploy
vercel --prod   # production deploy
```

---

## ⚙️ Local Setup

```bash
cp .env.example .env   # fill in GROQ_API_KEY (optional), DISCORD_TOKEN, etc.

# Backend
cd backend
pip install -r requirements.txt
python run.py          # http://127.0.0.1:8000

# Bot (separate terminal)
cd bot
pip install -r requirements.txt
python bot.py
```

---

## 🔑 Environment Variables

| Variable          | Description                                                  |
|-------------------|--------------------------------------------------------------|
| `GROQ_API_KEY`    | From [console.groq.com](https://console.groq.com) (optional) |
| `DISCORD_TOKEN`   | Bot token from the Discord Developer Portal (bot service)    |
| `NEWS_CHANNEL_ID` | Channel ID to post the daily digest (bot service)            |
| `NEWS_POST_HOUR`  | UTC hour to post daily news (default: `9`)                   |
| `API_URL`         | Backend URL (default: `http://127.0.0.1:8000`)               |
| `PORT`            | Injected by Railway; backend binds to it automatically (unused on Vercel) |
