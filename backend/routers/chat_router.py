"""Chat router — main chatbot endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agent.agent_controller import process_message
from backend.rate_limit import rate_limit_user
from backend.auth import get_current_user
from backend.database import ChatMessage, User, get_db
from backend.models import ChatHistoryItem, ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/", response_model=ChatResponse)
def send_message(
    data: ChatRequest,
    current_user: User = Depends(rate_limit_user),
    db: Session = Depends(get_db),
):
    """Process a chat message through the agent pipeline."""
    result = process_message(user=current_user, message=data.message, db=db)
    return ChatResponse(
        response=result["response"],
        tool_used=result.get("tool_used"),
        access_decision=result.get("access_decision"),
        sources=result.get("sources", []),
    )


@router.get("/history", response_model=list[ChatHistoryItem])
def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's chat history."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        ChatHistoryItem(
            role=m.role,
            content=m.content,
            tool_used=m.tool_used,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/history")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear the user's chat history."""
    db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).delete()
    db.commit()
    return {"message": "Chat history cleared."}
