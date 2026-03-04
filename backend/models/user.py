"""
User model for authentication and user management
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import uuid4


class User(BaseModel):
    """User document model"""
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    is_verified: bool = False
    role: Literal["user", "admin"] = "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "is_verified": True,
                "role": "user",
                "created_at": "2026-03-05T10:00:00",
                "updated_at": "2026-03-05T10:00:00"
            }
        }


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr


class UserResponse(BaseModel):
    """Schema for user API responses"""
    user_id: str
    email: str
    role: str
    is_verified: bool
    created_at: datetime


class OTPSession(BaseModel):
    """OTP session stored in Redis"""
    email: EmailStr
    hashed_otp: str
    attempts: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OTPRequest(BaseModel):
    """Schema for OTP request"""
    email: EmailStr


class OTPVerify(BaseModel):
    """Schema for OTP verification"""
    email: EmailStr
    otp: str


class TokenResponse(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
