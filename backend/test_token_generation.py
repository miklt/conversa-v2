"""
Quick test to generate a fresh magic token for testing verification
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.auth import create_magic_token
from app.core.config import settings

async def generate_test_token():
    """Generate a test magic token"""
    test_email = "michelet@usp.br"
    
    # Generate magic token
    magic_token = create_magic_token(test_email)
    
    print(f"🧪 Generated test magic token for {test_email}")
    print(f"🔗 Test URL: {settings.FRONTEND_URL}/verify-token?token={magic_token}")
    print(f"⏰ Token expires in {settings.MAGIC_TOKEN_EXPIRE_MINUTES} minutes")
    
    return magic_token

if __name__ == "__main__":
    token = asyncio.run(generate_test_token())