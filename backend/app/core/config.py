"""
Configuration settings for the application
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://conversa_user:conversa_senha_2024@localhost:5432/conversa_estagios"
    )
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Application
    APP_NAME: str = "Conversa Estágios"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000","https://estagiosv2.pcs.usp.br",'http://localhost','http://200.144.245.12:50100','http://localhost:50100']
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    MAGIC_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("MAGIC_TOKEN_EXPIRE_MINUTES", "15"))  # 15 minutes
    
    # Email Configuration
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@example.com")
    FROM_NAME: str = os.getenv("FROM_NAME", "Conversa Estágios")
    VITE_API_URL: str = os.getenv("VITE_API_URL", "http://localhost:8000/api/v1")
    
    # Frontend URL for magic links
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
