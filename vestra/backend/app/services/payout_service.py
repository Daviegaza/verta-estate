"""
Payout Service — agent commissions, landlord rent disbursements, and withdrawals.
Handles M-Pesa B2C payouts to Vestra users.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.enterprise import Payout, PayoutStatus

logger = logging.getLogger("vestra")


async def create_payout(
    db: AsyncSession,
    user_id: int,
    amount_kes: float,
    payout_type: str = "commission",
    reference_id: Optional[int] = None,
    reference_type: Optional[str] = None,
    mpesa_phone: Optional[str] = None,
    description: Optional[str] = None,
) -> Payout:
    """Create a payout request for a user."""
    payout = Payout(
        user_id=user_id,
        amount_kes=amount_kes,
        payout_type=payout_type,
        reference_id=reference_id,
        reference_type=reference_type,
        mpesa_phone=mpesa_phone,
        description=description,
        status=PayoutStatus.pending,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)

    logger.info(
        '{"event":"payout_created","id":%d,"user_id":%d,"amount":%s,"type":"%s"}',
        payout.id, user_id, amount_kes, payout_type,
    )
    return payout


async def process_payout(
    db: AsyncSession, payout_id: int,
) -> Optional[dict]:
    """
    Process a pending payout via M-Pesa B2C.
    In production, this calls Safaricom B2C API.
    Currently simulates the payout flow.
    """
    result = await db.execute(
        select(Payout).where(
            Payout.id == payout_id,
            Payout.status == PayoutStatus.pending,
        )
    )
    payout = result.scalar_one_or_none()
    if not payout:
        return None

    try:
        # In production: call M-Pesa B2C API here
        # from app.services.mpesa_service import initiate_b2c_payment
        # b2c_result = await initiate_b2c_payment(
        #     phone_number=payout.mpesa_phone,
        #     amount=payout.amount_kes,
        #     reference=f"PAYOUT-{payout.id}",
        # )

        payout.status = PayoutStatus.processing
        payout.processed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(payout)

        logger.info('{"event":"payout_processing","id":%d}', payout_id)
        return _serialize_payout(payout)

    except Exception as e:
        logger.error('{"event":"payout_failed","id":%d,"error":"%s"}', payout_id, str(e))
        payout.status = PayoutStatus.failed
        payout.failure_reason = str(e)[:500]
        await db.commit()
        return _serialize_payout(payout)


async def complete_payout(
    db: AsyncSession, payout_id: int, mpesa_receipt: str,
) -> Optional[dict]:
    """Mark a payout as completed after M-Pesa confirmation."""
    result = await db.execute(
        select(Payout).where(Payout.id == payout_id)
    )
    payout = result.scalar_one_or_none()
    if not payout:
        return None

    payout.status = PayoutStatus.completed
    payout.mpesa_receipt = mpesa_receipt
    payout.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(payout)

    from app.services.audit_service import log_action
    await log_action(
        db, payout.user_id, "payout.completed", "payout", payout_id,
        {"amount": float(payout.amount_kes), "receipt": mpesa_receipt},
    )

    logger.info(
        '{"event":"payout_completed","id":%d,"receipt":"%s"}', payout_id, mpesa_receipt,
    )
    return _serialize_payout(payout)


async def fail_payout(
    db: AsyncSession, payout_id: int, reason: str,
) -> Optional[dict]:
    """Mark a payout as failed."""
    result = await db.execute(
        select(Payout).where(Payout.id == payout_id)
    )
    payout = result.scalar_one_or_none()
    if not payout:
        return None

    payout.status = PayoutStatus.failed
    payout.failure_reason = reason[:500]

    await db.commit()
    await db.refresh(payout)

    logger.warning('{"event":"payout_failed","id":%d,"reason":"%s"}', payout_id, reason)
    return _serialize_payout(payout)


async def get_user_payouts(
    db: AsyncSession, user_id: int, limit: int = 50,
) -> list[dict]:
    """Get all payouts for a user."""
    result = await db.execute(
        select(Payout)
        .where(Payout.user_id == user_id)
        .order_by(Payout.created_at.desc())
        .limit(limit)
    )
    return [_serialize_payout(p) for p in result.scalars().all()]


async def get_pending_payouts(
    db: AsyncSession, limit: int = 50,
) -> list[dict]:
    """Get all pending payouts (admin view)."""
    result = await db.execute(
        select(Payout)
        .where(Payout.status.in_([PayoutStatus.pending, PayoutStatus.processing]))
        .order_by(Payout.created_at.asc())
        .limit(limit)
    )
    return [_serialize_payout(p) for p in result.scalars().all()]


async def get_payout_stats(db: AsyncSession) -> dict:
    """Get payout statistics."""
    total_result = await db.execute(
        select(func.sum(Payout.amount_kes))
        .where(Payout.status == PayoutStatus.completed)
    )
    total_paid = float(total_result.scalar() or 0)

    pending_result = await db.execute(
        select(func.sum(Payout.amount_kes))
        .where(Payout.status == PayoutStatus.pending)
    )
    pending_amount = float(pending_result.scalar() or 0)

    count_result = await db.execute(
        select(func.count(Payout.id))
        .where(Payout.status == PayoutStatus.completed)
    )
    completed_count = count_result.scalar() or 0

    return {
        "total_paid_kes": total_paid,
        "pending_amount_kes": pending_amount,
        "completed_payouts": completed_count,
    }


# ── Internal Helpers ──────────────────────────────────────────────────────────────

def _serialize_payout(p: Payout) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "amount_kes": float(p.amount_kes),
        "payout_type": p.payout_type,
        "status": p.status.value if p.status else None,
        "mpesa_receipt": p.mpesa_receipt,
        "reference_id": p.reference_id,
        "reference_type": p.reference_type,
        "description": p.description,
        "failure_reason": p.failure_reason,
        "processed_at": p.processed_at.isoformat() if p.processed_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
