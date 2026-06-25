import requests
from app.core.config import GROQ_API_KEY
from app.core.prompts import SYSTEM_PROMPT, NEWS_ENGINE_PROMPT

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
        "max_tokens": 1500,
        "temperature": 0.2,  # keep it factual, low creativity
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


def _build_engine_input(news_items: list[dict]) -> str:
    """Render the ranked, deduplicated items into the engine's input text."""
    lines = []
    for i, item in enumerate(news_items, start=1):
        also = item.get("also_seen_in") or []
        also_note = (
            f" (also reported by: {', '.join(also)})" if also else ""
        )
        summary = item.get("summary", "")
        summary_note = f"\n   Context: {summary}" if summary else ""
        lines.append(
            f"{i}. {item.get('title', 'Untitled')}\n"
            f"   Source: {item.get('source', 'Unknown')}{also_note}\n"
            f"   Link: {item.get('url', '')}{summary_note}"
        )
    return "\n\n".join(lines)


def _fallback_digest(news_items: list[dict]) -> str:
    """
    Produce the STRICT output format without the AI layer.

    Used when GROQ_API_KEY is missing or the API call fails. The engine has
    already filtered/deduped/ranked the items, so this is still a clean digest.
    """
    blocks = []
    for item in news_items:
        also = item.get("also_seen_in") or []
        source = item.get("source", "Unknown")
        if also:
            source = f"{source} — reported across multiple sources ({', '.join(also)})"
        summary = item.get("summary") or "Summary not available from source."
        # Keep summary to ~2-3 lines.
        summary = " ".join(summary.split())
        if len(summary) > 280:
            summary = summary[:277].rstrip() + "..."
        block = (
            f"🔥 {item.get('title', 'Untitled')}\n"
            f"Source: {source}\n"
            f"Summary: {summary}\n"
            f"Link: {item.get('url', '')}"
        )
        blocks.append(block)

    if not blocks:
        return "No high-impact tech news found in the provided data."
    return "\n\n---\n\n".join(blocks)


def summarize_news(news_items: list[dict]) -> str:
    """
    Turn a ranked list of news items into the strict Discord output format.

    The AI Tech News Engine prompt enforces filtering, dedup, ranking, and the
    exact output template. If the AI layer is unavailable, a deterministic
    fallback in the same format is returned.
    """
    if not news_items:
        return "No high-impact tech news found in the provided data."

    engine_input = _build_engine_input(news_items)

    try:
        return _call_groq(NEWS_ENGINE_PROMPT, engine_input)
    except Exception as e:
        print(f"[groq_service] Error in summarize_news: {e}")
        return _fallback_digest(news_items)
