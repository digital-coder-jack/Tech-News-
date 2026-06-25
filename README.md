# 🤖 Tech Community Discord Bot

A Discord bot that posts **daily tech news digests** automatically and answers questions via AI (powered by Groq + LLaMA 3.3).

---

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Loads env vars
│   │   │   └── prompts.py      # AI system prompts
│   │   ├── models/             # (Pydantic models — extend as needed)
│   │   ├── routes/
│   │   │   ├── chat.py         # POST /chat/
│   │   │   └── news.py         # GET  /news/
│   │   ├── services/
│   │   │   ├── groq_service.py # Groq AI calls
│   │   │   └── news_service.py # Hacker News fetcher
│   │   └── main.py             # FastAPI app
│   ├── requirements.txt
│   └── run.py
├── bot/
│   ├── bot.py                  # Discord bot
│   ├── config.py               # Bot env vars
│   └── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Setup

### 1. Clone and configure environment

```bash
cp .env.example .env
# Fill in your values in .env
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

### 3. Start the bot (separate terminal)

```bash
cd bot
pip install -r requirements.txt
python bot.py
```

---

## 🔑 Environment Variables

| Variable         | Description                                           |
|-----------------|-------------------------------------------------------|
| `GROQ_API_KEY`  | From [console.groq.com](https://console.groq.com)     |
| `DISCORD_TOKEN` | Your bot token from Discord Developer Portal          |
| `NEWS_CHANNEL_ID` | Channel ID to post daily news (right-click → Copy ID) |
| `NEWS_POST_HOUR`  | UTC hour to post daily news (default: `9`)           |
| `API_URL`       | Backend URL (default: `http://127.0.0.1:8000`)        |

---

## 🤖 Bot Features

- **Daily Tech News**: Automatically posts a curated, AI-summarized digest at a set time every day
- **@Mention Chat**: Mention the bot or DM it to ask any tech question
- **Free news source**: Uses [Hacker News API](https://github.com/HackerNews/API) — no extra API key needed

---

## 🛠️ API Endpoints

| Method | Endpoint   | Description                        |
|--------|------------|------------------------------------|
| `GET`  | `/`        | Health check                       |
| `POST` | `/chat/`   | Send a message, get an AI reply    |
| `GET`  | `/news/`   | Fetch and summarize today's news   |