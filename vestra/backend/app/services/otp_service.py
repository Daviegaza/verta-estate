"""
OTP Service — phone number authentication via WhatsApp/SMS.
Simple, Kenya-friendly auth: enter phone → get code → verify → done.
"""
from __future__ import annotations

import logging
import random
import string
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.redis import cache_delete, cache_get, cache_set

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

OTP_LENGTH = 6
OTP_TTL = 600  # 10 minutes
OTP_COOLDOWN = 60  # 1 minute between resends
MAX_ATTEMPTS = 5


def generate_otp() -> str:
    """Generate a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))


async def send_otp(phone: str) -> dict:
    """
    Generate and send OTP to phone number via WhatsApp.
    In development, OTP is always '123456' for testing.
    Returns status info.
    """
    from app.core.config import settings

    # Normalize phone to 254 format
    phone = _normalize_phone(phone)

    # Check cooldown
    cooldown_key = f"vestra:otp:cooldown:{phone}"
    if await cache_get(cooldown_key):
        return {"success": False, "message": "Please wait 1 minute before requesting a new code"}

    otp = generate_otp()

    # In development, use fixed OTP for easy testing
    if settings.ENVIRONMENT == "development":
        otp = "123456"

    # Store OTP in Redis with TTL
    key = f"vestra:otp:{phone}"
    await cache_set(key, {
        "code": otp,
        "attempts": 0,
        "created_at": datetime.now(UTC).isoformat(),
    }, ttl=OTP_TTL)

    # Set cooldown
    await cache_set(cooldown_key, "1", ttl=OTP_COOLDOWN)

    # Send via WhatsApp if configured
    if settings.WHATSAPP_ACCESS_TOKEN:
        try:
            from app.services.whatsapp_service import send_template_message
            await send_template_message(
                to_phone=phone,
                template_name="vestra_otp",
                language="en",
                parameters=[otp],
            )
        except Exception as e:
            logger.warning('{"event":"otp_whatsapp_failed","phone":"%s","error":"%s"}', phone[-4:], str(e))
    else:
        # Log OTP in dev (so developer can see it)
        logger.info('{"event":"otp_generated","phone":"%s","otp":"%s","dev":true}', phone[-4:], otp)

    return {"success": True, "message": f"Verification code sent to {phone[-4:]}"}


async def verify_otp(phone: str, code: str) -> dict:
    """
    Verify OTP code. Returns user data if valid.
    If user doesn't exist, returns {"new_user": true} so frontend can collect name.
    """
    from app.core.config import settings

    phone = _normalize_phone(phone)

    # Dev shortcut: any 6-digit code starting with 123 works in development
    is_dev_override = settings.ENVIRONMENT == "development" and code == "123456"

    key = f"vestra:otp:{phone}"
    data = await cache_get(key)

    if not data and not is_dev_override:
        return {"success": False, "message": "Code expired or not requested. Please request a new code."}

    if not is_dev_override:
        attempts = data.get("attempts", 0)
        if attempts >= MAX_ATTEMPTS:
            await cache_delete(key)
            return {"success": False, "message": "Too many attempts. Please request a new code."}

        if data.get("code") != code:
            data["attempts"] = attempts + 1
            ttl = OTP_TTL - 60  # Approximate remaining TTL
            await cache_set(key, data, ttl=max(ttl, 60))
            remaining = MAX_ATTEMPTS - data["attempts"]
            return {"success": False, "message": f"Invalid code. {remaining} attempts remaining."}

    # OTP verified — clean up
    await cache_delete(key)
    await cache_delete(f"vestra:otp:cooldown:{phone}")

    return {"success": True, "verified": True, "phone": phone}


async def get_or_create_user_by_phone(db: AsyncSession, phone: str, full_name: str | None = None) -> tuple:
    """
    Find existing user by phone or create a new one.
    Returns (user, is_new).
    All new users start as 'buyer' role (browse-only, no dashboard).
    """
    from sqlalchemy import select

    from app.models.user import User, UserRole

    phone = _normalize_phone(phone)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        is_new = True
        user = User(
            email=f"{phone}@vestra.user",  # Placeholder email
            phone=phone,
            full_name=full_name or f"User_{phone[-4:]}",
            hashed_password="",  # No password — OTP only
            role=UserRole.buyer,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user, is_new


def _normalize_phone(phone: str) -> str:
    """Normalize phone to 254XXXXXXXXX format."""
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not phone.startswith("254"):
        phone = "254" + phone
    return phone
