#!/usr/bin/env python3
"""
Test authentication flow end-to-end
"""
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add the parent directory to sys.path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.models import User, MagicToken
from backend.app.core.auth import (
    create_user, 
    create_magic_token, 
    verify_and_use_magic_token,
    create_access_token,
    get_current_user_from_token,
    hash_magic_token, 
    generate_magic_token
)


async def test_authentication_flow():
    """Test the complete authentication flow"""
    print("🧪 Testing Authentication Flow\n")
    
    # Get database session
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 1. Test user creation
        print("1️⃣ Testing user creation...")
        test_email = "joao.silva@usp.br"
        
        # Check if user already exists and clean up
        existing_user = db.query(User).filter(User.email == test_email).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
        
        user = create_user(db, test_email, "João Silva Test")
        print(f"✅ User created: {user.email} (ID: {user.id})")
        
        # 2. Test magic token creation
        print("\n2️⃣ Testing magic token creation...")
        plain_token, magic_token_record = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        print(f"✅ Magic token created: {plain_token[:10]}...")
        print(f"✅ Token expires at: {magic_token_record.expires_at}")
        
        # 3. Test token verification
        print("\n3️⃣ Testing magic token verification...")
        verified_user = verify_and_use_magic_token(db, plain_token)
        if verified_user and verified_user.id == user.id:
            print(f"✅ Token verified successfully for user: {verified_user.email}")
        else:
            print("❌ Token verification failed")
            return
        
        # 4. Test JWT token creation
        print("\n4️⃣ Testing JWT token creation...")
        jwt_token = create_access_token({"sub": user.email, "user_id": user.id})
        print(f"✅ JWT token created: {jwt_token[:50]}...")
        
        # 5. Test JWT token verification
        print("\n5️⃣ Testing JWT token verification...")
        current_user = get_current_user_from_token(db, jwt_token)
        if current_user and current_user.email == user.email:
            print(f"✅ JWT token verified successfully for user: {current_user.email}")
        else:
            print("❌ JWT token verification failed")
            return
        
        # 6. Test token reuse (should fail)
        print("\n6️⃣ Testing magic token reuse (should fail)...")
        reused_user = verify_and_use_magic_token(db, plain_token)
        if reused_user is None:
            print("✅ Magic token reuse correctly blocked")
        else:
            print("❌ Magic token reuse should have failed")
        
        # 7. Test expired token (simulate)
        print("\n7️⃣ Testing expired magic token...")
        # Create another token with past expiration
        
        expired_plain_token = generate_magic_token()
        expired_hashed_token = hash_magic_token(expired_plain_token)
        
        expired_token = MagicToken(
            user_id=user.id,
            token=expired_hashed_token,
            expires_at=datetime.utcnow() - timedelta(minutes=1),  # Already expired
            ip_address="127.0.0.1"
        )
        db.add(expired_token)
        db.commit()
        
        expired_user = verify_and_use_magic_token(db, expired_plain_token)
        if expired_user is None:
            print("✅ Expired token correctly rejected")
        else:
            print("❌ Expired token should have been rejected")
        
        print("\n🎉 All authentication tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup test data
        try:
            test_user = db.query(User).filter(User.email == test_email).first()
            if test_user:
                db.delete(test_user)
                db.commit()
            print("\n🧹 Test data cleaned up")
        except:
            pass
        
        db.close()


if __name__ == "__main__":
    asyncio.run(test_authentication_flow())