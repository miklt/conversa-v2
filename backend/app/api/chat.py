"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from backend.app.db.database import get_db
from backend.app.schemas.schemas import ChatRequest, ChatResponse
from backend.app.agents.chat_agent import process_chat_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Process a chat message and return a response using Pydantic AI agent
    """
    try:
        logger.info(f"Processing chat message: {request.message}")
        
        # Use Pydantic AI agent to process the message
        response = await process_chat_message(request.message, db)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat message")
