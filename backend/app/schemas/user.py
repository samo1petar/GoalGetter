"""
Pydantic schemas for User-related requests and responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserSettings(BaseModel):
    """User settings schema."""
    meeting_duration: int = 30
    timezone: str = "UTC"
    email_notifications: bool = True


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a new user with email/password."""
    password: str = Field(..., min_length=8)


class UserGoogleAuth(BaseModel):
    """Schema for Google OAuth authentication."""
    code: str
    state: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    auth_provider: str
    profile_image: Optional[str] = None
    phase: str
    meeting_interval: int
    calendar_connected: bool
    created_at: str
    updated_at: str
    settings: UserSettings

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = None
    settings: Optional[UserSettings] = None


class UserPhaseUpdate(BaseModel):
    """Schema for updating user phase."""
    phase: str = Field(..., pattern="^(goal_setting|tracking)$")


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str
