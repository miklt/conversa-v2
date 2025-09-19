"""
Authentication middleware and dependencies
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.core.auth import get_current_user_from_token
from backend.app.schemas.schemas import CurrentUser


# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT token.
    Raises HTTPException if user is not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_current_user_from_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    Dependency to optionally get current authenticated user from JWT token.
    Returns None if user is not authenticated (doesn't raise exception).
    """
    if not credentials:
        return None
    
    return get_current_user_from_token(db, credentials.credentials)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for X-Forwarded-For header (when behind a proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in case of multiple proxies
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to client IP
    client_host = request.client.host if request.client else "unknown"
    return client_host


def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")