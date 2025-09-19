#!/usr/bin/env python3
"""
Test script to validate authentication system setup
"""
import sys
import os

# Add the parent directory to sys.path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    # Test imports
    print("🔍 Testing imports...")
    
    from backend.app.core.auth import create_access_token, generate_magic_token
    print("✅ Core auth imports OK")
    
    from backend.app.core.dependencies import get_current_user
    print("✅ Dependencies imports OK")
    
    from backend.app.services.email_service import email_service
    print("✅ Email service imports OK")
    
    from backend.app.api.auth import router
    print("✅ Auth API imports OK")
    
    from backend.app.schemas.schemas import MagicLinkRequest, TokenResponse
    print("✅ Schema imports OK")
    
    from backend.app.models.models import User, MagicToken
    print("✅ Model imports OK")
    
    print("\n🎉 All authentication imports successful!")
    
    # Test token generation
    print("\n🔑 Testing token generation...")
    token = generate_magic_token()
    print(f"✅ Magic token generated: {token[:10]}...")
    
    jwt_token = create_access_token({"sub": "test@usp.br"})
    print(f"✅ JWT token generated: {jwt_token[:30]}...")
    
    print("\n✨ Authentication system setup validation complete!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)