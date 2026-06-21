"""Messaging API routes — buyer-seller-agent communication."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.messaging_service import (
    count_unread_messages,
    get_conversation,
    get_inbox,
    mark_message_read,
    send_message,
)

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/")
async def send_message_endpoint(
    receiver_id: int,
    body: str,
    property_id: int | None = None,
    subject: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to another user."""
    if receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    msg = await send_message(
        db=db,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        body=body,
        property_id=property_id,
        subject=subject,
    )
    return {
        "message_id": msg.id,
        "receiver_id": msg.receiver_id,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.get("/inbox")
async def inbox(
    limit: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation list (inbox)."""
    conversations = await get_inbox(db, current_user.id, limit)
    unread = await count_unread_messages(db, current_user.id)
    return {"unread_count": unread, "conversations": conversations}


@router.get("/conversation/{other_user_id}")
async def conversation(
    other_user_id: int,
    property_id: int | None = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages between current user and another user."""
    msgs = await get_conversation(db, current_user.id, other_user_id, property_id, limit)
    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "body": m.body,
                "is_read": m.is_read,
                "property_id": m.property_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in reversed(msgs)  # Oldest first for chat view
        ],
    }


@router.put("/{message_id}/read")
async def read_message(
    message_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a message as read."""
    msg = await mark_message_read(db, message_id, current_user.id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Marked as read"}
