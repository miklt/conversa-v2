"""
Email service for sending magic links
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from jinja2 import Template

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
    
    async def send_magic_link(self, to_email: str, magic_token: str, full_name: Optional[str] = None) -> bool:
        """Send magic link email"""
        try:
            # Create magic link URL
            magic_url = f"{settings.FRONTEND_URL}/verify-token?token={magic_token}"
            
            # Email subject
            subject = "Acesso ao Conversa Estágios - Link Mágico"
            
            # Create email content
            html_content = self._create_magic_link_html(
                to_email=to_email,
                magic_url=magic_url,
                full_name=full_name,
                expires_minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES
            )
            
            text_content = self._create_magic_link_text(
                to_email=to_email,
                magic_url=magic_url,
                full_name=full_name,
                expires_minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES
            )
            
            # Send email
            return await self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send magic link email to {to_email}: {e}")
            return False
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: str
    ) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(message)
            
            logger.info(f"Magic link email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _create_magic_link_html(
        self, 
        to_email: str, 
        magic_url: str, 
        full_name: Optional[str], 
        expires_minutes: int
    ) -> str:
        """Create HTML email content for magic link"""
        name = full_name or to_email.split('@')[0].title()
        
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Acesso ao Conversa Estágios</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #1a365d; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .button { 
                    display: inline-block; 
                    background-color: #3182ce; 
                    color: white; 
                    padding: 12px 24px; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0; 
                }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
                .warning { color: #e53e3e; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Conversa Estágios</h1>
                    <p>Sistema de Consulta de Relatórios de Estágio</p>
                </div>
                
                <div class="content">
                    <h2>Olá, {{ name }}!</h2>
                    
                    <p>Você solicitou acesso ao sistema <strong>Conversa Estágios</strong>. 
                    Clique no botão abaixo para fazer login:</p>
                    
                    <div style="text-align: center;">
                        <a href="{{ magic_url }}" class="button">Acessar Sistema</a>
                    </div>
                    
                    <p>Ou copie e cole este link no seu navegador:</p>
                    <p style="word-break: break-all; background-color: #e2e8f0; padding: 10px; border-radius: 5px;">
                        {{ magic_url }}
                    </p>
                    
                    <p class="warning">⚠️ Este link expira em {{ expires_minutes }} minutos.</p>
                    
                    <p>Se você não solicitou este acesso, pode ignorar este email com segurança.</p>
                </div>
                
                <div class="footer">
                    <p>Conversa Estágios - Universidade de São Paulo<br>
                    Sistema para consulta de dados de estágios de Engenharia Elétrica</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return html_template.render(
            name=name,
            magic_url=magic_url,
            expires_minutes=expires_minutes
        )
    
    def _create_magic_link_text(
        self, 
        to_email: str, 
        magic_url: str, 
        full_name: Optional[str], 
        expires_minutes: int
    ) -> str:
        """Create plain text email content for magic link"""
        name = full_name or to_email.split('@')[0].title()
        
        return f"""
Conversa Estágios - Acesso ao Sistema

Olá, {name}!

Você solicitou acesso ao sistema Conversa Estágios.
Clique no link abaixo para fazer login:

{magic_url}

⚠️ Este link expira em {expires_minutes} minutos.

Se você não solicitou este acesso, pode ignorar este email com segurança.

---
Conversa Estágios - Universidade de São Paulo
Sistema para consulta de dados de estágios de Engenharia Elétrica
        """.strip()


# Global email service instance
email_service = EmailService()