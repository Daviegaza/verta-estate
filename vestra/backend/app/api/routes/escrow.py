"""
Escrow API routes — secure property transaction holding.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.escrow_service import (
    create_escrow, deposit_paid, balance_paid,
    release_escrow, cancel_escrow, dispute_escrow,
    get_escrow_by_id, get_user_escrows, get_pending_escrows, get_escrow_stats,
)

router = APIRouter(prefix="/escrow", tags=["Escrow"])


@router.post("")
async def create_new_escrow(
    property_id: int = Query(...),
    amount_kes: float = Query(..., gt=0),
    seller_id: int = Query(...),
    agent_id: int = Query(None),
    deposit_amount_kes: float = Query(None),
    terms: str = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a new escrow transaction for a property purchase."""
    try:
        escrow = await create_escrow(
            db=db,
            property_id=property_id,
            buyer_id=current_user.id,
            seller_id=seller_id,
            amount_kes=amount_kes,
            agent_id=agent_id,
            deposit_amount_kes=deposit_amount_kes,
            terms=terms,
        )
        return {
            "id": escrow.id,
            "status": escrow.status.value,
            "amount_kes": float(escrow.amount_kes),
            "message": "Escrow created. Deposit payment is now required.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my")
async def my_escrows(
    limit: int = Query(20, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's escrow transactions."""
    return {"items": await get_user_escrows(db, current_user.id, limit)}


@router.get("/{escrow_id}")
async def escrow_detail(
    escrow_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single escrow transaction by ID."""
    escrow = await get_escrow_by_id(db, escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return escrow


@router.post("/{escrow_id}/deposit")
async def mark_deposit_paid(
    escrow_id: int,
    payment_reference: str = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark escrow deposit as paid."""
    escrow = await deposit_paid(db, escrow_id, payment_reference)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return {"message": "Deposit recorded", "status": escrow.status.value}


@router.post("/{escrow_id}/balance")
async def mark_balance_paid(
    escrow_id: int,
    payment_reference: str = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark escrow balance as paid (full amount now in escrow)."""
    escrow = await balance_paid(db, escrow_id, payment_reference)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return {"message": "Balance recorded", "status": escrow.status.value}


@router.post("/{escrow_id}/release")
async def release_escrow_funds(
    escrow_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Release escrow funds to seller (conditions met)."""
    try:
        escrow = await release_escrow(db, escrow_id, current_user.id)
        if not escrow:
            raise HTTPException(status_code=404, detail="Escrow not found")
        return {"message": "Escrow released to seller", "status": escrow.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{escrow_id}/cancel")
async def cancel_escrow_transaction(
    escrow_id: int,
    reason: str = Query(..., min_length=10),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an escrow and refund the buyer."""
    try:
        escrow = await cancel_escrow(db, escrow_id, current_user.id, reason)
        if not escrow:
            raise HTTPException(status_code=404, detail="Escrow not found")
        return {"message": "Escrow cancelled", "status": escrow.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{escrow_id}/dispute")
async def dispute_escrow_transaction(
    escrow_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Raise a dispute on an escrow — funds are frozen pending resolution."""
    escrow = await dispute_escrow(db, escrow_id, current_user.id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return {"message": "Escrow disputed. Funds frozen pending resolution.", "status": escrow.status.value}


# ── Admin Endpoints ──────────────────────────────────────────────────────────────

@router.get("/admin/pending")
async def admin_pending_escrows(
    limit: int = Query(20, le=100),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get all pending escrow transactions."""
    return {"items": await get_pending_escrows(db, limit)}


@router.get("/admin/stats")
async def admin_escrow_stats(
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get escrow statistics."""
    return await get_escrow_stats(db)
