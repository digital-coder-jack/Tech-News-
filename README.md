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
├── api/
│   └── index.py            # Vercel serverless entry (exposes FastAPI `app`)
├── backend/
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
│   └── run.py
├── bot/
│   ├── bot.py                  # Discord bot
│   ├── config.py               # Bot env vars
│   └── requirements.txt
├── requirements.txt        # Root deps (used by Vercel)
├── vercel.json             # Vercel build/route config
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

## ☁️ Deploy to Vercel

This repo is **Vercel-ready**.

1. Push the repo to GitHub.
2. In Vercel, **Import Project** → select the repo (no framework preset needed).
3. Add the environment variable **`GROQ_API_KEY`** in
   *Project → Settings → Environment Variables* (optional — the engine still
   returns a clean ranked digest without it).
4. **Deploy.**

How it works:
- `vercel.json` builds `api/index.py` with `@vercel/python` and routes all
  requests to it.
- `api/index.py` adds `backend/` to the path and exposes the FastAPI `app`.
- Root `requirements.txt` provides the Python dependencies.

After deploy, test:
```
GET  https://<your-app>.vercel.app/
GET  https://<your-app>.vercel.app/news/?limit=8
POST https://<your-app>.vercel.app/news/process
```

> Note: Vercel functions are stateless and time-limited. The Discord bot
> (`bot/`) is a long-running process and should be hosted separately
> (Railway, Fly.io, a VM, etc.), pointing `API_URL` at your Vercel deployment.

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
| `DISCORD_TOKEN`   | Bot token from the Discord Developer Portal                  |
| `NEWS_CHANNEL_ID` | Channel ID to post the daily digest                          |
| `NEWS_POST_HOUR`  | UTC hour to post daily news (default: `9`)                   |
| `API_URL`         | Backend URL (default: `http://127.0.0.1:8000`)               |
