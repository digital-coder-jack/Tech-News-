from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.routes.news import router as news_router

app = FastAPI(
    title="Tech Community Bot API",
    description="Backend API for the Discord tech news and chat bot.",
    version="1.0.0",
)

app.include_router(chat_router)
app.include_router(news_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Bot API is running."}