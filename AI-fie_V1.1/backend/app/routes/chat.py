from fastapi import APIRouter
from app.models.journal_models import ChatRequest, ChatResponse
from app.services.chat_orchestrator import handle_chat_message

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    reply = handle_chat_message(
        source=request.source,
        message=request.message
    )
    return ChatResponse(reply=reply)