#!/usr/bin/env python3
"""
Script para debugar o problema de verificação de magic tokens
"""

import asyncio
import sys
sys.path.append('.')

from backend.app.db.database import get_db
from backend.app.core.auth import create_magic_token, verify_and_use_magic_token, get_user_by_email, create_user
from backend.app.models.models import User, MagicToken
from datetime import datetime


async def debug_magic_token_issue():
    """
    Debug the magic token verification issue
    """
    print("🔍 DEBUGGING MAGIC TOKEN VERIFICATION")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # 1. Get or create a test user
        test_email = "debug@usp.br"
        user = get_user_by_email(db, test_email)
        
        if not user:
            print(f"Creating test user: {test_email}")
            user = create_user(db, test_email, "Debug User")
        else:
            print(f"Using existing user: {user.email} (id: {user.id})")
        
        # 2. Create a magic token
        print("\n📝 Creating magic token...")
        plain_token, magic_token_record = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Debug Script"
        )
        
        print(f"Plain token: {plain_token}")
        print(f"Token ID: {magic_token_record.id}")
        print(f"Expires at: {magic_token_record.expires_at}")
        print(f"Current time: {datetime.utcnow()}")
        
        # 3. Verify the token immediately
        print("\n🔍 Verifying token...")
        verified_user = verify_and_use_magic_token(db, plain_token)
        
        if verified_user:
            print(f"✅ Token verified successfully!")
            print(f"User: {verified_user.email}")
            print(f"User ID: {verified_user.id}")
        else:
            print("❌ Token verification failed!")
            
            # Debug: Check what tokens exist
            print("\n🔍 Checking existing tokens...")
            all_tokens = db.query(MagicToken).filter(
                MagicToken.user_id == user.id
            ).all()
            
            for i, token in enumerate(all_tokens):
                print(f"Token {i+1}:")
                print(f"  ID: {token.id}")
                print(f"  Used at: {token.used_at}")
                print(f"  Expires at: {token.expires_at}")
                print(f"  Is expired: {token.expires_at < datetime.utcnow()}")
                print(f"  Hash preview: {token.token[:30]}...")
        
        # 4. Test with a new token to see if the issue persists
        print("\n🔄 Testing with a fresh token...")
        plain_token2, magic_token_record2 = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Debug Script 2"
        )
        
        verified_user2 = verify_and_use_magic_token(db, plain_token2)
        
        if verified_user2:
            print(f"✅ Second token verified successfully!")
        else:
            print("❌ Second token verification also failed!")
            
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(debug_magic_token_issue())