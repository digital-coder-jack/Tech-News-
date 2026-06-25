from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.news_service import fetch_tech_news, process_news_items
from app.services.groq_service import summarize_news

router = APIRouter(prefix="/news", tags=["news"])


class RawNewsItem(BaseModel):
    title: str = Field(..., description="Headline of the news item")
    url: str | None = Field(default="", description="Link to the article")
    source: str | None = Field(default="Unknown", description="Origin source")
    summary: str | None = Field(default="", description="Optional context/description")
    score: int | None = Field(default=0, description="Optional popularity score")


class ProcessRequest(BaseModel):
    items: list[RawNewsItem] = Field(..., description="Raw news items to process")
    limit: int = Field(default=10, ge=1, le=20)


@router.get("/")
def get_news(limit: int = 10):
    """Fetch high-impact tech news from multiple sources and return a digest."""
    if not (1 <= limit <= 20):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20.")

    news_items = fetch_tech_news(limit=limit)

    if not news_items:
        raise HTTPException(
            status_code=503, detail="Failed to fetch news. Try again later."
        )

    summary = summarize_news(news_items)
    return {
        "summary": summary,
        "count": len(news_items),
        "raw": news_items,
    }


@router.post("/process")
def process_news(payload: ProcessRequest):
    """
    Run the AI Tech News Engine on RAW news data supplied by the caller.

    Filters, deduplicates, ranks, and summarizes the provided items into the
    strict Discord output format.
    """
    raw = [item.model_dump() for item in payload.items]
    ranked = process_news_items(raw, limit=payload.limit)

    if not ranked:
        return {
            "summary": "No high-impact tech news found in the provided data.",
            "count": 0,
            "raw": [],
        }

    summary = summarize_news(ranked)
    return {
        "summary": summary,
        "count": len(ranked),
        "raw": ranked,
    }
