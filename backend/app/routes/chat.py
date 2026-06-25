from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.groq_service import ask_groq

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/", response_model=ChatResponse)
def chat(data: ChatRequest):
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    reply = ask_groq(data.message)
    return {"reply": reply}