"""
Notification Service — multi-channel notifications (in-app, email, WhatsApp, SMS).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

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
    """Create an in-app notification."""
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
        data={"tenant_id": tenant_id, "amount_kes": amount_kes, "due_date": due_date},
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
