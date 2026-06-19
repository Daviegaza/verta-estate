"""
Subscription API endpoints — plans, upgrade, downgrade, cancel, M-Pesa payment.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import User, UserRole
from app.models.payment import PaymentPurpose, PaymentStatus
from app.services.subscription_service import (
    PLANS,
    get_all_plans_for_role,
    get_subscription_price,
    get_user_subscription,
    get_subscription_orm,
    create_subscription,
    upgrade_subscription,
    cancel_subscription,
    renew_subscription,
    check_subscription_active,
    get_listing_limit,
    process_auto_renewals,
    ROLE_REQUIRES_SUBSCRIPTION,
    TRIAL_DAYS,
    GRACE_PERIOD_DAYS,
)
from app.services.payment_service import initiate_mpesa_payment

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all available subscription plans for the user's role."""
    role = current_user.role.value
    plans = get_all_plans_for_role(role)
    current_sub = await get_user_subscription(db, current_user.id)

    return {
        "role": role,
        "current_tier": current_sub.get("tier", "free") if current_sub else "free",
        "current_status": current_sub.get("status", "active") if current_sub else "active",
        "requires_subscription": ROLE_REQUIRES_SUBSCRIPTION.get(current_user.role, False),
        "trial_days": TRIAL_DAYS,
        "grace_period_days": GRACE_PERIOD_DAYS,
        "plans": plans,
    }


@router.get("/plans/{role}")
async def list_plans_for_role(role: str):
    """Get plans for a specific role (public — for viewing before signup)."""
    if role not in PLANS:
        raise HTTPException(status_code=404, detail=f"Unknown role: {role}")
    return {
        "role": role,
        "requires_subscription": ROLE_REQUIRES_SUBSCRIPTION.get(UserRole(role), False),
        "plans": get_all_plans_for_role(role),
    }


# ── My Subscription ───────────────────────────────────────────────────────────

@router.get("/my")
async def my_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription status."""
    sub = await get_user_subscription(db, current_user.id) if db else None
    limit = await get_listing_limit(db, current_user.id, current_user.role.value) if db else 999

    return {
        "subscription": sub,
        "listing_limit": limit,
        "role": current_user.role.value,
        "requires_subscription": ROLE_REQUIRES_SUBSCRIPTION.get(current_user.role, False),
        "free_forever": not ROLE_REQUIRES_SUBSCRIPTION.get(current_user.role, False),
    }


# ── Subscribe / Upgrade ───────────────────────────────────────────────────────

@router.post("/subscribe")
async def subscribe_to_plan(
    tier: str = Query(..., pattern="^(free|basic|pro|premium)$"),
    phone_number: str = Query(..., description="M-Pesa phone number 2547XXXXXXXX"),
    background_tasks: BackgroundTasks = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to a plan. Initiates M-Pesa STK Push for payment.
    Free tier is activated immediately without payment.
    """
    role = current_user.role.value

    if role == "buyer":
        raise HTTPException(
            status_code=400,
            detail="Buyers don't need a subscription — Vestra is free for buyers forever!"
        )

    if tier not in PLANS.get(role, {}):
        raise HTTPException(status_code=400, detail=f"Invalid tier '{tier}' for role '{role}'")

    price = get_subscription_price(role, tier)

    # Free tier — activate immediately
    if price == 0:
        existing = await get_subscription_orm(db, current_user.id)
        if existing:
            sub = await upgrade_subscription(db, current_user.id, "free")
        else:
            sub = await create_subscription(db, current_user.id, "free", 0)
        return {
            "message": "Free plan activated!",
            "tier": "free",
            "subscription_id": sub.id,
        }

    # Paid tier — initiate M-Pesa STK Push
    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=phone_number,
        amount=price,
        purpose=PaymentPurpose.subscription,
        description=f"Vestra {tier.title()} Plan",
    )

    if payment.status == PaymentStatus.processing:
        return {
            "message": f"M-Pesa STK Push sent to {phone_number}. Enter your PIN to complete.",
            "payment_id": payment.id,
            "checkout_request_id": payment.mpesa_checkout_request_id,
            "amount": price,
            "tier": tier,
            "currency": "KES",
            "status": "payment_pending",
        }
    else:
        return {
            "message": "Payment initiation failed. Please try again.",
            "error": payment.error_message,
            "status": "failed",
        }


@router.post("/upgrade")
async def upgrade_plan(
    tier: str = Query(..., pattern="^(basic|pro|premium)$"),
    phone_number: str = Query(..., description="M-Pesa phone number"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade to a higher plan. Initiates M-Pesa payment for price difference."""
    role = current_user.role.value
    price = get_subscription_price(role, tier)

    if price == 0:
        raise HTTPException(status_code=400, detail="Cannot upgrade to free plan. Use /subscribe instead.")

    # Get current subscription
    current_sub = await get_user_subscription(db, current_user.id)
    current_tier = current_sub.get("tier", "free") if current_sub else "free"
    current_price = get_subscription_price(role, current_tier)

    # Calculate prorated amount for upgrade
    prorated = price - current_price
    if prorated <= 0:
        prorated = price  # Full price if downgrade or same

    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=phone_number,
        amount=prorated,
        purpose=PaymentPurpose.subscription,
        description=f"Upgrade to {tier.title()}",
    )

    return {
        "message": f"Upgrade to {tier.title()} — M-Pesa STK Push sent.",
        "payment_id": payment.id,
        "checkout_request_id": payment.mpesa_checkout_request_id,
        "amount": prorated,
        "from_tier": current_tier,
        "to_tier": tier,
        "status": "payment_pending",
    }


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_my_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel auto-renewal. Access remains until period end."""
    try:
        sub = await cancel_subscription(db, current_user.id)
        return {
            "message": "Subscription cancelled. You retain access until the end of your billing period.",
            "access_until": sub.current_period_end.isoformat(),
            "tier": sub.tier.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Reactivate ────────────────────────────────────────────────────────────────

@router.post("/reactivate")
async def reactivate_subscription(
    phone_number: str = Query(..., description="M-Pesa phone number"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a cancelled or expired subscription."""
    sub = await get_subscription_orm(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found. Use /subscribe first.")

    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=phone_number,
        amount=sub.amount_kes,
        purpose=PaymentPurpose.subscription,
        description="Vestra Reactivation",
    )

    return {
        "message": "M-Pesa STK Push sent for reactivation.",
        "payment_id": payment.id,
        "amount": sub.amount_kes,
        "tier": sub.tier.value,
    }


# ── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/all")
async def list_all_subscriptions(
    skip: int = 0,
    limit: int = 50,
    tier: str = None,
    status: str = None,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all subscriptions with filters."""
    from sqlalchemy import select
    from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus

    query = select(Subscription).order_by(Subscription.created_at.desc())
    if tier:
        try:
            query = query.where(Subscription.tier == SubscriptionTier(tier))
        except ValueError:
            pass
    if status:
        try:
            query = query.where(Subscription.status == SubscriptionStatus(status))
        except ValueError:
            pass

    result = await db.execute(query.offset(skip).limit(limit))
    subs = result.scalars().all()

    return {
        "items": [
            {
                "id": s.id, "user_id": s.user_id,
                "tier": s.tier.value, "status": s.status.value,
                "amount_kes": s.amount_kes, "auto_renew": s.auto_renew,
                "period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "renewal_failures": s.renewal_failures,
                "user_email": s.user.email if s.user else "Unknown",
                "created_at": s.created_at.isoformat(),
            }
            for s in subs
        ],
        "total": len(subs),
    }


@router.post("/admin/process-renewals")
async def trigger_auto_renewals(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Manually trigger subscription renewal processing."""
    results = await process_auto_renewals(db)
    return {
        "processed": len(results),
        "results": results,
    }


# ── Enforcement Check ─────────────────────────────────────────────────────────

@router.get("/check")
async def check_access(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user's subscription allows access."""
    allowed, reason = await check_subscription_active(
        db, current_user.id, current_user.role
    )
    limit = await get_listing_limit(db, current_user.id, current_user.role.value)

    return {
        "allowed": allowed,
        "reason": reason,
        "listing_limit": limit,
        "role": current_user.role.value,
        "free_forever": not ROLE_REQUIRES_SUBSCRIPTION.get(current_user.role, False),
    }


async def _get_db_session(user: User):
    """Get a DB session — used when we need DB but not as a FastAPI dependency."""
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal()
