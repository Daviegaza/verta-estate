"""
Dispute API routes — user disputes, admin investigation, and resolution.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.dispute_service import (
    create_dispute, get_dispute_by_id, get_user_disputes,
    get_all_disputes, assign_dispute, resolve_dispute, get_dispute_stats,
    DISPUTE_CATEGORIES,
)

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.post("")
async def file_dispute(
    category: str = Query(..., description=f"One of: {', '.join(DISPUTE_CATEGORIES)}"),
    description: str = Query(..., min_length=20, description="Detailed description of the issue"),
    property_id: int = Query(None),
    subject_type: str = Query(None),
    subject_id: int = Query(None),
    evidence_urls: str = Query(None, description="Comma-separated URLs of evidence"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """File a new dispute."""
    try:
        urls = [u.strip() for u in evidence_urls.split(",") if u.strip()] if evidence_urls else []
        dispute = await create_dispute(
            db=db,
            reporter_id=current_user.id,
            category=category,
            description=description,
            property_id=property_id,
            subject_type=subject_type,
            subject_id=subject_id,
            evidence_urls=urls,
        )
        return {
            "id": dispute.id,
            "status": dispute.status.value,
            "category": dispute.category,
            "message": "Dispute filed successfully. Our team will investigate.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/categories")
async def dispute_categories():
    """List available dispute categories."""
    return {"categories": DISPUTE_CATEGORIES}


@router.get("/my")
async def my_disputes(
    limit: int = Query(50, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get disputes filed by the current user."""
    return {"items": await get_user_disputes(db, current_user.id, limit)}


@router.get("/{dispute_id}")
async def dispute_detail(
    dispute_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single dispute by ID."""
    dispute = await get_dispute_by_id(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return dispute


# ── Admin Endpoints ──────────────────────────────────────────────────────────────

@router.get("/admin/all")
async def admin_list_disputes(
    status: str = Query(None, description="Filter by status: open, investigating, resolved, closed"),
    limit: int = Query(50, le=200),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all disputes with optional status filter."""
    return {"items": await get_all_disputes(db, status=status, limit=limit)}


@router.put("/admin/{dispute_id}/assign")
async def admin_assign_dispute(
    dispute_id: int,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Assign a dispute to yourself for investigation."""
    dispute = await assign_dispute(db, dispute_id, current_admin.id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return {"message": "Dispute assigned for investigation", "dispute": dispute}


@router.put("/admin/{dispute_id}/resolve")
async def admin_resolve_dispute(
    dispute_id: int,
    resolution: str = Query(..., min_length=20, description="Detailed resolution explanation"),
    status: str = Query("resolved", description="resolved or closed"),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Resolve a dispute with a finding and resolution."""
    dispute = await resolve_dispute(
        db, dispute_id, current_admin.id, resolution, status,
    )
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return {"message": f"Dispute {status}", "dispute": dispute}


@router.get("/admin/stats")
async def admin_dispute_stats(
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get dispute statistics."""
    return await get_dispute_stats(db)
