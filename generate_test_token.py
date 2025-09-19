"""
Generate a fresh token for immediate testing without email
"""
import sys
import os
import asyncio
sys.path.append('/Users/m/dev/conversa-v2')

from backend.app.core.auth import create_magic_token
from backend.app.core.config import settings

def generate_test_token():
    """Generate a plaintext magic token for testing"""
    test_email = "michelet@usp.br"
    
    # Generate raw magic token (this is what gets sent in the email)
    magic_token = create_magic_token(test_email)
    
    print(f"🧪 Generated test magic token for {test_email}")
    print(f"🔗 Test URL: {settings.FRONTEND_URL}/verify-token?token={magic_token}")
    print(f"⏰ Token expires in {settings.MAGIC_TOKEN_EXPIRE_MINUTES} minutes")
    print("")
    print(f"Raw token (copy this): {magic_token}")
    
    return magic_token

if __name__ == "__main__":
    token = generate_test_token()