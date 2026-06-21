from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    full_name: str
    password: str
    role: UserRole = UserRole.buyer
    turnstile_token: str | None = None  # Cloudflare Turnstile CAPTCHA token
    referral_code: str | None = None  # Referral code from another user

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
    phone: str | None
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    is_kyc_verified: bool = False
    avatar_url: str | None
    location: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("is_kyc_verified", mode="before")
    @classmethod
    def coerce_none_to_false(cls, v):
        return False if v is None else v


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AgentProfileCreate(BaseModel):
    agency_name: str | None = None
    license_number: str | None = None
    years_experience: int = 0
    specialization: list[str] = []


class AgentProfileResponse(BaseModel):
    id: int
    agency_name: str | None
    license_number: str | None
    years_experience: int
    badge_level: str | None
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
