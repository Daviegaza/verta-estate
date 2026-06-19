"""
API Key Service — Enterprise API access management.
Generates, validates, and tracks API keys for B2B clients (banks, SACCOs, insurers).
Keys are SHA-256 hashed; only the prefix and full key are shown once at creation.
"""
from __future__ import annotations

import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.enterprise import APIKey

logger = logging.getLogger("vestra")

KEY_PREFIX = "vsk_"  # Vestra Secret Key prefix


async def create_api_key(
    db: AsyncSession,
    user_id: int,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_per_min: int = 60,
    expires_in_days: int | None = 365,
) -> tuple[APIKey, str]:
    """
    Create a new API key. Returns (api_key_record, raw_key).
    The raw_key is only shown once — store it securely on the client side.
    """
    # Generate a cryptographically secure random key
    raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]  # First 12 chars for display: "vsk_aB3xY7..."

    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    api_key = APIKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes or ["read:properties", "read:verifications"],
        rate_limit_per_min=rate_limit_per_min,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info('{"event":"api_key_created","user_id":%d,"name":"%s","prefix":"%s"}',
                user_id, name, key_prefix)
    return api_key, raw_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[APIKey]:
    """
    Validate an API key. Returns the APIKey record if valid, None otherwise.
    Used as a FastAPI dependency for enterprise endpoints.
    """
    if not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None

    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return api_key


async def record_api_key_usage(
    db: AsyncSession,
    api_key_id: int,
    endpoint: str,
    response_status: int,
    response_time_ms: float,
) -> None:
    """Record API key usage for analytics."""
    # Track in Redis for real-time rate limiting and analytics
    from app.core.redis import get_redis
    r = await get_redis()
    if r is not None:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await r.hincrby(f"vestra:api_usage:{api_key_id}:{today}", endpoint, 1)
            await r.expire(f"vestra:api_usage:{api_key_id}:{today}", 86400 * 7)
        except Exception:
            pass


async def get_user_keys(db: AsyncSession, user_id: int) -> list[APIKey]:
    """List all API keys for a user (prefixes only, no raw keys)."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == user_id)
        .order_by(APIKey.created_at.desc())
    )
    return result.scalars().all()


async def revoke_api_key(db: AsyncSession, key_id: int, user_id: int) -> Optional[APIKey]:
    """Revoke (deactivate) an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return None

    api_key.is_active = False
    await db.commit()
    logger.info('{"event":"api_key_revoked","key_id":%d,"user_id":%d}', key_id, user_id)
    return api_key


async def get_api_key_usage(
    db: AsyncSession, user_id: int, days: int = 30,
) -> dict:
    """Get API key usage analytics for a user."""
    from app.core.redis import get_redis
    r = await get_redis()

    # Get user's API keys
    keys = await get_user_keys(db, user_id)
    if not keys:
        return {"keys": [], "total_calls": 0, "daily_usage": []}

    usage_data = []
    total_calls = 0

    for key in keys:
        key_usage = {}
        if r is not None:
            for d in range(days):
                day = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
                try:
                    daily = await r.hgetall(f"vestra:api_usage:{key.id}:{day}")
                    key_usage[day] = sum(int(v) for v in daily.values())
                    total_calls += key_usage.get(day, 0)
                except Exception:
                    key_usage[day] = 0

        usage_data.append({
            "key_id": key.id,
            "name": key.name,
            "prefix": key.key_prefix,
            "scopes": key.scopes,
            "is_active": key.is_active,
            "last_used": key.last_used_at.isoformat() if key.last_used_at else None,
            "daily_usage": key_usage,
        })

    return {
        "keys": usage_data,
        "total_calls": total_calls,
        "period_days": days,
    }
