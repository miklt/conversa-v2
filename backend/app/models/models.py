"""
Database models using SQLAlchemy with pgvector support
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, CheckConstraint, UniqueConstraint,
    Enum, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid
import enum


Base = declarative_base()


class CursoEnum(str, enum.Enum):
    """Enum for course types"""
    COMPUTACAO = "Engenharia de Computação"
    ELETRICA = "Engenharia Elétrica"


class PeriodoEnum(str, enum.Enum):
    """Enum for academic periods"""
    PRIMEIRO_SEMESTRE = "1S"
    SEGUNDO_SEMESTRE = "2S"
    PRIMEIRO_QUADRIMESTRE = "1Q"
    SEGUNDO_QUADRIMESTRE = "2Q"
    TERCEIRO_QUADRIMESTRE = "3Q"


class AnoAcademicoEnum(str, enum.Enum):
    """Enum for academic years"""
    SEGUNDO = "2°"
    TERCEIRO = "3°"
    QUARTO = "4°"
    QUINTO = "5°"


class TipoTermoEnum(str, enum.Enum):
    """Enum for technical term types"""
    LINGUAGEM = "linguagem"
    FRAMEWORK = "framework"
    FERRAMENTA = "ferramenta"
    PLATAFORMA = "plataforma"
    BANCO_DADOS = "banco_dados"
    TECNICA = "tecnica"
    TIPO_PROJETO = "tipo_projeto"


class Relatorio(Base):
    """Main reports table"""
    __tablename__ = 'relatorios'
    
    id = Column(Integer, primary_key=True)
    json_completo = Column(JSONB, nullable=False)
    
    # Metadata fields
    ano = Column(Integer, nullable=False)  # Calendar year
    periodo = Column(Enum(PeriodoEnum), nullable=False)
    ano_academico = Column(Enum(AnoAcademicoEnum), nullable=False)
    ordinal_estagio = Column(Integer, nullable=False)
    curso = Column(Enum(CursoEnum), nullable=False)
    
    # Company info
    empresa_razao_social = Column(String(255))
    empresa_cnpj = Column(String(20))
    
    # Tracking
    folder_origin = Column(String(200))  # Original folder name
    arquivo_origem = Column(String(255))  # Original JSON filename
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    embeddings = relationship("RelatorioEmbedding", back_populates="relatorio", cascade="all, delete-orphan")
    termos = relationship("RelatorioTermo", back_populates="relatorio", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('ordinal_estagio BETWEEN 1 AND 5', name='check_ordinal_estagio'),
        CheckConstraint('ano >= 2020 AND ano <= 2030', name='check_ano_valido'),
    )


class RelatorioEmbedding(Base):
    """Embeddings table for vector search"""
    __tablename__ = 'relatorio_embeddings'
    
    id = Column(Integer, primary_key=True)
    relatorio_id = Column(Integer, ForeignKey('relatorios.id', ondelete='CASCADE'), nullable=False)
    
    # Section and content
    secao = Column(String(50), nullable=False)  # 'sobre_empresa', 'atividades_realizadas', 'conclusao'
    conteudo = Column(Text, nullable=False)
    
    # Vector embedding
    embedding = Column(Vector(1536))  # OpenAI ada-002 dimension
    modelo = Column(String(50), default='gemini-embedding-001')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    relatorio = relationship("Relatorio", back_populates="embeddings")


class TermoTecnico(Base):
    """Technical terms normalization table"""
    __tablename__ = 'termos_tecnicos'
    
    id = Column(Integer, primary_key=True)
    termo = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoTermoEnum), nullable=False)
    termo_normalizado = Column(String(100), nullable=False)
    
    # Additional metadata
    descricao = Column(Text)
    sinonimos = Column(JSON)  # List of synonyms
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    relatorios = relationship("RelatorioTermo", back_populates="termo")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('termo', 'tipo', name='unique_termo_tipo'),
    )


class RelatorioTermo(Base):
    """Many-to-many relationship between reports and technical terms"""
    __tablename__ = 'relatorio_termos'
    
    relatorio_id = Column(Integer, ForeignKey('relatorios.id', ondelete='CASCADE'), primary_key=True)
    termo_id = Column(Integer, ForeignKey('termos_tecnicos.id', ondelete='CASCADE'), primary_key=True)
    secao = Column(String(50), primary_key=True)  # Where the term was found
    
    frequencia = Column(Integer, default=1)
    contexto = Column(Text)  # Optional context where term was found
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    relatorio = relationship("Relatorio", back_populates="termos")
    termo = relationship("TermoTecnico", back_populates="relatorios")


class ChatSession(Base):
    """Chat sessions table for conversation tracking"""
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    
    # Optional user identification
    user_identifier = Column(String(100))  # will be email with a sufix @usp.br
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Chat messages table"""
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Optional metadata (e.g., which reports were referenced)
    message_metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
