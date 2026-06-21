"""
Coupon & Discount Service — promotional codes for subscription discounts.
Supports percentage and fixed-amount discounts with usage limits and expiry.
"""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.enterprise import Coupon, DiscountType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")


async def create_coupon(
    db: AsyncSession,
    code: str,
    discount_type: str,
    discount_value: float,
    max_uses: int = 100,
    min_subscription_tier: str | None = None,
    expires_at: datetime | None = None,
    description: str | None = None,
) -> Coupon:
    """Create a new discount coupon."""
    # Validate discount type and value
    discount = DiscountType(discount_type)
    if discount == DiscountType.percentage and (discount_value <= 0 or discount_value > 100):
        raise ValueError("Percentage discount must be between 1 and 100")
    if discount == DiscountType.fixed and discount_value <= 0:
        raise ValueError("Fixed discount must be greater than 0")

    coupon = Coupon(
        code=code.upper().strip(),
        discount_type=discount,
        discount_value=discount_value,
        max_uses=max_uses,
        times_used=0,
        is_active=True,
        min_subscription_tier=min_subscription_tier,
        expires_at=expires_at,
        description=description,
        created_at=datetime.now(UTC),
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    logger.info(
        '{"event":"coupon_created","code":"%s","type":"%s","value":%s}',
        coupon.code, discount_type, discount_value,
    )
    return coupon


async def generate_bulk_coupons(
    db: AsyncSession,
    count: int,
    discount_type: str,
    discount_value: float,
    prefix: str = "VESTRA",
    max_uses: int = 1,
    **kwargs,
) -> list[Coupon]:
    """Generate multiple unique coupon codes."""
    coupons = []
    for _ in range(count):
        suffix = secrets.token_hex(4).upper()
        code = f"{prefix}-{suffix}"
        try:
            coupon = await create_coupon(
                db, code, discount_type, discount_value,
                max_uses=max_uses, **kwargs,
            )
            coupons.append(coupon)
        except Exception as e:
            logger.warning('{"event":"bulk_coupon_skip","code":"%s","error":"%s"}', code, str(e))
            continue
    return coupons


async def validate_coupon(
    db: AsyncSession, code: str, user_id: int | None = None,
) -> dict:
    """
    Validate a coupon code. Returns discount info or error.
    Does NOT apply the coupon — just checks validity.
    """
    result = await db.execute(
        select(Coupon).where(Coupon.code == code.upper().strip())
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        return {"valid": False, "error": "Invalid coupon code"}

    if not coupon.is_active:
        return {"valid": False, "error": "This coupon is no longer active"}

    if coupon.times_used >= coupon.max_uses:
        return {"valid": False, "error": "This coupon has reached its usage limit"}

    if coupon.expires_at and coupon.expires_at < datetime.now(UTC):
        return {"valid": False, "error": "This coupon has expired"}

    return {
        "valid": True,
        "code": coupon.code,
        "discount_type": coupon.discount_type.value if coupon.discount_type else None,
        "discount_value": float(coupon.discount_value),
        "description": coupon.description,
        "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
    }


async def apply_coupon(
    db: AsyncSession, code: str, user_id: int, original_amount: float,
) -> dict:
    """
    Apply a coupon to a transaction. Returns the discounted amount.
    Increments the coupon's usage counter.
    """
    validation = await validate_coupon(db, code, user_id)
    if not validation["valid"]:
        raise ValueError(validation["error"])

    result = await db.execute(
        select(Coupon).where(Coupon.code == code.upper().strip())
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise ValueError("Coupon not found")

    # Calculate discount
    if coupon.discount_type == DiscountType.percentage:
        discount_amount = original_amount * (float(coupon.discount_value) / 100)
    else:  # fixed
        discount_amount = float(coupon.discount_value)

    discounted = max(0, original_amount - discount_amount)

    # Increment usage
    coupon.times_used += 1
    if coupon.times_used >= coupon.max_uses:
        coupon.is_active = False

    await db.commit()

    logger.info(
        '{"event":"coupon_applied","code":"%s","user_id":%d,"original":%s,"discounted":%s}',
        code, user_id, original_amount, discounted,
    )

    return {
        "code": coupon.code,
        "original_amount": original_amount,
        "discount_amount": round(discount_amount, 2),
        "final_amount": round(discounted, 2),
        "discount_type": coupon.discount_type.value,
        "discount_value": float(coupon.discount_value),
    }


async def deactivate_coupon(
    db: AsyncSession, code: str,
) -> Coupon | None:
    """Deactivate a coupon code."""
    result = await db.execute(
        select(Coupon).where(Coupon.code == code.upper().strip())
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        return None

    coupon.is_active = False
    await db.commit()
    await db.refresh(coupon)

    logger.info('{"event":"coupon_deactivated","code":"%s"}', code)
    return coupon


async def list_active_coupons(
    db: AsyncSession, limit: int = 50,
) -> list[dict]:
    """List all active coupons (admin)."""
    result = await db.execute(
        select(Coupon)
        .where(Coupon.is_active)
        .order_by(Coupon.created_at.desc())
        .limit(limit)
    )
    coupons = result.scalars().all()

    return [
        {
            "id": c.id,
            "code": c.code,
            "discount_type": c.discount_type.value if c.discount_type else None,
            "discount_value": float(c.discount_value),
            "times_used": c.times_used,
            "max_uses": c.max_uses,
            "is_active": c.is_active,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "description": c.description,
        }
        for c in coupons
    ]
