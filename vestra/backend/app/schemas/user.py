from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    password: str
    role: UserRole = UserRole.buyer
    turnstile_token: Optional[str] = None  # Cloudflare Turnstile CAPTCHA token
    referral_code: Optional[str] = None  # Referral code from another user

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not v.startswith("+"):
            raise ValueError("Phone must start with country code e.g. +254...")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str]
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    is_kyc_verified: bool = False
    avatar_url: Optional[str]
    location: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("is_kyc_verified", mode="before")
    @classmethod
    def coerce_none_to_false(cls, v):
        return False if v is None else v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AgentProfileCreate(BaseModel):
    agency_name: Optional[str] = None
    license_number: Optional[str] = None
    years_experience: int = 0
    specialization: list[str] = []


class AgentProfileResponse(BaseModel):
    id: int
    agency_name: Optional[str]
    license_number: Optional[str]
    years_experience: int
    badge_level: Optional[str]
    total_listings: int
    successful_deals: int
    rating: float
    subscription_tier: str

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
