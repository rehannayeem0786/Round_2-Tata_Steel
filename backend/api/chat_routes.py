"""
Chat API routes — Handles conversational interactions with the
multi-agent system, including multi-turn conversations and feedback.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import process_query
from agents.feedback_agent import process_feedback, get_system_accuracy
from data.database import get_all_conversations, get_conversation

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_role: Optional[str] = 'engineer'
    image_data: Optional[str] = None


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_index: int
    rating: str  # 'positive' or 'negative'
    correction: Optional[str] = None


@router.post("")
async def chat(request: ChatRequest):
    """Process a chat message through the agent orchestrator."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        import asyncio
        # Run orchestration pipeline in a separate thread to prevent event loop blocking
        result = await asyncio.to_thread(
            process_query,
            query=request.message,
            conversation_id=request.conversation_id,
            user_role=request.user_role,
            image_data=request.image_data
        )
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        print(f"[ERR] Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on a system response."""
    if request.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="Rating must be 'positive' or 'negative'")
    
    try:
        result = process_feedback(
            request.conversation_id,
            request.message_index,
            request.rating,
            request.correction
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations():
    """List all conversations."""
    conversations = get_all_conversations()
    return {"success": True, "data": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str):
    """Get a specific conversation with full message history."""
    conversation = get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "data": conversation}


@router.get("/accuracy")
async def get_accuracy():
    """Get system accuracy metrics based on feedback."""
    stats = get_system_accuracy()
    return {"success": True, "data": stats}
