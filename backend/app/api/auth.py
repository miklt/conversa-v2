"""
Authentication API endpoints
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.core.auth import (
    create_access_token, 
    create_magic_token, 
    get_user_by_email, 
    create_user,
    verify_and_use_magic_token
)
from backend.app.core.dependencies import get_current_user, get_client_ip, get_user_agent
from backend.app.core.config import settings
from backend.app.services.email_service import email_service
from backend.app.schemas.schemas import (
    MagicLinkRequest, 
    MagicLinkResponse, 
    VerifyTokenRequest, 
    TokenResponse,
    UserResponse,
    CurrentUser,
    ErrorResponse
)


router = APIRouter()


@router.post(
    "/request-magic-link",
    response_model=MagicLinkResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid email domain"},
        500: {"model": ErrorResponse, "description": "Email sending failed"}
    }
)
async def request_magic_link(
    request: Request,
    magic_link_request: MagicLinkRequest,
    db: Session = Depends(get_db)
):
    """
    Request a magic link for authentication.
    Only @usp.br emails are allowed.
    """
    email = magic_link_request.email.lower()
    
    # Get or create user
    user = get_user_by_email(db, email)
    if not user:
        # Extract name from email for better UX
        name_part = email.split('@')[0]
        full_name = name_part.replace('.', ' ').title()
        
        user = create_user(db, email, full_name)
    
    # Get client info for security
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Create magic token
    plain_token, magic_token_record = create_magic_token(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Send magic link email
    email_sent = await email_service.send_magic_link(
        to_email=email,
        magic_token=plain_token,
        full_name=user.full_name
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send magic link email. Please try again."
        )
    
    return MagicLinkResponse(
        message="Magic link enviado para seu email",
        email=email,
        expires_in_minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES
    )


@router.post(
    "/verify-token",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
        401: {"model": ErrorResponse, "description": "Token verification failed"}
    }
)
async def verify_magic_token(
    verify_request: VerifyTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Verify magic token and return JWT access token.
    """
    user = verify_and_use_magic_token(db, verify_request.token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic token"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Create JWT access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at,
        last_login=user.last_login
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=user_response
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    """
    # Get full user details from database
    user = get_user_by_email(db, current_user.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
async def refresh_token(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh the current access token.
    """
    # Get full user details from database
    user = get_user_by_email(db, current_user.email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new JWT access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at,
        last_login=user.last_login
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=user_response
    )