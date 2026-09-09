"""
Pydantic schemas for authentication endpoints.
password_hash is intentionally excluded from all response models.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Request body for POST /auth/register."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    username: str
    password: str


# Backward compatibility alias
UserLogin = LoginRequest


class UserResponse(BaseModel):
    """Safe user representation — never includes password_hash."""
    id: int
    username: str
    email: str
    name: Optional[str] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response body for a successful login."""
    access_token: str
    token_type: str = "bearer"
