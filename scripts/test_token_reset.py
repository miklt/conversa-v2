#!/usr/bin/env python3
"""Testar se create_magic_token está resetando o used_at corretamente"""

import sys
sys.path.append("/Users/m/dev/conversa-v2")

from backend.app.db.database import get_db
from backend.app.core.auth import create_magic_token
from backend.app.models.models import MagicToken, User
from datetime import datetime

def test_token_reset():
    print("🧪 Testando reset do used_at no create_magic_token...")
    
    db = next(get_db())
    
    try:
        # Buscar o usuário com token usado
        user = db.query(User).filter(User.email == "michelet@usp.br").first()
        if not user:
            print("❌ Usuário não encontrado")
            return
        
        print(f"👤 Testando com usuário: {user.email} (id: {user.id})")
        
        # Verificar token antes
        token_before = db.query(MagicToken).filter(MagicToken.user_id == user.id).first()
        print(f"\n📋 ANTES:")
        print(f"   Token ID: {token_before.id}")
        print(f"   Criado: {token_before.created_at}")
        print(f"   Usado: {token_before.used_at}")
        print(f"   Status: {'USADO' if token_before.used_at else 'NÃO USADO'}")
        
        # Criar novo token (deveria resetar o used_at)
        print(f"\n🔄 Criando novo magic token...")
        plain_token, magic_token_obj = create_magic_token(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="TestScript/1.0"
        )
        
        # Verificar token depois
        token_after = db.query(MagicToken).filter(MagicToken.user_id == user.id).first()
        print(f"\n📋 DEPOIS:")
        print(f"   Token ID: {token_after.id}")
        print(f"   Criado: {token_after.created_at}")
        print(f"   Usado: {token_after.used_at}")
        print(f"   Status: {'USADO' if token_after.used_at else 'NÃO USADO'}")
        print(f"   Token Plain: {plain_token[:8]}...")
        
        # Verificação
        if token_after.used_at is None:
            print(f"\n✅ SUCESSO: used_at foi resetado para None")
        else:
            print(f"\n❌ FALHA: used_at ainda está definido: {token_after.used_at}")
        
        if token_before.id == token_after.id:
            print(f"✅ SUCESSO: Mesmo token atualizado (UPDATE)")
        else:
            print(f"❌ FALHA: Token diferente criado (INSERT)")
        
        return token_after.used_at is None
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = test_token_reset()
    print(f"\n🎯 Resultado: {'✅ PASSOU' if success else '❌ FALHOU'}")