"""
Messaging Service — buyer-seller-agent communication within the platform.
"""
from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update

from app.models.kyc_notification import Message

logger = logging.getLogger("vestra")


async def send_message(
    db: AsyncSession,
    sender_id: int,
    receiver_id: int,
    body: str,
    property_id: Optional[int] = None,
    subject: Optional[str] = None,
) -> Message:
    """Send a message from one user to another and push it via WebSocket."""
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        property_id=property_id,
        subject=subject,
        body=body,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # ── Push to WebSocket (receiver gets instant delivery) ──────────────────
    try:
        from app.core.websocket import manager as ws_manager

        payload = {
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "body": message.body,
            "property_id": message.property_id,
            "subject": message.subject,
            "is_read": message.is_read,
            "created_at": (
                message.created_at.isoformat() if message.created_at else None
            ),
        }
        await ws_manager.broadcast_to_user(
            receiver_id, {"type": "message", "payload": payload}
        )
        # Also push to sender so their open conversation window updates
        await ws_manager.broadcast_to_user(
            sender_id, {"type": "message", "payload": payload}
        )
    except Exception:
        logger.debug(
            '{"event":"ws_push_failed","message_id":%d,"receiver_id":%d}',
            message.id,
            receiver_id,
        )

    return message


async def get_conversation(
    db: AsyncSession,
    user_id: int,
    other_user_id: int,
    property_id: Optional[int] = None,
    limit: int = 50,
) -> list[Message]:
    """Get messages between two users, newest first."""
    query = (
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == user_id),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if property_id:
        query = query.where(Message.property_id == property_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_inbox(
    db: AsyncSession,
    user_id: int,
    limit: int = 30,
) -> list[dict]:
    """Get conversation list — last message from each conversation partner."""
    # Get distinct conversation partners
    sent = (
        select(Message.receiver_id.label("other_id"), Message.created_at)
        .where(Message.sender_id == user_id)
    )
    received = (
        select(Message.sender_id.label("other_id"), Message.created_at)
        .where(Message.receiver_id == user_id)
    )
    # Get most recent message per conversation
    from sqlalchemy import union_all, text
    all_msgs = union_all(sent, received).alias("all_msgs")

    result = await db.execute(
        select(Message)
        .where(
            or_(
                Message.sender_id == user_id,
                Message.receiver_id == user_id,
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit * 3)  # Overfetch to dedupe
    )
    messages = result.scalars().all()

    # Deduplicate by conversation partner
    seen = set()
    conversations = []
    for msg in messages:
        other_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
        pair_key = f"{min(user_id, other_id)}-{max(user_id, other_id)}"
        if pair_key not in seen:
            seen.add(pair_key)
            conversations.append({
                "message_id": msg.id,
                "other_user_id": other_id,
                "property_id": msg.property_id,
                "subject": msg.subject,
                "last_message": msg.body[:200],
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })

    return conversations


async def mark_message_read(
    db: AsyncSession, message_id: int, user_id: int
) -> Optional[Message]:
    """Mark a message as read (only by the receiver)."""
    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.receiver_id == user_id,
        )
    )
    message = result.scalar_one_or_none()
    if message:
        message.is_read = True
        await db.commit()
        await db.refresh(message)
    return message


async def count_unread_messages(db: AsyncSession, user_id: int) -> int:
    """Count unread messages for a user."""
    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.receiver_id == user_id,
            Message.is_read == False,
        )
    )
    return result.scalar_one()
