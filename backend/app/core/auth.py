"""
Authentication utilities using JWT
"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import User, MagicToken
from backend.app.schemas.schemas import CurrentUser, TokenErrorType

logger = logging.getLogger(__name__)


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
    # Bcrypt has a 72 byte limit, so we truncate the token
    # This is safe because we're still using the full token for verification
    truncated_token = token[:72] if len(token) > 72 else token
    return get_password_hash(truncated_token)


def verify_magic_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a magic token against its hash"""
    try:
        # Bcrypt has a 72 byte limit, so we truncate the token for verification
        truncated_token = plain_token[:72] if len(plain_token) > 72 else plain_token
        result = verify_password(truncated_token, hashed_token)
        logger.debug(f"Token verification: plain='{plain_token[:8]}...', hash='{hashed_token[:20]}...', result={result}")
        return result
    except Exception as e:
        logger.error(f"Error verifying magic token: {e}")
        return False


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
    """
    Create a magic token for a user.
    Security Policy: Only ONE magic token per user at any time.
    Uses UPDATE strategy to prevent table bloat and DoS attacks.
    """
    logger.info(f"Creating magic token for user_id={user_id}")
    
    # Generate plain token
    plain_token = generate_magic_token()
    logger.info(f"Generated plain token: {plain_token[:8]}...")
    
    # Hash for storage
    hashed_token = hash_magic_token(plain_token)
    logger.info(f"Token hashed for storage")
    
    # Create expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES)
    logger.info(f"Token will expire at: {expires_at}")
    
    # Check if user has ANY magic tokens (cleanup multiple if exist)
    existing_tokens = db.query(MagicToken).filter(
        MagicToken.user_id == user_id
    ).all()
    
    if existing_tokens:
        # SECURITY: Ensure only 1 token per user - clean up any extras
        if len(existing_tokens) > 1:
            logger.warning(f"Found {len(existing_tokens)} tokens for user_id={user_id}, cleaning up extras")
            # Delete all but the first one
            for token in existing_tokens[1:]:
                db.delete(token)
                logger.info(f"Deleted extra token id={token.id}")
        
        # UPDATE the remaining token with new values (prevents table bloat)
        main_token = existing_tokens[0]
        logger.info(f"Updating existing token id={main_token.id} for user_id={user_id} (prevents DoS/spam)")
        main_token.token = hashed_token
        main_token.expires_at = expires_at
        main_token.used_at = None  # Reset usage status
        main_token.created_at = datetime.utcnow()  # Update creation time
        main_token.ip_address = ip_address
        main_token.user_agent = user_agent
        
        db.commit()
        db.refresh(main_token)
        
        logger.info(f"Magic token updated successfully with id={main_token.id}")
        return plain_token, main_token
    else:
        # CREATE new token (first time for this user)
        logger.info(f"Creating first magic token for user_id={user_id}")
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
        
        logger.info(f"Magic token created successfully with id={magic_token.id}")
        return plain_token, magic_token


def verify_and_use_magic_token(db: Session, plain_token: str) -> Optional[User]:
    """Verify a magic token and mark it as used"""
    result = verify_magic_token_with_details(db, plain_token)
    return result[0] if result[0] else None


def verify_magic_token_with_details(db: Session, plain_token: str) -> tuple[Optional[User], Optional[TokenErrorType]]:
    """Verify a magic token and return detailed error information"""
    logger.info(f"Attempting to verify magic token: {plain_token[:8]}...")
    
    # Get all tokens to check various failure scenarios
    all_tokens = db.query(MagicToken).all()
    
    for magic_token in all_tokens:
        if verify_magic_token(plain_token, magic_token.token):
            logger.info(f"Found matching token for user_id={magic_token.user_id}")
            
            # Check if token was already used (with grace period for double-clicks)
            if magic_token.used_at is not None:
                # Allow reuse within 30 seconds to handle double-clicks/race conditions
                time_since_used = datetime.utcnow() - magic_token.used_at
                grace_period_seconds = 30
                
                if time_since_used.total_seconds() <= grace_period_seconds:
                    logger.warning(f"Token was recently used ({time_since_used.total_seconds():.1f}s ago) - allowing within grace period")
                    # Return the same user without updating used_at again
                    user = db.query(User).filter(User.id == magic_token.user_id).first()
                    if user:
                        logger.info(f"Returning user within grace period: {user.email}")
                        return user, None
                    else:
                        logger.error(f"User not found for id: {magic_token.user_id}")
                        return None, TokenErrorType.INVALID
                else:
                    logger.warning(f"Token was already used at: {magic_token.used_at} (outside grace period)")
                    return None, TokenErrorType.ALREADY_USED
            
            # Check if token is expired
            if magic_token.expires_at <= datetime.utcnow():
                logger.warning(f"Token expired at: {magic_token.expires_at}")
                return None, TokenErrorType.EXPIRED
            
            # Token is valid - mark as used and return user
            logger.info(f"Token verified successfully for user_id={magic_token.user_id}")
            magic_token.used_at = datetime.utcnow()
            
            # Update user's last login
            user = db.query(User).filter(User.id == magic_token.user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                logger.info(f"Updated last_login for user: {user.email}")
            else:
                logger.error(f"User not found for id: {magic_token.user_id}")
                return None, TokenErrorType.INVALID
            
            db.commit()
            return user, None
    
    # No matching token found
    logger.warning(f"No matching token found for provided magic token")
    return None, TokenErrorType.NOT_FOUND


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


def cleanup_expired_tokens(db: Session) -> dict:
    """
    Clean up expired magic tokens and optionally inactive users.
    This should be called periodically (e.g., daily) via a background task.
    
    Returns statistics about cleanup.
    """
    # Count tokens before cleanup
    expired_tokens_count = db.query(MagicToken).filter(
        MagicToken.expires_at < datetime.utcnow()
    ).count()
    
    # Delete expired tokens
    db.query(MagicToken).filter(
        MagicToken.expires_at < datetime.utcnow()
    ).delete()
    
    # Mark very old used tokens (older than 30 days) for potential cleanup
    old_used_tokens_count = db.query(MagicToken).filter(
        MagicToken.used_at.is_not(None),
        MagicToken.used_at < datetime.utcnow() - timedelta(days=30)
    ).count()
    
    # Optional: Delete very old used tokens to keep database clean
    db.query(MagicToken).filter(
        MagicToken.used_at.is_not(None),
        MagicToken.used_at < datetime.utcnow() - timedelta(days=30)
    ).delete()
    
    db.commit()
    
    return {
        "expired_tokens_deleted": expired_tokens_count,
        "old_used_tokens_deleted": old_used_tokens_count,
        "cleanup_timestamp": datetime.utcnow().isoformat()
    }