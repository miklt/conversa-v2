#!/usr/bin/env python3
"""
Test email sending with current configuration
"""
import sys
import os
import asyncio

# Add the parent directory to sys.path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from backend.app.services.email_service import email_service
from backend.app.core.config import settings


async def test_email_sending():
    """Test email sending with current configuration"""
    print("📧 Testing Email Configuration\n")
    
    # Display current configuration (without passwords)
    print("📋 Current Email Settings:")
    print(f"  SMTP Server: {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
    print(f"  Username: {settings.SMTP_USERNAME}")
    print(f"  From Email: {settings.FROM_EMAIL}")
    print(f"  From Name: {settings.FROM_NAME}")
    print(f"  Frontend URL: {settings.FRONTEND_URL}")
    print(f"  Password configured: {'Yes' if settings.SMTP_PASSWORD else 'No'}")
    print()
    
    # Test email address (should be a valid @usp.br email for testing)
    test_email = input("Digite um email @usp.br para teste (ou Enter para usar teste@usp.br): ").strip()
    if not test_email:
        test_email = "teste@usp.br"
    
    if not test_email.endswith("@usp.br"):
        print("❌ Email deve terminar com @usp.br")
        return
    
    # Generate a test magic token
    test_token = "test_token_123456789"
    print(f"\n📤 Enviando email de teste para: {test_email}")
    print(f"🔑 Token de teste: {test_token}")
    print(f"🔗 URL do magic link: {settings.FRONTEND_URL}/verify-token?token={test_token}")
    
    try:
        # Send test email
        success = await email_service.send_magic_link(
            to_email=test_email,
            magic_token=test_token,
            full_name="Usuário Teste"
        )
        
        if success:
            print("\n✅ Email enviado com sucesso!")
            print(f"📬 Verifique a caixa de entrada de {test_email}")
            print("📨 Se não encontrar, verifique também a pasta de spam")
        else:
            print("\n❌ Falha ao enviar email")
            print("🔧 Verifique as configurações SMTP no arquivo .env")
            
    except Exception as e:
        print(f"\n❌ Erro ao enviar email: {e}")
        print("🔧 Possíveis problemas:")
        print("  - Senha do Gmail incorreta (use App Password)")
        print("  - 2FA não habilitado no Gmail")
        print("  - Configurações SMTP incorretas")
        print("  - Conexão de rede bloqueada")


if __name__ == "__main__":
    asyncio.run(test_email_sending())