from fastapi import APIRouter, HTTPException
from app.services.news_service import fetch_tech_news
from app.services.groq_service import summarize_news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/")
def get_news(limit: int = 10):
    """Fetch and summarize today's top tech news."""
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