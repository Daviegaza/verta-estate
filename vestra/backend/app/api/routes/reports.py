"""
Verification Report API — paid trust report generation and retrieval.
Also provides public shareable trust report endpoints (no auth required).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.report_service import generate_verification_pdf
from app.services.verification_service import get_verification_by_id
from app.models.user import UserRole
from app.models.document import VerificationStatus

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


# ── Public Shareable Trust Report (no auth) ─────────────────────────────────────


_BADGE_COLORS = {
    "platinum": "#7c3aed",  # Purple
    "gold": "#f59e0b",      # Yellow/Amber
    "silver": "#9ca3af",    # Gray
    "bronze": "#f97316",    # Orange
}


def _get_badge_level(trust_score: float) -> str:
    if trust_score >= 90:
        return "platinum"
    elif trust_score >= 75:
        return "gold"
    elif trust_score >= 60:
        return "silver"
    else:
        return "bronze"


@router.get("/public/{verification_id}")
async def get_public_trust_report(
    verification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Public (no-auth) trust report for sharing.
    Returns property info, trust score with component breakdown,
    verification badge level, and AI summary (no internal notes).
    """
    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Only show approved verifications publicly
    if verification.status not in (VerificationStatus.approved, VerificationStatus.flagged):
        raise HTTPException(status_code=404, detail="Verification report not available for public view")

    # Get property details
    prop = None
    if verification.property_id:
        from app.services.property_service import get_property_by_id
        prop = await get_property_by_id(db, verification.property_id)

    # Parse trust components from stored ai_raw_response
    trust_components = []
    if verification.ai_raw_response:
        raw = verification.ai_raw_response
        if isinstance(raw, dict) and "trust_components" in raw:
            trust_components = raw["trust_components"]

    trust_score = verification.trust_score or 0
    badge_level = _get_badge_level(trust_score)
    badge_color = _BADGE_COLORS.get(badge_level, "#6b7280")

    # Build AI summary (public-safe — no internal notes)
    ai_summary = verification.ai_summary or "AI analysis completed."
    recommendation = verification.ai_recommendation or "review"
    fraud_score = verification.fraud_risk_score or 0

    from datetime import timezone
    verified_on = None
    if verification.reviewed_at:
        verified_on = verification.reviewed_at.astimezone(timezone.utc).isoformat()
    elif verification.created_at:
        verified_on = verification.created_at.astimezone(timezone.utc).isoformat()

    # QR-code placeholder URL (in production, point to a real URL)
    qr_url = f"https://vestra.co.ke/reports/public/{verification_id}"

    return {
        "verification_id": verification.id,
        "property": {
            "title": prop.title if prop else "N/A",
            "city": prop.city if prop else "N/A",
            "property_type": prop.property_type.value if prop and prop.property_type else "N/A",
            "listing_type": prop.listing_type.value if prop and prop.listing_type else "N/A",
            "price_kes": float(prop.price) if prop and prop.price else None,
        },
        "trust_score": trust_score,
        "badge": {
            "level": badge_level,
            "color": badge_color,
            "label": badge_level.capitalize(),
        },
        "fraud_risk_score": fraud_score,
        "price_reasonableness": verification.price_reasonableness,
        "ownership_confidence": verification.ownership_confidence,
        "ai_recommendation": recommendation,
        "ai_summary": ai_summary,
        "trust_components": trust_components,
        "document_flags": verification.document_flags or [],
        "verified_on": verified_on,
        "qr_code_url": qr_url,
        "report_url": f"https://vestra.co.ke/reports/public/{verification_id}",
    }


@router.get("/public/{verification_id}/badge")
async def get_public_trust_badge(
    verification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Public SVG trust badge for embedding on external sites.
    Colors: platinum=purple, gold=yellow, silver=gray, bronze=orange.
    """
    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    if verification.status not in (VerificationStatus.approved, VerificationStatus.flagged):
        raise HTTPException(status_code=404, detail="Badge not available")

    trust_score = verification.trust_score or 0
    badge_level = _get_badge_level(trust_score)
    badge_color = _BADGE_COLORS.get(badge_level, "#6b7280")
    badge_label = badge_level.capitalize()

    # Generate simple SVG badge
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60" viewBox="0 0 200 60">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{badge_color};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{badge_color};stop-opacity:0.85" />
    </linearGradient>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/>
    </filter>
  </defs>
  <rect width="200" height="60" rx="8" ry="8" fill="url(#bg)" filter="url(#shadow)"/>

  <!-- Shield icon -->
  <path d="M20 12 L100 8 L180 12 L180 36 Q180 52 100 56 Q20 52 20 36 Z"
        fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.4)" stroke-width="1"/>

  <!-- Trust text -->
  <text x="100" y="22" font-family="Arial, sans-serif" font-size="10"
        fill="rgba(255,255,255,0.9)" text-anchor="middle" font-weight="bold">
    VESTRA TRUSTED</text>

  <!-- Score -->
  <text x="100" y="40" font-family="Arial, sans-serif" font-size="20"
        fill="#ffffff" text-anchor="middle" font-weight="bold">
    {trust_score:.0f}/100</text>

  <!-- Badge level -->
  <text x="100" y="54" font-family="Arial, sans-serif" font-size="9"
        fill="rgba(255,255,255,0.85)" text-anchor="middle" font-weight="bold">
    {badge_label} BADGE</text>
</svg>'''

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Badge-Level": badge_level,
            "X-Trust-Score": str(trust_score),
        },
    )
