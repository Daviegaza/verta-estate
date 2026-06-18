"""
Webhook Service — outbound event delivery for enterprise clients.
Registers webhook URLs, delivers events with HMAC signatures, retries on failure.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.enterprise import Webhook, WebhookEvent

logger = logging.getLogger("vestra")

MAX_RETRIES = 3
RETRY_DELAY_S = 5
TIMEOUT_S = 10


async def register_webhook(
    db: AsyncSession,
    user_id: int,
    url: str,
    events: list[str],
    secret: str | None = None,
) -> Webhook:
    """Register a new webhook endpoint for a user."""
    import secrets as _secrets

    webhook = Webhook(
        user_id=user_id,
        url=url,
        secret=secret or _secrets.token_urlsafe(32),
        events=events,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    logger.info('{"event":"webhook_registered","user_id":%d,"url":"%s"}', user_id, url)
    return webhook


async def get_user_webhooks(db: AsyncSession, user_id: int) -> list[Webhook]:
    """Get all webhooks for a user."""
    result = await db.execute(
        select(Webhook)
        .where(Webhook.user_id == user_id)
        .order_by(Webhook.created_at.desc())
    )
    return result.scalars().all()


async def delete_webhook(db: AsyncSession, webhook_id: int, user_id: int) -> bool:
    """Delete a webhook registration."""
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user_id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        return False
    await db.delete(wh)
    await db.commit()
    return True


async def trigger_webhook(
    event: str,
    data: dict,
    db: AsyncSession | None = None,
) -> list[dict]:
    """
    Trigger webhook deliveries for a specific event type.
    Sends signed POST requests to all registered webhooks listening for this event.
    Returns delivery results for each webhook.
    """
    if db is None:
        logger.warning('{"event":"webhook_trigger_no_db","event_type":"%s"}', event)
        return []

    result = await db.execute(
        select(Webhook).where(
            Webhook.is_active == True,
            Webhook.events.contains([event]),
        )
    )
    webhooks = result.scalars().all()

    if not webhooks:
        return []

    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    payload_bytes = json.dumps(payload, default=str).encode()

    deliveries = []
    for wh in webhooks:
        result = await _deliver_webhook(wh, payload_bytes, payload)
        deliveries.append(result)

    return deliveries


async def _deliver_webhook(
    webhook: Webhook,
    payload_bytes: bytes,
    payload: dict,
) -> dict:
    """Deliver a webhook event with HMAC signature and retries."""
    # Compute HMAC signature
    signature = hmac.new(
        webhook.secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Vestra-Event": payload["event"],
        "X-Vestra-Signature-256": f"sha256={signature}",
        "X-Vestra-Delivery-ID": hashlib.sha256(
            f"{webhook.id}:{payload['timestamp']}".encode()
        ).hexdigest()[:16],
        "User-Agent": "Vestra-Webhook/2.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_bytes,
                    headers=headers,
                )
                if response.status_code < 500:
                    # Success or client error — don't retry
                    if response.status_code >= 200 and response.status_code < 300:
                        webhook.last_success_at = datetime.now(timezone.utc)
                        webhook.failures = 0
                    else:
                        webhook.failures += 1

                    return {
                        "webhook_id": webhook.id,
                        "url": webhook.url,
                        "status": response.status_code,
                        "success": response.status_code < 300,
                        "attempt": attempt,
                    }
        except Exception as e:
            logger.warning(
                '{"event":"webhook_delivery_attempt_failed","webhook_id":%d,"attempt":%d,"error":"%s"}',
                webhook.id, attempt, str(e)[:100],
            )

        # Exponential backoff before retry
        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY_S * attempt)

    # All retries failed
    webhook.failures += 1
    return {
        "webhook_id": webhook.id,
        "url": webhook.url,
        "status": 0,
        "success": False,
        "attempt": MAX_RETRIES,
        "error": "All delivery attempts failed",
    }
