"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ChatRole(str, Enum):
    """Chat message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TokenErrorType(str, Enum):
    """Magic token error types"""
    INVALID = "invalid"
    EXPIRED = "expired"
    ALREADY_USED = "already_used"
    NOT_FOUND = "not_found"


class ChatMessage(BaseModel):
    """Chat message model"""
    role: ChatRole
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    context_limit: Optional[int] = Field(default=3, ge=1, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qual a linguagem de programação mais usada em 2025?",
                "session_id": "optional-session-uuid",
                "context_limit": 3
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Em 2025, Python foi a linguagem mais utilizada nos estágios, seguida por JavaScript e Java.",
                "session_id": "session-uuid",
                "sources": [
                    {"report_id": 1, "company": "BTG Pactual", "relevance": 0.95}
                ],
                "confidence": 0.85
            }
        }


class ReportSearchRequest(BaseModel):
    """Report search request model"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: Optional[int] = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "desenvolvimento backend com Python",
                "limit": 10,
                "filters": {
                    "year": 2025,
                    "course": "Engenharia de Computação"
                }
            }
        }


class ReportSummary(BaseModel):
    """Report summary model (privacy-filtered)"""
    id: int
    company: str
    year: int
    period: str
    course: str
    activities_summary: Optional[str] = None
    technologies: Optional[List[str]] = None
    relevance_score: Optional[float] = None


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[ReportSummary]
    total_count: int
    query_interpretation: Optional[str] = None


class StatsRequest(BaseModel):
    """Statistics request model"""
    metric: str = Field(..., description="Type of statistic to retrieve")
    filters: Optional[Dict[str, Any]] = None
    group_by: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric": "top_technologies",
                "filters": {
                    "year": 2025,
                    "course": "Engenharia de Computação"
                },
                "group_by": "period"
            }
        }


class StatsResponse(BaseModel):
    """Statistics response model"""
    metric: str
    data: Dict[str, Any]
    period: Optional[str] = None
    total_reports: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric": "top_technologies",
                "data": {
                    "Python": 30,
                    "JavaScript": 25,
                    "Java": 20,
                    "SQL": 18,
                    "React": 15
                },
                "period": "2025",
                "total_reports": 74
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Authentication Schemas

class MagicLinkRequest(BaseModel):
    """Request for magic link"""
    email: EmailStr = Field(..., description="Email address (must be @usp.br domain)")
    
    @validator('email')
    def validate_usp_email(cls, v):
        if not v.endswith('@usp.br'):
            raise ValueError('Email must be from @usp.br domain')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "joao.silva@usp.br"
            }
        }


class MagicLinkResponse(BaseModel):
    """Magic link response"""
    message: str
    email: str
    expires_in_minutes: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Magic link enviado para seu email",
                "email": "joao.silva@usp.br",
                "expires_in_minutes": 15
            }
        }


class VerifyTokenRequest(BaseModel):
    """Verify magic token request"""
    token: str = Field(..., description="Magic token from email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456ghi789"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserResponse"
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "email": "joao.silva@usp.br",
                    "full_name": "João Silva",
                    "is_active": True,
                    "created_at": "2025-01-01T00:00:00Z"
                }
            }
        }


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "joao.silva@usp.br",
                "full_name": "João Silva",
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "last_login": "2025-01-01T12:00:00Z"
            }
        }


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    full_name: Optional[str] = None
    
    @validator('email')
    def validate_usp_email(cls, v):
        if not v.endswith('@usp.br'):
            raise ValueError('Email must be from @usp.br domain')
        return v


class CurrentUser(BaseModel):
    """Current authenticated user"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
