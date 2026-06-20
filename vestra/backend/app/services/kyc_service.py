"""
KYC Service — identity verification workflow for agents, landlords, and users.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.kyc_notification import KYCVerification, KYCStatus

logger = logging.getLogger("vestra")

KYC_EXPIRY_DAYS = 365  # Re-verify annually


async def submit_kyc(
    db: AsyncSession,
    user_id: int,
    id_type: str,
    id_number: str,
    id_front_url: Optional[str] = None,
    id_back_url: Optional[str] = None,
    selfie_url: Optional[str] = None,
) -> KYCVerification:
    """Submit a KYC verification request."""
    # Check if user already has a pending/reviewing KYC
    result = await db.execute(
        select(KYCVerification).where(
            KYCVerification.user_id == user_id,
            KYCVerification.status.in_([KYCStatus.pending, KYCStatus.reviewing]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    kyc = KYCVerification(
        user_id=user_id,
        status=KYCStatus.pending,
        id_type=id_type,
        id_number=id_number,
        id_front_url=id_front_url,
        id_back_url=id_back_url,
        selfie_url=selfie_url,
    )
    db.add(kyc)
    await db.commit()
    await db.refresh(kyc)
    logger.info('{"event":"kyc_submitted","user_id":%d,"id_type":"%s"}', user_id, id_type)

    # ── Fire analytics event: kyc_submitted ────────────────────────────────
    from app.services.analytics_service import fire_and_forget_track_user_event
    import asyncio
    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=user_id,
            event_type="kyc_submitted",
            event_data={"id_type": id_type},
        )
    )

    return kyc


async def get_kyc_status(db: AsyncSession, user_id: int) -> Optional[KYCVerification]:
    """Get the latest KYC verification for a user."""
    result = await db.execute(
        select(KYCVerification)
        .where(KYCVerification.user_id == user_id)
        .order_by(KYCVerification.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def admin_review_kyc(
    db: AsyncSession,
    kyc_id: int,
    reviewer_id: int,
    status: KYCStatus,
    rejection_reason: Optional[str] = None,
) -> Optional[KYCVerification]:
    """Admin reviews a KYC submission."""
    result = await db.execute(
        select(KYCVerification).where(KYCVerification.id == kyc_id)
    )
    kyc = result.scalar_one_or_none()
    if not kyc:
        return None

    kyc.status = status
    kyc.reviewer_id = reviewer_id
    kyc.reviewed_at = datetime.now(timezone.utc)
    if rejection_reason:
        kyc.rejection_reason = rejection_reason
    if status == KYCStatus.approved:
        kyc.expires_at = datetime.now(timezone.utc) + timedelta(days=KYC_EXPIRY_DAYS)

    await db.commit()
    await db.refresh(kyc)

    # Update user's is_verified and is_kyc_verified flags
    if status == KYCStatus.approved:
        from app.models.user import User
        user_result = await db.execute(select(User).where(User.id == kyc.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.is_verified = True
            user.is_kyc_verified = True
            await db.commit()

    logger.info(
        '{"event":"kyc_reviewed","kyc_id":%d,"status":"%s","reviewer_id":%d}',
        kyc_id, status.value, reviewer_id,
    )

    # ── Fire analytics event on approval ──────────────────────────────────
    if status == KYCStatus.approved:
        from app.services.analytics_service import fire_and_forget_track_user_event
        import asyncio
        asyncio.create_task(
            fire_and_forget_track_user_event(
                user_id=kyc.user_id,
                event_type="kyc_approved",
                event_data={"kyc_id": kyc_id, "id_type": kyc.id_type},
            )
        )

    return kyc


async def get_pending_kyc(db: AsyncSession, limit: int = 20) -> list[KYCVerification]:
    """Get pending KYC submissions for admin review."""
    result = await db.execute(
        select(KYCVerification)
        .where(KYCVerification.status == KYCStatus.pending)
        .order_by(KYCVerification.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def count_pending_kyc(db: AsyncSession) -> int:
    """Count pending KYC submissions."""
    result = await db.execute(
        select(func.count(KYCVerification.id)).where(
            KYCVerification.status == KYCStatus.pending
        )
    )
    return result.scalar_one()
