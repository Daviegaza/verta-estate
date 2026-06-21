"""
Notification Service — multi-channel notifications (in-app, email, WhatsApp, SMS).
Includes lifecycle automated notification triggers.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_

from app.models.kyc_notification import Notification

logger = logging.getLogger("vestra")


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    body: Optional[str] = None,
    data: Optional[dict] = None,
    channel: str = "in_app",
) -> Notification:
    """Create an in-app notification and push it via WebSocket."""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data=data or {},
        channel=channel,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # ── Push to WebSocket ───────────────────────────────────────────────────
    try:
        from app.core.websocket import manager as ws_manager

        await ws_manager.broadcast_to_user(
            user_id,
            {
                "type": "notification",
                "payload": {
                    "id": notification.id,
                    "type": notification.type,
                    "title": notification.title,
                    "body": notification.body,
                    "data": notification.data,
                    "is_read": notification.is_read,
                    "created_at": (
                        notification.created_at.isoformat()
                        if notification.created_at
                        else None
                    ),
                },
            },
        )
    except Exception:
        logger.debug(
            '{"event":"ws_push_failed","notification_id":%d,"user_id":%d}',
            notification.id,
            user_id,
        )

    return notification


async def get_user_notifications(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
    unread_only: bool = False,
) -> list[Notification]:
    """Get notifications for a user, newest first."""
    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.is_read == False)
    result = await db.execute(query)
    return result.scalars().all()


async def mark_notification_read(
    db: AsyncSession, notification_id: int, user_id: int
) -> Optional[Notification]:
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification:
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    """Mark all notifications as read for a user. Returns count updated."""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount


async def count_unread(db: AsyncSession, user_id: int) -> int:
    """Count unread notifications for a user."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    return result.scalar_one()


# ═══════════════════════════════════════════════════════════════════════════════
# Lifecycle Notifications
# ═══════════════════════════════════════════════════════════════════════════════


async def send_welcome_notification(
    db: AsyncSession,
    user_id: int,
    full_name: str,
) -> Notification:
    """Send welcome notification after successful registration."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="welcome",
        title=f"Welcome to Vestra, {full_name}!",
        body="Your account is ready. Verify your email to get started with Africa's most trusted property platform.",
        data={"action": "verify_email"},
    )


async def send_complete_profile_reminder(
    db: AsyncSession,
    user_id: int,
    full_name: str,
) -> Notification:
    """Send 'Complete your profile' reminder 24 hours after registration."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="profile_reminder",
        title="Complete Your Profile",
        body=f"Hi {full_name}, complete your profile to get the most out of Vestra. Add your phone number, location, and profile picture.",
        data={"action": "complete_profile"},
    )


async def send_verify_property_prompt(
    db: AsyncSession,
    user_id: int,
    property_id: int,
    property_title: str,
) -> Notification:
    """Prompt user to verify their property after listing creation."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="verify_property_prompt",
        title="Verify Your Property",
        body=f"Your listing '{property_title}' is live! Verify it with AI to get a Trust Score badge and increase buyer confidence by up to 73%.",
        data={"property_id": property_id, "action": "verify_property"},
    )


async def send_payment_receipt(
    db: AsyncSession,
    user_id: int,
    payment_id: int,
    amount_kes: float,
    purpose: str,
    mpesa_receipt: Optional[str] = None,
) -> Notification:
    """Send payment receipt notification after successful payment."""
    purpose_label = purpose.replace("_", " ").title() if purpose else "Payment"
    body = f"Your {purpose_label} of KES {amount_kes:,.0f} was successful."
    if mpesa_receipt:
        body += f" M-Pesa Receipt: {mpesa_receipt}"

    return await create_notification(
        db=db,
        user_id=user_id,
        type="payment_receipt",
        title="Payment Successful",
        body=body,
        data={"payment_id": payment_id, "amount_kes": amount_kes, "mpesa_receipt": mpesa_receipt},
    )


async def send_subscription_expiring_warning(
    db: AsyncSession,
    user_id: int,
    tier: str,
    days_remaining: int,
    amount_kes: float,
) -> Notification:
    """Send warning that subscription is expiring soon (3 days before)."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="subscription_expiring",
        title="Subscription Expiring Soon",
        body=f"Your {tier.title()} subscription will expire in {days_remaining} days. Renew at KES {amount_kes:,.0f}/month to keep your listings active and access premium features.",
        data={"tier": tier, "days_remaining": days_remaining, "amount_kes": amount_kes, "action": "renew_subscription"},
    )


async def send_subscription_expired(
    db: AsyncSession,
    user_id: int,
    tier: str,
) -> Notification:
    """Send notification that subscription has expired."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="subscription_expired",
        title="Subscription Expired",
        body=f"Your {tier.title()} subscription has expired. Your listings may be hidden and premium features are disabled. Renew now to reactivate.",
        data={"tier": tier, "action": "renew_subscription"},
    )


async def send_rent_due_notification(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    unit_name: str,
    amount_kes: float,
    due_date: str,
) -> Notification:
    """Notify tenant that rent is due."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="rent_due",
        title="Rent Payment Due",
        body=f"Your rent of KES {amount_kes:,.0f} for {unit_name} is due on {due_date}. Pay via M-Pesa to avoid late fees.",
        data={"tenant_id": tenant_id, "amount_kes": amount_kes, "due_date": due_date, "action": "pay_rent"},
    )


async def send_rent_overdue_notification(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    unit_name: str,
    amount_kes: float,
    days_overdue: int,
) -> Notification:
    """Notify tenant that rent is overdue."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="rent_overdue",
        title="Rent Overdue",
        body=f"Your rent of KES {amount_kes:,.0f} for {unit_name} is {days_overdue} days overdue. Please pay immediately to avoid penalties.",
        data={"tenant_id": tenant_id, "amount_kes": amount_kes, "days_overdue": days_overdue, "action": "pay_rent"},
    )


async def send_agent_badge_expiring_warning(
    db: AsyncSession,
    user_id: int,
    badge_level: str,
    days_remaining: int,
) -> Notification:
    """Notify agent that their verification badge is expiring soon."""
    badge_display = badge_level.title() if badge_level else "Verified"
    return await create_notification(
        db=db,
        user_id=user_id,
        type="badge_expiring",
        title=f"{badge_display} Badge Expiring Soon",
        body=f"Your {badge_display} Agent Badge will expire in {days_remaining} days. Renew your subscription to keep your badge and maintain client trust.",
        data={"badge_level": badge_level, "days_remaining": days_remaining, "action": "renew_subscription"},
    )


async def send_verification_complete_notification(
    db: AsyncSession,
    user_id: int,
    property_id: int,
    property_title: str,
    trust_score: float,
) -> Notification:
    """Notify user that verification is complete."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="verification_complete",
        title="Verification Complete",
        body=f"Your property '{property_title}' has been verified with a Trust Score of {trust_score:.0f}/100.",
        data={"property_id": property_id, "trust_score": trust_score},
    )


async def send_referral_converted_notification(
    db: AsyncSession,
    user_id: int,
    referred_name: str,
    reward_kes: float,
) -> Notification:
    """Notify referrer that their referral made a payment (converted)."""
    return await create_notification(
        db=db,
        user_id=user_id,
        type="referral_converted",
        title="Referral Converted!",
        body=f"Great news! {referred_name} just made their first payment. You earned KES {reward_kes:,.0f} in referral rewards.",
        data={"referred_name": referred_name, "reward_kes": reward_kes, "action": "view_referrals"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Background fire-and-forget wrappers
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# Scheduled Lifecycle Triggers (call from cron or task queue)
# ═══════════════════════════════════════════════════════════════════════════════


async def send_complete_profile_reminders(db: AsyncSession) -> list[dict]:
    """
    Find users who registered ~24h ago but haven't completed their profile
    (no phone, no location) and send them a reminder notification.

    Call from scheduler / cron every hour.
    """
    from app.models.user import User

    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)
    twenty_five_hours_ago = now - timedelta(hours=25)

    result = await db.execute(
        select(User).where(
            User.created_at >= twenty_five_hours_ago,
            User.created_at <= twenty_four_hours_ago,
            (User.phone.is_(None)) | (User.location.is_(None)),
        )
    )
    users_needing_reminder = result.scalars().all()

    sent = []
    for user in users_needing_reminder:
        try:
            await send_complete_profile_reminder(
                db=db,
                user_id=user.id,
                full_name=user.full_name,
            )
            sent.append({"user_id": user.id, "email": user.email})
        except Exception:
            logger.warning(
                '{"event":"profile_reminder_failed","user_id":%d}',
                user.id,
            )

    if sent:
        logger.info(
            '{"event":"profile_reminders_sent","count":%d}',
            len(sent),
        )

    return sent


async def _bg_create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """Fire-and-forget notification creation with own DB session."""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await create_notification(
                db=db, user_id=user_id, type=notification_type,
                title=title, body=body, data=data or {},
            )
    except Exception:
        logger.warning(
            '{"event":"bg_notification_failed","type":"%s","user_id":%d}',
            notification_type, user_id, exc_info=True,
        )
