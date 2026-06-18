"""
Verification Report API — paid trust report generation and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.report_service import generate_verification_pdf
from app.services.verification_service import get_verification_by_id
from app.models.user import UserRole

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/verification/{verification_id}")
async def get_verification_report(
    verification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get verification report data as JSON."""
    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Only the requester, property owner, or admin can view
    prop_owner_id = None
    if verification.property_id:
        from app.services.property_service import get_property_by_id
        prop = await get_property_by_id(db, verification.property_id)
        if prop:
            prop_owner_id = prop.owner_id if hasattr(prop, 'owner_id') else prop.get('owner_id')

    is_authorized = (
        current_user.id == verification.user_id or
        current_user.id == prop_owner_id or
        current_user.role in (UserRole.admin, UserRole.super_admin)
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to view this report")

    return {
        "id": verification.id,
        "property_id": verification.property_id,
        "status": verification.status.value if hasattr(verification.status, 'value') else verification.status,
        "fraud_risk_score": verification.fraud_risk_score,
        "trust_score": verification.trust_score,
        "price_reasonableness": verification.price_reasonableness,
        "ownership_confidence": verification.ownership_confidence,
        "ai_recommendation": verification.ai_recommendation,
        "document_flags": verification.document_flags or [],
        "ai_summary": verification.ai_summary,
        "created_at": verification.created_at.isoformat() if verification.created_at else None,
    }


@router.get("/verification/{verification_id}/pdf")
async def download_verification_pdf(
    verification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Download a branded PDF verification report.
    Requires authentication. Only the requester, property owner, or admin can access.
    """
    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Authorization check
    prop_owner_id = None
    if verification.property_id:
        from app.services.property_service import get_property_by_id
        prop = await get_property_by_id(db, verification.property_id)
        if prop:
            prop_owner_id = prop.owner_id if hasattr(prop, 'owner_id') else prop.get('owner_id')

    is_authorized = (
        current_user.id == verification.user_id or
        current_user.id == prop_owner_id or
        current_user.role in (UserRole.admin, UserRole.super_admin)
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to download this report")

    pdf_bytes = await generate_verification_pdf(db, verification_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=503,
            detail="PDF generation is temporarily unavailable. Please try again later."
        )

    filename = f"Vestra_Trust_Report_{verification_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-cache",
        },
    )
