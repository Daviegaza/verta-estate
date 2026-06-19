"""
Payout API routes — agent commission withdrawals and landlord rent disbursements.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.payout_service import (
    create_payout, process_payout, complete_payout, fail_payout,
    get_user_payouts, get_pending_payouts, get_payout_stats,
)

router = APIRouter(prefix="/payouts", tags=["Payouts"])


@router.post("/request")
async def request_payout(
    amount_kes: float = Query(..., gt=0),
    payout_type: str = Query("commission", description="commission, rent_disbursement, refund"),
    description: str = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a payout (agent commission withdrawal, etc.)."""
    payout = await create_payout(
        db=db,
        user_id=current_user.id,
        amount_kes=amount_kes,
        payout_type=payout_type,
        description=description,
    )
    return {
        "id": payout.id,
        "amount_kes": float(payout.amount_kes),
        "status": payout.status.value,
        "message": f"Payout of KES {amount_kes:,.0f} requested. Processing within 24 hours.",
    }


@router.get("/my")
async def my_payouts(
    limit: int = Query(50, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's payout history."""
    return {"items": await get_user_payouts(db, current_user.id, limit)}


@router.get("/{payout_id}")
async def payout_detail(
    payout_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single payout by ID."""
    payouts = await get_user_payouts(db, current_user.id, 100)
    payout = next((p for p in payouts if p["id"] == payout_id), None)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return payout


# ── Admin Endpoints ──────────────────────────────────────────────────────────────

@router.get("/admin/pending")
async def admin_pending_payouts(
    limit: int = Query(50, le=200),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get pending payouts for processing."""
    return {"items": await get_pending_payouts(db, limit)}


@router.post("/admin/{payout_id}/process")
async def admin_process_payout(
    payout_id: int,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Process a pending payout via M-Pesa B2C."""
    payout = await process_payout(db, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found or not in pending state")
    return {"message": "Payout processing initiated", "payout": payout}


@router.post("/admin/{payout_id}/complete")
async def admin_complete_payout(
    payout_id: int,
    mpesa_receipt: str = Query(...),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Mark a payout as completed with M-Pesa receipt."""
    payout = await complete_payout(db, payout_id, mpesa_receipt)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return {"message": "Payout marked as completed", "payout": payout}


@router.post("/admin/{payout_id}/fail")
async def admin_fail_payout(
    payout_id: int,
    reason: str = Query(..., min_length=5),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Mark a payout as failed."""
    payout = await fail_payout(db, payout_id, reason)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return {"message": "Payout marked as failed", "payout": payout}


@router.get("/admin/stats")
async def admin_payout_stats(
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get payout statistics."""
    return await get_payout_stats(db)
