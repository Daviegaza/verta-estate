"""
Event Bus — central event emitter for the VESTRA platform.
Fires notifications and webhooks after key business events.

Durable: uses Redis Streams for reliable delivery with retry and dead-letter.
Falls back to asyncio.create_task when Redis is unavailable (graceful degradation).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# ── Event type constants (match WebhookEvent enum values) ──────────────────
EVENT_PAYMENT_COMPLETED = "payment.completed"
EVENT_VERIFICATION_COMPLETED = "verification.completed"
EVENT_SUBSCRIPTION_CREATED = "subscription.created"
EVENT_ESCROW_COMPLETED = "escrow.completed"
EVENT_DISPUTE_FILED = "dispute.filed"
EVENT_REFERRAL_REWARDED = "referral.rewarded"
EVENT_PROPERTY_VERIFIED = "property.verified"
EVENT_RENTAL_PAYMENT_DUE = "rental.payment_due"
EVENT_PAYOUT_PROCESSED = "payout.processed"

# ── Notification mapping: event_type -> (title_template, body_template) ───
_NOTIFICATION_TEMPLATES = {
    EVENT_PAYMENT_COMPLETED: (
        "Payment Successful",
        "Your payment of KES {amount} has been completed successfully.",
    ),
    EVENT_VERIFICATION_COMPLETED: (
        "Verification Complete",
        "Your property '{property_title}' has been verified with a Trust Score of {trust_score}/100.",
    ),
    EVENT_SUBSCRIPTION_CREATED: (
        "Subscription Activated",
        "Your {tier} subscription is now active. Welcome to Vestra!",
    ),
    EVENT_ESCROW_COMPLETED: (
        "Escrow Released",
        "Escrow for property '{property_title}' has been completed. Funds released to seller.",
    ),
    EVENT_DISPUTE_FILED: (
        "Dispute Filed",
        "Your dispute (category: {category}) has been received and is under review.",
    ),
    EVENT_REFERRAL_REWARDED: (
        "Referral Reward Earned!",
        "You earned KES {reward_kes} for referring a friend. Keep sharing Vestra!",
    ),
    EVENT_PROPERTY_VERIFIED: (
        "Property Verified",
        "Your property '{property_title}' has been verified successfully.",
    ),
    EVENT_RENTAL_PAYMENT_DUE: (
        "Rent Payment Due",
        "Your rent of KES {amount} for {unit_name} is due on {due_date}.",
    ),
    EVENT_PAYOUT_PROCESSED: (
        "Payout Processed",
        "Your payout of KES {amount} has been processed successfully.",
    ),
}


def _format_notification(event_type: str, data: dict) -> tuple[str, str]:
    """Format notification title and body from event data."""
    templates = _NOTIFICATION_TEMPLATES.get(event_type)
    if not templates:
        # Fallback for unknown event types
        return f"Event: {event_type}", str(data)
    title_tpl, body_tpl = templates
    try:
        title = title_tpl.format(**data)
    except (KeyError, ValueError):
        title = title_tpl
    try:
        body = body_tpl.format(**data)
    except (KeyError, ValueError):
        body = body_tpl
    return title, body


async def emit_event(
    event_type: str,
    user_id: int,
    data: dict,
    db: AsyncSession | None = None,
) -> None:
    """
    Central event emitter. Called after key business events.

    Enqueues a notification task + webhook delivery onto the Redis Stream
    for durable, retryable processing. Falls back to asyncio.create_task
    when Redis is unavailable.

    Args:
        db: Database session (from the caller's request context).
        event_type: Dot-notation event type matching WebhookEvent enum.
        user_id: The user to notify.
        data: Event payload dict used for notification formatting and webhook body.
    """
    from app.core.task_queue import enqueue

    title, body = _format_notification(event_type, data)

    # ── Enqueue notification (durable, via Redis Streams) ─────────────────
    notification_enqueued = await enqueue(
        "notification",
        {"user_id": user_id, "type": event_type, "title": title, "body": body, "data": data},
    )

    # ── Enqueue webhook delivery (durable) ────────────────────────────────
    webhook_enqueued = await enqueue(
        "webhook",
        {"event": event_type, "data": data},
    )

    # ── Fallback to fire-and-forget if Redis is down ──────────────────────
    if not notification_enqueued:
        asyncio.create_task(
            _create_notification_background(event_type, user_id, data)
        )
    if not webhook_enqueued:
        asyncio.create_task(
            _trigger_webhooks_background(event_type, data)
        )

    logger.info(
        '{"event":"bus_event","type":"%s","user_id":%d,"durable":%s}',
        event_type,
        user_id,
        "redis_stream" if (notification_enqueued or webhook_enqueued) else "fire_and_forget",
    )


async def _create_notification_background(
    event_type: str,
    user_id: int,
    data: dict,
) -> None:
    """Create a notification record in a background task with its own DB session."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import create_notification

    try:
        async with AsyncSessionLocal() as bg_db:
            title, body = _format_notification(event_type, data)
            await create_notification(
                db=bg_db,
                user_id=user_id,
                type=event_type,
                title=title,
                body=body,
                data=data,
            )
    except Exception as e:
        logger.warning(
            '{"event":"bus_notification_failed","type":"%s","user_id":%d,"error":"%s"}',
            event_type, user_id, str(e)[:100],
        )


async def _trigger_webhooks_background(
    event_type: str,
    data: dict,
) -> None:
    """Deliver webhooks in a background task with its own DB session."""
    from app.core.database import AsyncSessionLocal
    from app.services.webhook_service import trigger_webhook

    try:
        async with AsyncSessionLocal() as bg_db:
            results = await trigger_webhook(event=event_type, data=data, db=bg_db)
            if results:
                logger.info(
                    '{"event":"bus_webhooks_delivered","type":"%s","count":%d}',
                    event_type, len(results),
                )
    except Exception as e:
        logger.warning(
            '{"event":"bus_webhook_trigger_failed","type":"%s","error":"%s"}',
            event_type, str(e)[:100],
        )
