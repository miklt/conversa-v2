"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging

from backend.app.db.database import get_db
from backend.app.schemas.schemas import ChatRequest, ChatResponse, CurrentUser
from backend.app.core.dependencies import get_current_user_optional
from backend.app.agents.chat_agent import process_chat_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
):
    """
    Process a chat message and return a response using Pydantic AI agent.
    Authentication is optional - logged in users get enhanced experience.
    """
    try:
        # Log user context if authenticated
        if current_user:
            logger.info(f"Processing chat message from authenticated user {current_user.email}: {request.message}")
        else:
            logger.info(f"Processing chat message from anonymous user: {request.message}")
        
        # Use Pydantic AI agent to process the message
        response = await process_chat_message(request.message, db)
        
        # Add session ID if user is authenticated (could be used for chat history)
        if current_user:
            # In the future, we could create/manage chat sessions here
            response.session_id = f"user_{current_user.id}_session"
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat message")
