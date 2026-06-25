import requests
from app.core.config import GROQ_API_KEY
from app.core.prompts import SYSTEM_PROMPT, NEWS_SUMMARY_PROMPT

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def _call_groq(system_prompt: str, user_message: str) -> str:
    """Internal helper to call the Groq API."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    res = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


def ask_groq(message: str) -> str:
    """Answer a general user question."""
    try:
        return _call_groq(SYSTEM_PROMPT, message)
    except Exception as e:
        print(f"[groq_service] Error in ask_groq: {e}")
        return "⚠️ Sorry, I couldn't process that right now. Please try again later."


def summarize_news(news_items: list[dict]) -> str:
    """Summarize a list of news items into a Discord-ready message."""
    if not news_items:
        return "No news articles were found to summarize."

    news_text = "\n".join(
        f"{i + 1}. {item['title']} — {item['url']}"
        for i, item in enumerate(news_items)
    )

    try:
        return _call_groq(NEWS_SUMMARY_PROMPT, news_text)
    except Exception as e:
        print(f"[groq_service] Error in summarize_news: {e}")
        # Fallback: return a plain list if AI summarization fails
        fallback = "📰 **Today's Tech News**\n\n"
        for item in news_items:
            fallback += f"• [{item['title']}]({item['url']})\n"
        return fallback