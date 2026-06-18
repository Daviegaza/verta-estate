"""
KYC (Know Your Customer) API routes — identity verification.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.kyc_service import (
    submit_kyc, get_kyc_status, admin_review_kyc,
    get_pending_kyc, count_pending_kyc,
)
from app.models.kyc_notification import KYCStatus

router = APIRouter(prefix="/kyc", tags=["KYC"])


@router.post("/submit")
async def submit_kyc_endpoint(
    id_type: str = Form(...),
    id_number: str = Form(...),
    id_front: UploadFile = File(None),
    id_back: UploadFile = File(None),
    selfie: UploadFile = File(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit KYC verification with ID documents."""
    # Save uploaded files
    import os
    from app.core.config import settings

    upload_dir = os.path.join(settings.UPLOAD_DIR, "kyc", str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    id_front_url = None
    id_back_url = None
    selfie_url = None

    if id_front:
        id_front_url = os.path.join(upload_dir, f"front_{id_front.filename}")
        with open(id_front_url, "wb") as f:
            f.write(await id_front.read())

    if id_back:
        id_back_url = os.path.join(upload_dir, f"back_{id_back.filename}")
        with open(id_back_url, "wb") as f:
            f.write(await id_back.read())

    if selfie:
        selfie_url = os.path.join(upload_dir, f"selfie_{selfie.filename}")
        with open(selfie_url, "wb") as f:
            f.write(await selfie.read())

    kyc = await submit_kyc(
        db=db,
        user_id=current_user.id,
        id_type=id_type,
        id_number=id_number,
        id_front_url=id_front_url,
        id_back_url=id_back_url,
        selfie_url=selfie_url,
    )
    return {
        "kyc_id": kyc.id,
        "status": kyc.status.value,
        "message": "KYC submitted successfully. We will review and get back to you.",
    }


@router.get("/status")
async def kyc_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's KYC verification status."""
    kyc = await get_kyc_status(db, current_user.id)
    if not kyc:
        return {"status": "not_submitted", "message": "You haven't submitted KYC yet."}
    return {
        "kyc_id": kyc.id,
        "status": kyc.status.value,
        "id_type": kyc.id_type,
        "id_number": kyc.id_number[-4:].rjust(len(kyc.id_number), "*") if kyc.id_number else None,
        "rejection_reason": kyc.rejection_reason,
        "submitted_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "reviewed_at": kyc.reviewed_at.isoformat() if kyc.reviewed_at else None,
        "expires_at": kyc.expires_at.isoformat() if kyc.expires_at else None,
    }


@router.get("/admin/pending")
async def admin_pending_kyc(
    limit: int = 20,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: get pending KYC submissions."""
    items = await get_pending_kyc(db, limit)
    return {
        "total": await count_pending_kyc(db),
        "items": [
            {
                "id": k.id,
                "user_id": k.user_id,
                "id_type": k.id_type,
                "id_number": k.id_number,
                "status": k.status.value,
                "submitted_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in items
        ],
    }


@router.post("/admin/review/{kyc_id}")
async def admin_review_kyc_endpoint(
    kyc_id: int,
    status: KYCStatus,
    rejection_reason: str = None,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: approve or reject a KYC submission."""
    kyc = await admin_review_kyc(
        db=db,
        kyc_id=kyc_id,
        reviewer_id=current_user.id,
        status=status,
        rejection_reason=rejection_reason,
    )
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return {
        "kyc_id": kyc.id,
        "status": kyc.status.value,
        "message": f"KYC {status.value}",
    }
