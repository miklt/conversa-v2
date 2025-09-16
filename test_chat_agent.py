#!/usr/bin/env python3
"""
Test script for the Pydantic AI chat agent
"""
import asyncio
import os
import sys
sys.path.append('/Users/m/dev/conversa-v2')

from backend.app.agents.chat_agent import process_chat_message
from backend.app.db.database import get_db
from sqlalchemy.orm import Session

async def test_chat_agent():
    """Test the chat agent with a sample query"""
    # Get database session
    db = next(get_db())
    
    try:
                # Test query about programming languages
        #message = "Qual é a linguagem de programação mais usada?"
        message = "Qual é a empresa com menos estagiários em 2025?"
        
        print(f"Testing query: {message}")
        
        response = await process_chat_message(message, db)
        
        print("Response:")
        print(f"Text: {response.response}")
        print(f"Confidence: {response.confidence}")
        if hasattr(response, 'sources'):
            print(f"Sources: {response.sources}")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_chat_agent())