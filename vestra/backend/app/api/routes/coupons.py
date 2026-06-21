"""
Coupon API routes — promotional discount codes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.services.coupon_service import (
    apply_coupon,
    list_active_coupons,
    validate_coupon,
)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.get("/validate/{code}")
async def check_coupon(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a coupon code without applying it."""
    result = await validate_coupon(db, code, current_user.id)
    return result


@router.post("/apply/{code}")
async def apply_coupon_code(
    code: str,
    amount: float = Query(..., gt=0, description="Original amount before discount"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a coupon to get a discounted amount."""
    try:
        result = await apply_coupon(db, code, current_user.id, amount)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/admin/list")
async def admin_list_coupons(
    limit: int = Query(50, le=200),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all active coupons."""
    return {"items": await list_active_coupons(db, limit)}
