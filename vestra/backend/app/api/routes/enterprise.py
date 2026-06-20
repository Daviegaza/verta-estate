"""
Enterprise API routes — API key management, webhooks, usage analytics, metrics.
For B2B clients: banks, SACCOs, insurers paying KES 25K-150K/month.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.api_key_service import (
    create_api_key, get_user_keys, revoke_api_key, get_api_key_usage,
    validate_api_key, record_api_key_usage,
)
from app.services.webhook_service import (
    register_webhook, get_user_webhooks, delete_webhook,
)

router = APIRouter(prefix="/enterprise", tags=["Enterprise API"])


# ── API Key Validation & Tracking Dependency ───────────────────────────────────


async def resolve_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency: validates an API key from the X-API-Key header.
    Tracks usage and enforces rate limits per key.
    Raises 401 if the key is missing, invalid, or expired.
    Raises 429 if the key's rate limit is exceeded.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "api_key_required", "message": "Provide an API key via the X-API-Key header."},
        )

    key = await validate_api_key(db, x_api_key)
    if not key:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key", "message": "Invalid or expired API key."},
        )

    # Record usage
    await record_api_key_usage(db, key.id, endpoint=request.url.path, response_status=200, response_time_ms=0.0)

    # Enforce rate limits
    from app.core.redis import RedisRateLimiter
    limiter = RedisRateLimiter(max_requests=key.rate_limit_per_min, window_seconds=60)
    allowed = await limiter.is_allowed(f"api_key:{key.id}")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limit_exceeded", "message": f"Max {key.rate_limit_per_min} req/min exceeded."},
        )

    request.state.api_key = key
    return key


# ── API Keys ─────────────────────────────────────────────────────────────────

@router.post("/keys")
async def create_key(
    name: str = Query(..., description="Key name e.g. 'SACCO Integration'"),
    scopes: str = Query("read:properties,read:verifications", description="Comma-separated scopes"),
    rate_limit: int = Query(60, description="Requests per minute"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. THE RAW KEY IS ONLY SHOWN ONCE."""
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]

    api_key, raw_key = await create_api_key(
        db=db,
        user_id=current_user.id,
        name=name,
        scopes=scope_list,
        rate_limit_per_min=rate_limit,
    )

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # SHOWN ONLY ONCE — store it now!
        "prefix": api_key.key_prefix,
        "scopes": api_key.scopes,
        "rate_limit_per_min": api_key.rate_limit_per_min,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "message": "⚠️ Store this key securely. It will NOT be shown again.",
    }


@router.get("/keys")
async def list_keys(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys (prefixes only)."""
    keys = await get_user_keys(db, current_user.id)
    return {
        "total": len(keys),
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "rate_limit_per_min": k.rate_limit_per_min,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ],
    }


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    key = await revoke_api_key(db, key_id, current_user.id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": f"API key '{key.name}' revoked", "id": key_id}


@router.get("/usage")
async def api_usage(
    days: int = Query(30, ge=1, le=90),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get API key usage analytics."""
    return await get_api_key_usage(db, current_user.id, days)


# ── Metrics ──────────────────────────────────────────────────────────────────


@router.get("/metrics")
async def enterprise_metrics(
    days: int = Query(30, ge=1, le=90),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enterprise API usage metrics per key with total request counts."""
    result = await get_api_key_usage(db, current_user.id, days)

    # Enrich with total request counts per key
    for key_data in result.get("keys", []):
        daily = key_data.get("daily_usage", {})
        key_data["total_requests"] = sum(
            int(v) for v in daily.values() if isinstance(v, (int, float))
        )
        key_data["average_daily"] = round(
            key_data["total_requests"] / max(len(daily), 1), 1
        )

    result["total_requests"] = sum(
        k.get("total_requests", 0) for k in result.get("keys", [])
    )
    return result


# ── Webhooks ────────────────────────────────────────────────────────────────

@router.post("/webhooks")
async def create_webhook(
    url: str = Query(..., description="Your webhook URL"),
    events: str = Query("property.created,verification.completed", description="Comma-separated events"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a webhook endpoint to receive real-time events."""
    event_list = [e.strip() for e in events.split(",") if e.strip()]
    webhook = await register_webhook(db, current_user.id, url, event_list)
    return {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "secret": webhook.secret,
        "message": "Webhook registered. Use the secret to verify incoming signatures.",
    }


@router.get("/webhooks")
async def list_webhooks(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered webhooks."""
    hooks = await get_user_webhooks(db, current_user.id)
    return {
        "total": len(hooks),
        "webhooks": [
            {
                "id": h.id, "url": h.url, "events": h.events,
                "is_active": h.is_active, "failures": h.failures,
                "last_success": h.last_success_at.isoformat() if h.last_success_at else None,
            }
            for h in hooks
        ],
    }


@router.delete("/webhooks/{webhook_id}")
async def remove_webhook(
    webhook_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a webhook registration."""
    ok = await delete_webhook(db, webhook_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook removed", "id": webhook_id}
