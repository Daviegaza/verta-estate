"""Fraud reporting and blacklist API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.fraud_service import (
    report_fraud, check_blacklist, admin_review_fraud, get_pending_fraud_reports,
)
from app.models.trust_safety import FraudReportStatus

router = APIRouter(prefix="/fraud", tags=["Fraud"])


@router.post("/report")
async def report_fraud_endpoint(
    description: str,
    reported_phone: Optional[str] = None,
    reported_email: Optional[str] = None,
    reported_title_deed: Optional[str] = None,
    reported_name: Optional[str] = None,
    evidence_urls: Optional[str] = None,  # Comma-separated URLs
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Report a fraudulent listing, agent, or user."""
    urls = [u.strip() for u in (evidence_urls or "").split(",") if u.strip()]
    report = await report_fraud(
        db=db,
        reporter_id=current_user.id,
        description=description,
        reported_phone=reported_phone,
        reported_email=reported_email,
        reported_title_deed=reported_title_deed,
        reported_name=reported_name,
        evidence_urls=urls,
    )
    return {
        "report_id": report.id,
        "status": report.status.value,
        "message": "Thank you for your report. Our team will investigate.",
    }


@router.get("/check")
async def check_fraud_endpoint(
    phone: Optional[str] = None,
    email: Optional[str] = None,
    title_deed: Optional[str] = None,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint: check if a phone/email/title_deed appears in fraud blacklist.
    Used by buyers before making payments.
    """
    if not any([phone, email, title_deed, name]):
        raise HTTPException(status_code=400, detail="Provide at least one search parameter")
    return await check_blacklist(db, phone=phone, email=email, title_deed=title_deed, name=name)


@router.get("/admin/pending")
async def admin_pending_fraud(
    limit: int = 20,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: get pending fraud reports."""
    items = await get_pending_fraud_reports(db, limit)
    return {
        "items": [
            {
                "id": r.id,
                "reported_phone": r.reported_phone,
                "reported_email": r.reported_email,
                "reported_name": r.reported_name,
                "description": r.description[:200],
                "status": r.status.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
    }


@router.put("/admin/review/{report_id}")
async def admin_review_fraud_endpoint(
    report_id: int,
    status: FraudReportStatus,
    notes: Optional[str] = None,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: review a fraud report."""
    report = await admin_review_fraud(
        db=db,
        report_id=report_id,
        reviewer_id=current_user.id,
        status=status,
        notes=notes,
    )
    if not report:
        raise HTTPException(status_code=404, detail="Fraud report not found")
    return {"report_id": report.id, "status": report.status.value}
