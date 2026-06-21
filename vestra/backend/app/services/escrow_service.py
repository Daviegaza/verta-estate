"""
Escrow Service — secure transaction holding for property purchases.
Vestra holds funds in escrow until conditions are met, protecting both buyer and seller.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.trust_safety import EscrowTransaction, EscrowStatus

logger = logging.getLogger("vestra")

# Vestra escrow fee: 1% per transaction
ESCROW_FEE_PCT = 1.0


async def create_escrow(
    db: AsyncSession,
    property_id: int,
    buyer_id: int,
    seller_id: int,
    amount_kes: float,
    agent_id: Optional[int] = None,
    deposit_amount_kes: Optional[float] = None,
    terms: Optional[str] = None,
) -> EscrowTransaction:
    """Create a new escrow transaction for a property purchase."""
    escrow = EscrowTransaction(
        property_id=property_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        agent_id=agent_id,
        amount_kes=amount_kes,
        deposit_amount_kes=deposit_amount_kes,
        status=EscrowStatus.initiated,
        terms=terms,
    )
    db.add(escrow)
    await db.commit()
    await db.refresh(escrow)

    # Log audit
    from app.services.audit_service import log_action
    await log_action(
        db, buyer_id, "escrow.created", "escrow", escrow.id,
        {"amount": amount_kes, "property_id": property_id},
    )

    logger.info(
        '{"event":"escrow_created","id":%d,"amount":%s,"property_id":%d,"buyer_id":%d}',
        escrow.id, amount_kes, property_id, buyer_id,
    )
    return escrow


async def deposit_paid(
    db: AsyncSession, escrow_id: int, payment_reference: str,
) -> Optional[EscrowTransaction]:
    """Mark the deposit as paid. Only valid from 'initiated' status."""
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None
    if escrow.status != EscrowStatus.initiated:
        raise ValueError(f"Cannot mark deposit paid from status: {escrow.status.value}")

    escrow.status = EscrowStatus.deposit_paid
    escrow.deposit_reference = payment_reference

    await db.commit()
    await db.refresh(escrow)
    logger.info('{"event":"escrow_deposit_paid","id":%d,"ref":"%s"}', escrow_id, payment_reference)
    return escrow


async def balance_paid(
    db: AsyncSession, escrow_id: int, payment_reference: str,
) -> Optional[EscrowTransaction]:
    """Mark the balance as paid. Only valid from 'deposit_paid' status."""
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None
    if escrow.status != EscrowStatus.deposit_paid:
        raise ValueError(f"Cannot mark balance paid from status: {escrow.status.value}. Deposit must be paid first.")

    escrow.status = EscrowStatus.balance_paid
    escrow.payment_reference = payment_reference

    await db.commit()
    await db.refresh(escrow)
    logger.info('{"event":"escrow_balance_paid","id":%d,"ref":"%s"}', escrow_id, payment_reference)
    return escrow


async def release_escrow(
    db: AsyncSession, escrow_id: int, released_by_id: int,
) -> Optional[EscrowTransaction]:
    """
    Release escrow funds to the seller. Called when conditions are met
    (title deed transfer verified, both parties confirm).
    """
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None
    if escrow.status != EscrowStatus.balance_paid:
        raise ValueError(f"Cannot release escrow in status: {escrow.status.value}")

    # Calculate Vestra fee (1%)
    fee_kes = float(escrow.amount_kes) * (ESCROW_FEE_PCT / 100)
    seller_payout = float(escrow.amount_kes) - fee_kes

    escrow.status = EscrowStatus.completed
    escrow.release_condition_met = True
    escrow.completion_date = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(escrow)

    from app.services.audit_service import log_action
    await log_action(
        db, released_by_id, "escrow.released", "escrow", escrow_id,
        {"fee_kes": fee_kes, "seller_payout": seller_payout},
    )

    logger.info(
        '{"event":"escrow_released","id":%d,"seller_payout":%s,"fee":%s}',
        escrow_id, seller_payout, fee_kes,
    )

    # ── Fire event bus: escrow completed ───────────────────────────────────
    from app.services.event_bus import emit_event, EVENT_ESCROW_COMPLETED
    asyncio.create_task(
        _bg_emit_escrow_event(escrow)
    )

    return escrow


async def cancel_escrow(
    db: AsyncSession, escrow_id: int, cancelled_by_id: int, reason: str,
) -> Optional[EscrowTransaction]:
    """Cancel an escrow and refund the buyer."""
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None

    if escrow.status in (EscrowStatus.completed, EscrowStatus.refunded):
        raise ValueError(f"Cannot cancel escrow in terminal status: {escrow.status.value}")

    escrow.status = EscrowStatus.cancelled

    await db.commit()
    await db.refresh(escrow)

    from app.services.audit_service import log_action
    await log_action(
        db, cancelled_by_id, "escrow.cancelled", "escrow", escrow_id,
        {"reason": reason},
    )

    logger.info('{"event":"escrow_cancelled","id":%d,"reason":"%s"}', escrow_id, reason)
    return escrow


async def dispute_escrow(
    db: AsyncSession, escrow_id: int, disputed_by_id: int,
) -> Optional[EscrowTransaction]:
    """Mark an escrow as disputed — funds are frozen pending resolution."""
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None

    escrow.status = EscrowStatus.disputed

    await db.commit()
    await db.refresh(escrow)

    from app.services.audit_service import log_action
    await log_action(
        db, disputed_by_id, "escrow.disputed", "escrow", escrow_id, {},
    )

    logger.warning('{"event":"escrow_disputed","id":%d}', escrow_id)
    return escrow


async def get_escrow_by_id(
    db: AsyncSession, escrow_id: int,
) -> Optional[dict]:
    """Get escrow details with related data."""
    escrow = await _get_escrow(db, escrow_id)
    if not escrow:
        return None
    return _serialize_escrow(escrow)


async def get_user_escrows(
    db: AsyncSession, user_id: int, limit: int = 20,
) -> list[dict]:
    """Get all escrows where user is buyer or seller."""
    result = await db.execute(
        select(EscrowTransaction)
        .where(
            (EscrowTransaction.buyer_id == user_id) |
            (EscrowTransaction.seller_id == user_id)
        )
        .order_by(EscrowTransaction.created_at.desc())
        .limit(limit)
    )
    return [_serialize_escrow(e) for e in result.scalars().all()]


async def get_pending_escrows(
    db: AsyncSession, limit: int = 20,
) -> list[dict]:
    """Get all pending escrows (for admin)."""
    result = await db.execute(
        select(EscrowTransaction)
        .where(EscrowTransaction.status.in_([
            EscrowStatus.initiated,
            EscrowStatus.deposit_paid,
            EscrowStatus.balance_paid,
            EscrowStatus.disputed,
        ]))
        .order_by(EscrowTransaction.created_at.desc())
        .limit(limit)
    )
    return [_serialize_escrow(e) for e in result.scalars().all()]


async def get_escrow_stats(db: AsyncSession) -> dict:
    """Get escrow statistics for admin dashboard."""
    total_result = await db.execute(
        select(func.count(EscrowTransaction.id))
    )
    total = total_result.scalar() or 0

    volume_result = await db.execute(
        select(func.sum(EscrowTransaction.amount_kes))
        .where(EscrowTransaction.status == EscrowStatus.completed)
    )
    total_volume = float(volume_result.scalar() or 0)

    active_result = await db.execute(
        select(func.count(EscrowTransaction.id))
        .where(EscrowTransaction.status.in_([
            EscrowStatus.deposit_paid,
            EscrowStatus.balance_paid,
        ]))
    )
    active = active_result.scalar() or 0

    return {
        "total_escrows": total,
        "total_volume_kes": total_volume,
        "vestra_fees_earned": total_volume * (ESCROW_FEE_PCT / 100),
        "active_escrows": active,
    }


# ── Internal Helpers ──────────────────────────────────────────────────────────────

async def _get_escrow(db: AsyncSession, escrow_id: int) -> Optional[EscrowTransaction]:
    result = await db.execute(
        select(EscrowTransaction).where(EscrowTransaction.id == escrow_id)
    )
    return result.scalar_one_or_none()


def _serialize_escrow(e: EscrowTransaction) -> dict:
    return {
        "id": e.id,
        "property_id": e.property_id,
        "buyer_id": e.buyer_id,
        "seller_id": e.seller_id,
        "agent_id": e.agent_id,
        "amount_kes": float(e.amount_kes),
        "deposit_amount_kes": float(e.deposit_amount_kes) if e.deposit_amount_kes else None,
        "status": e.status.value if e.status else None,
        "payment_reference": e.payment_reference,
        "release_condition_met": e.release_condition_met,
        "completion_date": e.completion_date.isoformat() if e.completion_date else None,
        "terms": e.terms,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_escrow_event(escrow) -> None:
    """Fire-and-forget: emit escrow.completed event."""
    from app.services.event_bus import emit_event, EVENT_ESCROW_COMPLETED

    try:
        data = {
            "escrow_id": escrow.id,
            "property_id": escrow.property_id,
            "amount_kes": float(escrow.amount_kes),
            "buyer_id": escrow.buyer_id,
            "seller_id": escrow.seller_id,
        }
        await emit_event(
            event_type=EVENT_ESCROW_COMPLETED,
            user_id=escrow.buyer_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_escrow_event_failed","escrow_id":%d}',
            escrow.id,
        )
