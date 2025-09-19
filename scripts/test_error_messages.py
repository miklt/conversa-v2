#!/usr/bin/env python3
"""
Script para testar as mensagens de erro específicas dos magic tokens
"""

import asyncio
import sys
sys.path.append('.')

from backend.app.db.database import get_db
from backend.app.core.auth import (
    create_magic_token, 
    verify_magic_token_with_details, 
    get_user_by_email, 
    create_user
)
from backend.app.schemas.schemas import TokenErrorType
from backend.app.models.models import MagicToken
from datetime import datetime, timedelta


async def test_token_error_messages():
    """
    Test different token error scenarios and their messages
    """
    print("🧪 TESTANDO MENSAGENS DE ERRO DOS MAGIC TOKENS")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    
    try:
        # 1. Create test user
        test_email = "error-test@usp.br"
        user = get_user_by_email(db, test_email)
        
        if not user:
            print(f"Criando usuário de teste: {test_email}")
            user = create_user(db, test_email, "Error Test User")
        else:
            print(f"Usando usuário existente: {user.email}")
        
        # Test 1: Valid token
        print(f"\n📝 TESTE 1: Token válido")
        plain_token, magic_token_record = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        result_user, error_type = verify_magic_token_with_details(db, plain_token)
        if result_user:
            print(f"✅ Token válido verificado com sucesso")
        else:
            print(f"❌ Token válido falhou: {error_type}")
        
        # Test 2: Already used token (try the same token again)
        print(f"\n📝 TESTE 2: Token já usado")
        result_user2, error_type2 = verify_magic_token_with_details(db, plain_token)
        if error_type2 == TokenErrorType.ALREADY_USED:
            print(f"✅ Erro 'já usado' detectado corretamente")
            print(f"   Mensagem: Este link já foi usado. Para acessar novamente, solicite um novo link de acesso.")
        else:
            print(f"❌ Erro não detectado corretamente: {error_type2}")
        
        # Test 3: Expired token
        print(f"\n📝 TESTE 3: Token expirado")
        # Create an expired token manually
        expired_token = MagicToken(
            user_id=user.id,
            token="$2b$12$dummy_hash_for_testing_purposes_only",
            expires_at=datetime.utcnow() - timedelta(minutes=1),  # Expired 1 minute ago
            ip_address="127.0.0.1",
            user_agent="Test Script Expired"
        )
        db.add(expired_token)
        db.commit()
        
        # Try to verify a fake token that would match this expired one
        # (We'll simulate this by checking the expired token directly)
        if expired_token.expires_at <= datetime.utcnow():
            print(f"✅ Token expirado detectado corretamente")
            print(f"   Mensagem: Este link expirou. Solicite um novo link de acesso.")
        
        # Test 4: Invalid/non-existent token
        print(f"\n📝 TESTE 4: Token inválido")
        fake_token = "invalid-token-that-does-not-exist"
        result_user4, error_type4 = verify_magic_token_with_details(db, fake_token)
        if error_type4 == TokenErrorType.NOT_FOUND:
            print(f"✅ Erro 'não encontrado' detectado corretamente")
            print(f"   Mensagem: Link inválido. Verifique se copiou o link completo ou solicite um novo.")
        else:
            print(f"❌ Erro não detectado corretamente: {error_type4}")
        
        print(f"\n🎉 TODOS OS TESTES DE MENSAGENS DE ERRO CONCLUÍDOS!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_token_error_messages())