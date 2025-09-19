#!/usr/bin/env python3
"""Verificar estado atual dos magic tokens no banco"""

import sys
import os

# Ajustar path para o projeto
project_root = "/Users/m/dev/conversa-v2"
sys.path.append(project_root)

from backend.app.db.database import get_db
from backend.app.models.models import MagicToken, User
from datetime import datetime

def check_magic_tokens_state():
    print("🔍 Verificando estado atual dos magic tokens...")
    
    db = next(get_db())
    
    try:
        # Buscar todos os tokens
        tokens = db.query(MagicToken).all()
        
        print(f"📊 Total de tokens na tabela: {len(tokens)}")
        print()
        
        for token in tokens:
            user = db.query(User).filter(User.id == token.user_id).first()
            user_email = user.email if user else "Unknown"
            
            # Calcular tempos relativos
            now_utc = datetime.utcnow()
            
            print(f"🎫 Token ID: {token.id}")
            print(f"   👤 Usuário: {user_email} (id: {token.user_id})")
            print(f"   🔑 Hash: {token.token[:20]}...")
            print(f"   📅 Criado: {token.created_at} UTC")
            print(f"   ⏰ Expira: {token.expires_at} UTC")
            print(f"   ✅ Usado: {token.used_at} UTC" if token.used_at else "   ❌ Não usado")
            
            # Status do token
            if token.used_at:
                time_since_used = now_utc - token.used_at
                print(f"   📈 Usado há: {time_since_used}")
                print(f"   🚨 STATUS: USADO ❌")
            elif token.expires_at <= now_utc:
                time_expired = now_utc - token.expires_at
                print(f"   📈 Expirou há: {time_expired}")
                print(f"   🚨 STATUS: EXPIRADO ⏰")
            else:
                time_until_expire = token.expires_at - now_utc
                print(f"   📈 Expira em: {time_until_expire}")
                print(f"   🚨 STATUS: VÁLIDO ✅")
            
            print()
        
        # Verificar se há tokens problemáticos
        used_tokens = [t for t in tokens if t.used_at is not None]
        expired_tokens = [t for t in tokens if t.expires_at <= now_utc and t.used_at is None]
        valid_tokens = [t for t in tokens if t.expires_at > now_utc and t.used_at is None]
        
        print(f"📈 RESUMO:")
        print(f"   Tokens usados: {len(used_tokens)}")
        print(f"   Tokens expirados: {len(expired_tokens)}")
        print(f"   Tokens válidos: {len(valid_tokens)}")
        
        if used_tokens:
            print(f"\n🚨 TOKENS QUE DEVERIAM TER SIDO RESETADOS:")
            for token in used_tokens:
                user = db.query(User).filter(User.id == token.user_id).first()
                print(f"   - ID {token.id} (user: {user.email if user else 'Unknown'})")
                print(f"     Usado em: {token.used_at}")
                print(f"     Criado em: {token.created_at}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    check_magic_tokens_state()