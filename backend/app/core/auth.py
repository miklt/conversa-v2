"""
Authentication utilities using JWT
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import User, MagicToken
from backend.app.schemas.schemas import CurrentUser


# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return payload
    except JWTError:
        return None


def generate_magic_token() -> str:
    """Generate a secure random token for magic links"""
    return secrets.token_urlsafe(32)


def hash_magic_token(token: str) -> str:
    """Hash a magic token for storage"""
    return get_password_hash(token)


def verify_magic_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a magic token against its hash"""
    return verify_password(plain_token, hashed_token)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, full_name: Optional[str] = None) -> User:
    """Create a new user"""
    user = User(
        email=email,
        full_name=full_name,
        is_active=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_magic_token(
    db: Session,
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> tuple[str, MagicToken]:
    """Create a magic token for a user"""
    # Generate plain token
    plain_token = generate_magic_token()
    
    # Hash for storage
    hashed_token = hash_magic_token(plain_token)
    
    # Create expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES)
    
    # Clean up old unused tokens for this user
    db.query(MagicToken).filter(
        MagicToken.user_id == user_id,
        MagicToken.used_at.is_(None),
        MagicToken.expires_at < datetime.utcnow()
    ).delete()
    
    # Create new token
    magic_token = MagicToken(
        user_id=user_id,
        token=hashed_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(magic_token)
    db.commit()
    db.refresh(magic_token)
    
    return plain_token, magic_token


def verify_and_use_magic_token(db: Session, plain_token: str) -> Optional[User]:
    """Verify a magic token and mark it as used"""
    # Get all unused magic tokens that haven't expired
    magic_tokens = db.query(MagicToken).filter(
        MagicToken.used_at.is_(None),
        MagicToken.expires_at > datetime.utcnow()
    ).all()
    
    for magic_token in magic_tokens:
        if verify_magic_token(plain_token, magic_token.token):
            # Mark token as used
            magic_token.used_at = datetime.utcnow()
            
            # Update user's last login
            user = db.query(User).filter(User.id == magic_token.user_id).first()
            if user:
                user.last_login = datetime.utcnow()
            
            db.commit()
            return user
    
    return None


def get_current_user_from_token(db: Session, token: str) -> Optional[CurrentUser]:
    """Get current user from JWT token"""
    payload = verify_token(token)
    if payload is None:
        return None
    
    email = payload.get("sub")
    if email is None:
        return None
    
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active)
    )


def authenticate_user(db: Session, email: str) -> Optional[User]:
    """Authenticate user by email (for magic link)"""
    user = get_user_by_email(db, email)
    if user and user.is_active:
        return user
    return None