from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.news import router as news_router

app = FastAPI(
    title="AI Tech News Engine API",
    description=(
        "Backend API for the Discord tech news + chat bot. "
        "Includes an AI Tech News Engine that fetches, filters, deduplicates, "
        "ranks, and summarizes high-impact tech news into a strict Discord format."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(news_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "AI Tech News Engine API is running.",
        "endpoints": {
            "health": "GET /",
            "fetch_and_summarize": "GET /news/?limit=10",
            "process_raw": "POST /news/process",
            "chat": "POST /chat/",
        },
    }
