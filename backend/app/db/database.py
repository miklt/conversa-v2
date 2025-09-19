"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings
from backend.app.models.models import Base

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for development
    echo=settings.DEBUG,  # Log SQL statements in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Get database session
    To be used as a dependency in FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """
    Drop all tables - use with caution!
    """
    Base.metadata.drop_all(bind=engine)
