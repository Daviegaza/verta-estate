"""
Fraud Service — fraud reporting, blacklist checking, and investigation tools.
"""
from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.trust_safety import FraudReport, FraudReportStatus

logger = logging.getLogger("vestra")


async def report_fraud(
    db: AsyncSession,
    reporter_id: int,
    description: str,
    reported_phone: Optional[str] = None,
    reported_email: Optional[str] = None,
    reported_title_deed: Optional[str] = None,
    reported_name: Optional[str] = None,
    evidence_urls: Optional[list] = None,
) -> FraudReport:
    """Submit a fraud report."""
    report = FraudReport(
        reporter_id=reporter_id,
        reported_phone=reported_phone,
        reported_email=reported_email,
        reported_title_deed=reported_title_deed,
        reported_name=reported_name,
        description=description,
        evidence_urls=evidence_urls or [],
        status=FraudReportStatus.pending,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    logger.info(
        '{"event":"fraud_reported","reporter_id":%d,"phone":"%s","email":"%s"}',
        reporter_id, reported_phone, reported_email,
    )
    return report


async def check_blacklist(
    db: AsyncSession,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    title_deed: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """
    Check if a phone/email/title_deed/name appears in confirmed fraud reports.
    Returns a risk assessment.
    """
    conditions = []
    if phone:
        conditions.append(FraudReport.reported_phone == phone)
    if email:
        conditions.append(FraudReport.reported_email == email)
    if title_deed:
        conditions.append(FraudReport.reported_title_deed == title_deed)
    if name:
        conditions.append(FraudReport.reported_name == name)

    if not conditions:
        return {"blacklisted": False, "matches": 0, "reports": []}

    result = await db.execute(
        select(FraudReport).where(
            FraudReport.status == FraudReportStatus.confirmed,
            or_(*conditions),
        )
    )
    matches = result.scalars().all()

    return {
        "blacklisted": len(matches) > 0,
        "matches": len(matches),
        "reports": [
            {
                "id": r.id,
                "description": r.description[:200],
                "reported_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in matches
        ],
    }


async def admin_review_fraud(
    db: AsyncSession,
    report_id: int,
    reviewer_id: int,
    status: FraudReportStatus,
    notes: Optional[str] = None,
) -> Optional[FraudReport]:
    """Admin reviews a fraud report."""
    result = await db.execute(
        select(FraudReport).where(FraudReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        return None

    report.status = status
    report.reviewed_by_id = reviewer_id
    report.review_notes = notes

    await db.commit()
    await db.refresh(report)
    logger.info(
        '{"event":"fraud_reviewed","report_id":%d,"status":"%s"}',
        report_id, status.value,
    )
    return report


async def get_pending_fraud_reports(
    db: AsyncSession, limit: int = 20
) -> list[FraudReport]:
    """Get pending fraud reports for admin review."""
    result = await db.execute(
        select(FraudReport)
        .where(FraudReport.status == FraudReportStatus.pending)
        .order_by(FraudReport.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
