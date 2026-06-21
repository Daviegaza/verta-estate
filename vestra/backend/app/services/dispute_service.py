"""
Dispute Service — dispute creation, investigation, and resolution.
Handles buyer-seller disputes, fraud claims, and payment issues.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.models.trust_safety import Dispute, DisputeStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

DISPUTE_CATEGORIES = [
    "fraud",
    "misrepresentation",
    "payment_issue",
    "title_deed",
    "property_condition",
    "agent_misconduct",
    "refund_request",
    "other",
]


async def create_dispute(
    db: AsyncSession,
    reporter_id: int,
    category: str,
    description: str,
    property_id: int | None = None,
    subject_type: str | None = None,
    subject_id: int | None = None,
    evidence_urls: list | None = None,
) -> Dispute:
    """File a new dispute."""
    if category not in DISPUTE_CATEGORIES:
        raise ValueError(f"Invalid category: {category}. Must be one of {DISPUTE_CATEGORIES}")

    dispute = Dispute(
        reporter_id=reporter_id,
        property_id=property_id,
        subject_type=subject_type,
        subject_id=subject_id,
        category=category,
        description=description,
        evidence_urls=evidence_urls or [],
        status=DisputeStatus.open,
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)

    from app.services.audit_service import log_action
    await log_action(
        db, reporter_id, "dispute.created", "dispute", dispute.id,
        {"category": category, "property_id": property_id},
    )

    logger.info(
        '{"event":"dispute_created","id":%d,"reporter":%d,"category":"%s"}',
        dispute.id, reporter_id, category,
    )

    # ── Fire event bus: dispute filed ──────────────────────────────────────
    _task_dispute = asyncio.create_task(  # noqa: RUF006
        _bg_emit_dispute_event(dispute)
    )

    return dispute


async def get_dispute_by_id(
    db: AsyncSession, dispute_id: int,
) -> dict | None:
    """Get dispute details."""
    result = await db.execute(
        select(Dispute).where(Dispute.id == dispute_id)
    )
    dispute = result.scalar_one_or_none()
    return _serialize_dispute(dispute) if dispute else None


async def get_user_disputes(
    db: AsyncSession, user_id: int, limit: int = 50,
) -> list[dict]:
    """Get all disputes filed by a user."""
    result = await db.execute(
        select(Dispute)
        .where(Dispute.reporter_id == user_id)
        .order_by(Dispute.created_at.desc())
        .limit(limit)
    )
    return [_serialize_dispute(d) for d in result.scalars().all()]


async def get_all_disputes(
    db: AsyncSession, status: str | None = None, limit: int = 50,
) -> list[dict]:
    """Get all disputes (admin view), optionally filtered by status."""
    query = select(Dispute).order_by(Dispute.created_at.desc())

    if status:
        try:
            dispute_status = DisputeStatus(status)
            query = query.where(Dispute.status == dispute_status)
        except ValueError:
            pass  # Invalid status — return all

    query = query.limit(limit)
    result = await db.execute(query)
    return [_serialize_dispute(d) for d in result.scalars().all()]


async def assign_dispute(
    db: AsyncSession, dispute_id: int, admin_id: int,
) -> dict | None:
    """Assign a dispute to an admin for investigation."""
    result = await db.execute(
        select(Dispute).where(Dispute.id == dispute_id)
    )
    dispute = result.scalar_one_or_none()
    if not dispute:
        return None

    dispute.resolved_by_id = admin_id
    dispute.status = DisputeStatus.investigating

    await db.commit()
    await db.refresh(dispute)

    from app.services.audit_service import log_action
    await log_action(
        db, admin_id, "dispute.assigned", "dispute", dispute_id,
        {"admin_id": admin_id},
    )

    logger.info('{"event":"dispute_assigned","id":%d,"admin":%d}', dispute_id, admin_id)
    return _serialize_dispute(dispute)


async def resolve_dispute(
    db: AsyncSession,
    dispute_id: int,
    resolver_id: int,
    resolution: str,
    status: str = "resolved",
) -> dict | None:
    """Resolve a dispute with a resolution note."""
    result = await db.execute(
        select(Dispute).where(Dispute.id == dispute_id)
    )
    dispute = result.scalar_one_or_none()
    if not dispute:
        return None

    dispute.status = DisputeStatus(status)
    dispute.resolution = resolution
    dispute.resolved_by_id = resolver_id
    dispute.resolved_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(dispute)

    from app.services.audit_service import log_action
    await log_action(
        db, resolver_id, "dispute.resolved", "dispute", dispute_id,
        {"status": status, "resolution": resolution[:200]},
    )

    logger.info(
        '{"event":"dispute_resolved","id":%d,"status":"%s"}', dispute_id, status,
    )
    return _serialize_dispute(dispute)


async def get_dispute_stats(db: AsyncSession) -> dict:
    """Get dispute statistics for admin dashboard."""
    total_result = await db.execute(select(func.count(Dispute.id)))
    total = total_result.scalar() or 0

    open_result = await db.execute(
        select(func.count(Dispute.id))
        .where(Dispute.status == DisputeStatus.open)
    )
    open_count = open_result.scalar() or 0

    investigating_result = await db.execute(
        select(func.count(Dispute.id))
        .where(Dispute.status == DisputeStatus.investigating)
    )
    investigating_count = investigating_result.scalar() or 0

    # By category
    category_counts = {}
    for cat in DISPUTE_CATEGORIES:
        count_result = await db.execute(
            select(func.count(Dispute.id)).where(Dispute.category == cat)
        )
        count = count_result.scalar() or 0
        if count > 0:
            category_counts[cat] = count

    return {
        "total": total,
        "open": open_count,
        "investigating": investigating_count,
        "by_category": category_counts,
    }


# ── Internal Helpers ──────────────────────────────────────────────────────────────

def _serialize_dispute(d: Dispute) -> dict:
    return {
        "id": d.id,
        "reporter_id": d.reporter_id,
        "property_id": d.property_id,
        "subject_type": d.subject_type,
        "subject_id": d.subject_id,
        "category": d.category,
        "description": d.description,
        "evidence_urls": d.evidence_urls or [],
        "status": d.status.value if d.status else None,
        "resolution": d.resolution,
        "resolved_by_id": d.resolved_by_id,
        "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_dispute_event(dispute) -> None:
    """Fire-and-forget: emit dispute.filed event."""
    from app.services.event_bus import EVENT_DISPUTE_FILED, emit_event

    try:
        data = {
            "dispute_id": dispute.id,
            "category": dispute.category,
            "property_id": dispute.property_id,
            "description": dispute.description[:200],
        }
        await emit_event(
            event_type=EVENT_DISPUTE_FILED,
            user_id=dispute.reporter_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_dispute_event_failed","dispute_id":%d}',
            dispute.id,
        )
