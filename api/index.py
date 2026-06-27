import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# ── Prompts ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful and friendly AI assistant for a tech community Discord server.
Answer questions clearly and concisely about tech, programming, and general queries.
Keep responses short and Discord-friendly."""

NEWS_SUMMARY_PROMPT = """You are a tech news curator for a Discord community server.
Given a list of tech news headlines and links, write a clean engaging Discord message summarizing today's top stories.
Rules:
- Use Discord markdown (bold, bullet points)
- Add a relevant emoji to each story
- Keep each summary to 1-2 punchy sentences
- Put the link after each story title
- End with a short motivating line for the community"""

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Tech Community Bot API",
    description="Backend API for the Discord tech news and chat bot.",
    version="1.0.0",
)

# ── Pydantic models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# ── Groq service ───────────────────────────────────────────────────────────────
def _call_groq(system_prompt: str, user_message: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    res = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


def ask_groq(message: str) -> str:
    try:
        return _call_groq(SYSTEM_PROMPT, message)
    except Exception as e:
        print(f"[groq] ask_groq error: {e}")
        return "⚠️ Sorry, I couldn't process that right now. Please try again later."


def summarize_news(news_items: list) -> str:
    if not news_items:
        return "No news articles found."

    news_text = "\n".join(
        f"{i + 1}. {item['title']} — {item['url']}"
        for i, item in enumerate(news_items)
    )

    try:
        return _call_groq(NEWS_SUMMARY_PROMPT, news_text)
    except Exception as e:
        print(f"[groq] summarize_news error: {e}")
        fallback = "📰 **Today's Tech News**\n\n"
        for item in news_items:
            fallback += f"• **{item['title']}**\n  {item['url']}\n\n"
        return fallback

# ── News service ───────────────────────────────────────────────────────────────
def fetch_tech_news(limit: int = 10) -> list:
    try:
        response = requests.get(HN_TOP_STORIES_URL, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[: limit * 2]

        stories = []
        for story_id in story_ids:
            if len(stories) >= limit:
                break
            item = requests.get(HN_ITEM_URL.format(story_id), timeout=10).json()
            if item and item.get("type") == "story" and item.get("url"):
                stories.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url"),
                    "score": item.get("score", 0),
                })
        return stories
    except Exception as e:
        print(f"[news] fetch error: {e}")
        return []

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Bot API is running."}


@app.post("/chat/", response_model=ChatResponse)
def chat(data: ChatRequest):
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    reply = ask_groq(data.message)
    return {"reply": reply}


@app.get("/news/")
def get_news(limit: int = 10):
    if not (1 <= limit <= 20):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20.")
    news_items = fetch_tech_news(limit=limit)
    if not news_items:
        raise HTTPException(status_code=503, detail="Failed to fetch news. Try again later.")
    summary = summarize_news(news_items)
    return {
        "summary": summary,
        "count": len(news_items),
        "raw": news_items,
    }
