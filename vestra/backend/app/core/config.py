from pydantic_settings import BaseSettings
from typing import List
import os
import secrets


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vestra"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_RECYCLE: int = 3600

    # ── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 50

    # ── Auth ────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-64-char-minimum-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60       # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── M-Pesa ──────────────────────────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = "174379"
    MPESA_PASSKEY: str = ""
    MPESA_CALLBACK_URL: str = "https://yourdomain.com/api/payments/mpesa/callback"
    MPESA_ENV: str = "sandbox"

    # ── Stripe ──────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── Email ───────────────────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@vestra.co.ke"
    SMTP_FROM_NAME: str = "Vestra"

    # ── WhatsApp Business API ───────────────────────────────────────────────
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_BUSINESS_ID: str = ""
    WHATSAPP_APP_SECRET: str = ""

    # ── Uploads ─────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_MIME_TYPES: List[str] = [
        "application/pdf", "image/jpeg", "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    # ── Rate Limiting ───────────────────────────────────────────────────────
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_GENERAL_PER_MINUTE: int = 120
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 300

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Vestra"
    APP_VERSION: str = "2.0.0"
    BASE_URL: str = "http://localhost:3000"  # Public-facing URL for links in emails etc.
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production
    CORS_ORIGINS: str = "http://localhost:3000"

    # ── CAPTCHA (Cloudflare Turnstile) ──────────────────────────────────────
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_SITE_KEY: str = ""

    # ── Account Lockout ─────────────────────────────────────────────────────
    ACCOUNT_LOCKOUT_MAX_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 15

    # ── Security ────────────────────────────────────────────────────────────
    CSP_ENABLED: bool = True
    CSRF_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()

# Validate critical settings on import
if settings.ENVIRONMENT == "production":
    assert settings.SECRET_KEY != "change-me-in-production-use-64-char-minimum-key", \
        "SECRET_KEY must be changed in production!"
    assert len(settings.SECRET_KEY) >= 32, \
        "SECRET_KEY must be at least 32 characters"
    assert not settings.DEBUG, "DEBUG must be False in production"
    assert settings.REDIS_PASSWORD, \
        "REDIS_PASSWORD must be set in production!"
    assert "ssl=require" in settings.DATABASE_URL or "ssl=verify-full" in settings.DATABASE_URL, \
        "DATABASE_URL must enforce SSL (add ?ssl=require) in production!"
    assert settings.TURNSTILE_SECRET_KEY, \
        "TURNSTILE_SECRET_KEY must be set in production for CAPTCHA!"
