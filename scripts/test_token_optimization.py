#!/usr/bin/env python3
"""
Test script para validar a otimização anti-DoS da tabela magic_tokens.
Testa se múltiplas solicitações do mesmo usuário atualizam o mesmo registro.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.app.db.database import get_db
from backend.app.core.auth import create_magic_token
from backend.app.models.models import MagicToken, User
from datetime import datetime

def test_token_optimization():
    """Testa se a otimização de tokens está funcionando corretamente"""
    print("🧪 Testando otimização anti-DoS da tabela magic_tokens...")
    
    db = next(get_db())
    
    try:
        # Buscar um usuário existente para teste
        user = db.query(User).first()
        if not user:
            print("❌ Nenhum usuário encontrado para teste")
            return
        
        user_id = user.id
        print(f"📋 Testando com user_id={user_id}")
        
        # Contar tokens iniciais na tabela
        initial_count = db.query(MagicToken).count()
        user_tokens_initial = db.query(MagicToken).filter(MagicToken.user_id == user_id).count()
        
        print(f"📊 Estado inicial:")
        print(f"   - Total de tokens na tabela: {initial_count}")
        print(f"   - Tokens do usuário {user_id}: {user_tokens_initial}")
        
        print(f"\n🔄 Simulando múltiplas solicitações de magic token...")
        
        # Simular 5 solicitações consecutivas (potencial ataque DoS)
        tokens_created = []
        
        for i in range(1, 6):
            print(f"\n   Solicitação #{i}:")
            plain_token, magic_token_obj = create_magic_token(
                db=db,
                user_id=user_id,
                ip_address=f"192.168.1.{i}",
                user_agent=f"TestAgent/{i}.0"
            )
            
            tokens_created.append({
                'plain': plain_token,
                'id': magic_token_obj.id,
                'created_at': magic_token_obj.created_at
            })
            
            # Verificar estado da tabela após cada solicitação
            total_count = db.query(MagicToken).count()
            user_count = db.query(MagicToken).filter(MagicToken.user_id == user_id).count()
            
            print(f"     Token ID: {magic_token_obj.id}")
            print(f"     Total na tabela: {total_count}")
            print(f"     Tokens do usuário: {user_count}")
        
        print(f"\n📊 Resultados do teste:")
        
        # Verificar se apenas 1 token por usuário
        final_user_count = db.query(MagicToken).filter(MagicToken.user_id == user_id).count()
        final_total_count = db.query(MagicToken).count()
        
        print(f"   - Tokens finais do usuário: {final_user_count}")
        print(f"   - Total final na tabela: {final_total_count}")
        print(f"   - Crescimento da tabela: {final_total_count - initial_count}")
        
        # Verificar se todos os tokens têm o mesmo ID (foram atualizados)
        unique_ids = set(token['id'] for token in tokens_created)
        print(f"   - IDs únicos gerados: {len(unique_ids)} (esperado: 1)")
        print(f"   - IDs: {list(unique_ids)}")
        
        # Verificações de sucesso
        success_checks = []
        
        # Check 1: Apenas 1 token por usuário
        if final_user_count == 1:
            print("✅ SUCESSO: Apenas 1 token por usuário mantido")
            success_checks.append(True)
        else:
            print(f"❌ FALHA: {final_user_count} tokens encontrados para o usuário (esperado: 1)")
            success_checks.append(False)
        
        # Check 2: Tabela não cresceu descontroladamente
        growth = final_total_count - initial_count
        if growth <= 1:  # Máximo 1 novo token se usuário não tinha antes
            print(f"✅ SUCESSO: Crescimento controlado da tabela (+{growth})")
            success_checks.append(True)
        else:
            print(f"❌ FALHA: Tabela cresceu muito (+{growth} tokens)")
            success_checks.append(False)
        
        # Check 3: Mesmo ID reutilizado (UPDATE ao invés de INSERT)
        if len(unique_ids) == 1:
            print("✅ SUCESSO: Mesmo registro atualizado (UPDATE)")
            success_checks.append(True)
        else:
            print(f"❌ FALHA: {len(unique_ids)} registros diferentes criados")
            success_checks.append(False)
        
        # Resultado final
        if all(success_checks):
            print(f"\n🎉 TESTE PASSOU! Otimização anti-DoS funcionando perfeitamente")
            print(f"   - Proteção contra spam de solicitações: ✅")
            print(f"   - Tabela com tamanho controlado: ✅") 
            print(f"   - Performance otimizada: ✅")
        else:
            print(f"\n❌ TESTE FALHOU! Verificar implementação")
        
        return all(success_checks)
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = test_token_optimization()
    sys.exit(0 if success else 1)