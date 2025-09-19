#!/usr/bin/env python3
"""Testar proteção contra dupla verif        # Simular passagem de tempo modificando used_at no banco
        token_record = db.query(MagicToken).filter(MagicToken.user_id == user.id).first()
        if token_record and token_record.used_at:
            # Simular que o token foi usado há 35 segundos
            token_record.used_at = datetime.utcnow() - timedelta(seconds=35)
            db.commit()
            print(f"   Token used_at simulado para: {token_record.used_at}")de token"""

import sys
sys.path.append("/Users/m/dev/conversa-v2")

from backend.app.db.database import get_db
from backend.app.core.auth import create_magic_token, verify_magic_token_with_details
from backend.app.models.models import MagicToken, User
from datetime import datetime, timedelta
import time

def test_double_verification():
    print("🧪 Testando proteção contra dupla verificação...")
    
    db = next(get_db())
    
    try:
        # Buscar usuário
        user = db.query(User).filter(User.email == "michelet@usp.br").first()
        if not user:
            print("❌ Usuário não encontrado")
            return
        
        print(f"👤 Testando com usuário: {user.email} (id: {user.id})")
        
        # Criar novo token
        plain_token, magic_token_obj = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="TestScript/1.0"
        )
        
        print(f"🔑 Token criado: {plain_token[:8]}...")
        
        # PRIMEIRA verificação
        print(f"\n🔄 PRIMEIRA verificação...")
        user1, error1 = verify_magic_token_with_details(db, plain_token)
        
        if user1 and not error1:
            print(f"✅ Primeira verificação: SUCESSO")
            print(f"   Usuário: {user1.email}")
        else:
            print(f"❌ Primeira verificação: FALHA - {error1}")
        
        # SEGUNDA verificação (imediatamente - simula duplo clique)
        print(f"\n⚡ SEGUNDA verificação (imediata - duplo clique)...")
        user2, error2 = verify_magic_token_with_details(db, plain_token)
        
        if user2 and not error2:
            print(f"✅ Segunda verificação: SUCESSO (grace period)")
            print(f"   Usuário: {user2.email}")
        else:
            print(f"❌ Segunda verificação: FALHA - {error2}")
        
        # TERCEIRA verificação (após 35 segundos - simula reuso tardio)
        print(f"\n⏰ Aguardando 35 segundos para testar reuso tardio...")
        print(f"   (simulando tentativa de reuso fora do grace period)")
        
        # Simular passagem de tempo modificando used_at no banco
        token_record = db.query(MagicToken).filter(MagicToken.user_id == user.id).first()
        if token_record and token_record.used_at:
            # Simular que o token foi usado há 35 segundos
            token_record.used_at = datetime.utcnow() - timedelta(seconds=35)
            db.commit()
            print(f"   Token usado_at simulado para: {token_record.used_at}")
        
        user3, error3 = verify_magic_token_with_details(db, plain_token)
        
        if user3 and not error3:
            print(f"❌ Terceira verificação: SUCESSO (ERRO - deveria falhar!)")
        else:
            print(f"✅ Terceira verificação: FALHA - {error3} (correto)")
        
        # Resumo
        print(f"\n📊 RESUMO DO TESTE:")
        print(f"   1ª verificação (nova): {'✅ PASSOU' if user1 else '❌ FALHOU'}")
        print(f"   2ª verificação (grace): {'✅ PASSOU' if user2 else '❌ FALHOU'}")
        print(f"   3ª verificação (tardio): {'✅ PASSOU' if not user3 else '❌ FALHOU'}")
        
        success = bool(user1) and bool(user2) and not bool(user3)
        return success
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = test_double_verification()
    print(f"\n🎯 Resultado geral: {'✅ PASSOU' if success else '❌ FALHOU'}")
    print(f"{'🎉 Proteção contra dupla verificação funcionando!' if success else '🚨 Problema na proteção!'}")