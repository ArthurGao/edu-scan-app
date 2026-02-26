from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    nickname: Optional[str] = Field(None, max_length=50)
    grade_level: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    grade_level: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
