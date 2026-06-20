"""
Subscription service — plan definitions, billing, enforcement, auto-renewal.
Sellers, agents, and landlords require paid subscriptions. Buyers are FREE.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.models.user import UserRole
from app.core.redis import cache_get, cache_set, cache_delete

logger = logging.getLogger("vestra")

# ── SUBSCRIPTION PLANS ────────────────────────────────────────────────────────
# (tier, monthly_price_kes, features_list, max_listings, badge_level)

PLANS = {
    "seller": {
        "free": {
            "price": 0,
            "max_listings": 1,
            "features": ["1 active listing", "Basic Trust Score", "Standard support"],
            "badge": None,
        },
        "basic": {
            "price": 500,
            "max_listings": 5,
            "features": ["5 active listings", "Trust Score badge", "WhatsApp inquiries", "Email support"],
            "badge": "bronze",
        },
        "pro": {
            "price": 2000,
            "max_listings": 20,
            "features": ["20 active listings", "Priority in search results", "AI valuation on all listings", "WhatsApp + SMS inquiries", "Priority support", "Listing performance analytics"],
            "badge": "silver",
        },
        "premium": {
            "price": 4999,
            "max_listings": 100,
            "features": ["Unlimited listings", "Featured placement (top 3)", "Dedicated account manager", "Custom branding", "API access", "Bulk upload", "White-label reports"],
            "badge": "gold",
        },
    },
    "agent": {
        "free": {
            "price": 0,
            "max_listings": 2,
            "features": ["2 active listings", "Basic profile", "Standard support"],
            "badge": None,
        },
        "basic": {
            "price": 1000,
            "max_listings": 10,
            "features": ["10 active listings", "Agent profile badge", "WhatsApp business link", "Email support"],
            "badge": "bronze",
        },
        "pro": {
            "price": 5000,
            "max_listings": 50,
            "features": ["50 active listings", "Vestra Verified Agent badge", "Priority in agent directory", "Lead generation tools", "Client management dashboard", "Priority support", "Co-branded marketing materials"],
            "badge": "gold",
        },
        "premium": {
            "price": 10000,
            "max_listings": 200,
            "features": ["200 active listings", "Platinum Verified Agent badge", "Featured agent placement", "Dedicated account manager", "White-label reports", "API access", "Team accounts (5 seats)", "Training & certification"],
            "badge": "platinum",
        },
    },
    "landlord": {
        "free": {
            "price": 0,
            "max_listings": 2,
            "features": ["2 property listings", "Basic rent collection", "Standard support"],
            "badge": None,
        },
        "basic": {
            "price": 500,
            "max_listings": 10,
            "features": ["10 property listings", "M-Pesa rent collection", "Tenant screening (basic)", "Email support"],
            "badge": "bronze",
        },
        "pro": {
            "price": 1500,
            "max_listings": 30,
            "features": ["30 property listings", "Automated rent collection", "Tenant screening (advanced)", "Maintenance request tracking", "Rental income analytics", "Priority support"],
            "badge": "silver",
        },
        "premium": {
            "price": 4999,
            "max_listings": 100,
            "features": ["100 property listings", "Full property management suite", "Automated rent + deposit handling", "Advanced tenant screening + credit checks", "Maintenance contractor network", "Tax reporting", "Dedicated account manager", "API access"],
            "badge": "gold",
        },
    },
}

# Role → required subscription (buyers always free)
ROLE_REQUIRES_SUBSCRIPTION = {
    UserRole.buyer: False,
    UserRole.seller: True,
    UserRole.agent: True,
    UserRole.landlord: True,
    UserRole.admin: False,
    UserRole.super_admin: False,
}

GRACE_PERIOD_DAYS = 3
TRIAL_DAYS = 7


# ── Plan Helpers ──────────────────────────────────────────────────────────────

def get_plan(role: str, tier: str) -> dict:
    """Get plan details for a role+tier combination."""
    role_plans = PLANS.get(role, PLANS["seller"])
    return role_plans.get(tier, role_plans["free"])


def get_all_plans_for_role(role: str) -> list[dict]:
    """Get all plans available for a given role."""
    role_plans = PLANS.get(role, PLANS["seller"])
    return [
        {"tier": tier, "price": p["price"], "features": p["features"],
         "max_listings": p["max_listings"], "badge": p["badge"]}
        for tier, p in role_plans.items()
    ]


def get_subscription_price(role: str, tier: str) -> float:
    """Get the monthly price for a specific plan."""
    return PLANS.get(role, {}).get(tier, {}).get("price", 0)


# ── Subscription CRUD ─────────────────────────────────────────────────────────

async def get_user_subscription(db: AsyncSession, user_id: int) -> Optional[Subscription]:
    """Get a user's active subscription, with Redis caching."""
    cache_key = f"vestra:sub:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached  # Returns the tier info dict

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub_dict = {
            "id": sub.id, "user_id": sub.user_id,
            "tier": sub.tier.value, "status": sub.status.value,
            "amount_kes": sub.amount_kes, "auto_renew": sub.auto_renew,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "grace_period_end": sub.grace_period_end.isoformat() if sub.grace_period_end else None,
            "renewal_failures": sub.renewal_failures,
        }
        await cache_set(cache_key, sub_dict, ttl=300)
        return sub_dict

    return None


async def get_subscription_orm(db: AsyncSession, user_id: int) -> Optional[Subscription]:
    """Get the actual ORM Subscription object (for writes)."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_subscription(
    db: AsyncSession,
    user_id: int,
    tier: str,
    amount_kes: float,
    payment_method: str = "mpesa",
    mpesa_phone: Optional[str] = None,
    trial: bool = False,
) -> Subscription:
    """Create a new subscription for a user."""
    now = datetime.now(timezone.utc)
    period_start = now
    period_end = now + timedelta(days=TRIAL_DAYS if trial else 30)

    sub = Subscription(
        user_id=user_id,
        tier=SubscriptionTier(tier),
        status=SubscriptionStatus.trialing if trial else SubscriptionStatus.active,
        amount_kes=amount_kes,
        billing_cycle="monthly",
        auto_renew=True,
        payment_method=payment_method,
        mpesa_phone=mpesa_phone,
        current_period_start=period_start,
        current_period_end=period_end,
        grace_period_end=period_end + timedelta(days=GRACE_PERIOD_DAYS),
        trial_end=period_end if trial else None,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # Update agent profile if applicable
    await _sync_agent_profile(db, user_id, tier)

    # Clear cache
    await cache_delete(f"vestra:sub:{user_id}")
    logger.info('{"event":"subscription_created","user_id":%d,"tier":"%s"}', user_id, tier)

    # ── Fire event bus: subscription created ───────────────────────────────
    asyncio.create_task(
        _bg_emit_subscription_event(sub, "created")
    )

    # ── Fire analytics: subscription_started ──────────────────────────────
    asyncio.create_task(
        _bg_track_subscription_analytics(user_id, "subscription_started", tier, float(sub.amount_kes))
    )

    return sub


async def upgrade_subscription(
    db: AsyncSession, user_id: int, new_tier: str,
) -> Subscription:
    """Upgrade or downgrade a subscription."""
    sub = await get_subscription_orm(db, user_id)
    if not sub:
        raise ValueError("No active subscription found")

    old_tier = sub.tier.value
    role = await _get_role_from_sub(db, user_id)
    new_price = get_subscription_price(role, new_tier)
    if new_price == 0 and new_tier != "free":
        new_price = sub.amount_kes  # Keep old price if not found

    sub.tier = SubscriptionTier(new_tier)
    sub.amount_kes = new_price
    sub.renewal_failures = 0

    await db.commit()
    await db.refresh(sub)

    # Update agent profile
    await _sync_agent_profile(db, user_id, new_tier)

    # Clear cache
    await cache_delete(f"vestra:sub:{user_id}")
    logger.info('{"event":"subscription_upgraded","user_id":%d,"from":"%s","to":"%s"}',
                user_id, old_tier, new_tier)

    # ── Fire analytics: subscription_upgraded ─────────────────────────────
    asyncio.create_task(
        _bg_track_subscription_analytics(user_id, "subscription_upgraded", new_tier, float(sub.amount_kes),
                                         extra={"from_tier": old_tier})
    )

    return sub


async def cancel_subscription(db: AsyncSession, user_id: int) -> Subscription:
    """Cancel auto-renewal. Subscription remains active until period end."""
    sub = await get_subscription_orm(db, user_id)
    if not sub:
        raise ValueError("No active subscription found")

    sub.auto_renew = False
    sub.status = SubscriptionStatus.cancelled
    sub.cancelled_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(sub)
    await cache_delete(f"vestra:sub:{user_id}")
    logger.info('{"event":"subscription_cancelled","user_id":%d}', user_id)

    # ── Fire analytics: subscription_cancelled ────────────────────────────
    asyncio.create_task(
        _bg_track_subscription_analytics(user_id, "subscription_cancelled",
                                         sub.tier.value if sub.tier else "unknown",
                                         float(sub.amount_kes))
    )

    return sub


async def renew_subscription(
    db: AsyncSession, user_id: int, payment_id: int,
) -> Subscription:
    """Renew subscription after successful payment."""
    sub = await get_subscription_orm(db, user_id)
    if not sub:
        raise ValueError("No subscription found")

    now = datetime.now(timezone.utc)
    sub.status = SubscriptionStatus.active
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)
    sub.grace_period_end = sub.current_period_end + timedelta(days=GRACE_PERIOD_DAYS)
    sub.last_payment_id = payment_id
    sub.renewal_failures = 0

    await db.commit()
    await db.refresh(sub)
    await cache_delete(f"vestra:sub:{user_id}")
    logger.info('{"event":"subscription_renewed","user_id":%d,"payment_id":%d}',
                user_id, payment_id)

    # ── Fire event bus: subscription renewed ───────────────────────────────
    asyncio.create_task(
        _bg_emit_subscription_event(sub, "renewed")
    )

    return sub


async def mark_renewal_failed(db: AsyncSession, user_id: int) -> Optional[Subscription]:
    """Mark a failed renewal attempt. Cancel subscription after max failures."""
    sub = await get_subscription_orm(db, user_id)
    if not sub:
        return None

    sub.renewal_failures += 1

    if sub.renewal_failures >= sub.max_renewal_failures:
        sub.status = SubscriptionStatus.expired
        sub.auto_renew = False
        logger.warning('{"event":"subscription_expired","user_id":%d,"failures":%d}',
                       user_id, sub.renewal_failures)
    else:
        sub.status = SubscriptionStatus.past_due
        logger.warning('{"event":"subscription_past_due","user_id":%d,"failure":%d}',
                       user_id, sub.renewal_failures)

    await db.commit()
    await cache_delete(f"vestra:sub:{user_id}")
    return sub


async def process_auto_renewals(db: AsyncSession) -> list[dict]:
    """
    Process all subscriptions due for renewal.
    Called by a cron job or scheduled task.
    Initiates M-Pesa STK Push for each expiring subscription.
    """
    now = datetime.now(timezone.utc)
    # Find subscriptions expiring within 1 day that have auto_renew enabled
    cutoff = now + timedelta(days=1)

    result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.auto_renew == True,
            Subscription.current_period_end <= cutoff,
        )
    )
    due_subs = result.scalars().all()

    renewed = []
    for sub in due_subs:
        if sub.mpesa_phone and sub.payment_method == "mpesa":
            # Initiate STK Push for renewal
            from app.services.mpesa_service import initiate_stk_push
            try:
                mpesa_resp = await initiate_stk_push(
                    phone_number=sub.mpesa_phone,
                    amount=sub.amount_kes,
                    account_reference=f"SUB-{sub.id}",
                    transaction_desc="Vestra Renewal",
                )
                renewed.append({
                    "subscription_id": sub.id,
                    "user_id": sub.user_id,
                    "amount": sub.amount_kes,
                    "mpesa_response": mpesa_resp,
                })
            except Exception as e:
                await mark_renewal_failed(db, sub.id)
                renewed.append({
                    "subscription_id": sub.id,
                    "user_id": sub.user_id,
                    "error": str(e),
                })

    return renewed


# ── Enforcement ────────────────────────────────────────────────────────────────

async def check_subscription_active(
    db: AsyncSession, user_id: int, role: UserRole,
) -> tuple[bool, str]:
    """
    Check if a user has an active subscription.
    Returns (is_allowed, reason).
    Buyers and admins are always allowed.
    """
    # Buyers and admins don't need subscriptions
    if not ROLE_REQUIRES_SUBSCRIPTION.get(role, False):
        return True, "free_role"

    sub = await get_user_subscription(db, user_id)

    if not sub:
        # Auto-create free trial
        return True, "trial"  # They get a 7-day trial

    status = sub.get("status", "expired")

    if status == "active" or status == "trialing":
        return True, status

    if status == "past_due":
        # In grace period
        grace_end = sub.get("grace_period_end")
        if grace_end:
            grace_dt = datetime.fromisoformat(grace_end)
            if datetime.now(timezone.utc) < grace_dt:
                return True, "grace_period"
        return False, "past_due"

    if status in ("cancelled", "expired"):
        return False, status

    return False, "no_subscription"


async def enforce_subscription(
    db: AsyncSession, user_id: int, role: UserRole,
) -> None:
    """
    Raise an exception if the user doesn't have an active subscription.
    Use this as a FastAPI dependency for protected endpoints.
    """
    from fastapi import HTTPException, status

    allowed, reason = await check_subscription_active(db, user_id, role)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "subscription_required",
                "message": f"Your subscription is {reason}. Please renew to continue.",
                "renew_url": "/api/subscriptions/plans",
            },
        )


async def get_listing_limit(db: AsyncSession, user_id: int, role: str) -> int:
    """Get the maximum number of listings a user can create."""
    if role in ("admin", "super_admin"):
        return 999999

    sub = await get_user_subscription(db, user_id)
    tier = sub.get("tier", "free") if sub else "free"
    plan = get_plan(role, tier)
    return plan.get("max_listings", 1)


# ── Internal Helpers ───────────────────────────────────────────────────────────

async def _sync_agent_profile(db: AsyncSession, user_id: int, tier: str) -> None:
    """Update agent profile badge level based on subscription tier."""
    from app.models.property import AgentProfile
    result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        badge_map = {"basic": "bronze", "pro": "gold", "premium": "platinum"}
        profile.badge_level = badge_map.get(tier, None)
        profile.subscription_tier = tier
        profile.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await db.commit()


async def _get_role_from_sub(db: AsyncSession, user_id: int) -> str:
    """Get user role for a subscription."""
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.role.value if user else "seller"


# ── Background event helpers ──────────────────────────────────────────────────


# ── Lifecycle Notification Triggers ────────────────────────────────────────────


async def send_subscription_lifecycle_notifications(db: AsyncSession) -> list[dict]:
    """
    Scan all subscriptions and send lifecycle notifications where needed.
    Call this from a cron/scheduler every hour.

    Notifications sent:
    - Expiry warning: 3 days before subscription ends
    - Expired: subscription has ended
    - Badge expiring: for agents with badges
    """
    from app.models.user import User
    from app.services.notification_service import (
        send_subscription_expiring_warning,
        send_subscription_expired,
        send_agent_badge_expiring_warning,
    )

    now = datetime.now(timezone.utc)
    notifications_sent = []

    # ── Find subscriptions expiring in ~3 days ────────────────────────────
    three_days_from_now = now + timedelta(days=3)
    week_from_now = now + timedelta(days=7)

    result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.current_period_end >= now,
            Subscription.current_period_end <= three_days_from_now + timedelta(hours=2),
        )
    )
    expiring_subs = result.scalars().all()

    for sub in expiring_subs:
        days_remaining = (sub.current_period_end - now).days
        if days_remaining < 0:
            continue
        try:
            await send_subscription_expiring_warning(
                db=db,
                user_id=sub.user_id,
                tier=sub.tier.value if sub.tier else "free",
                days_remaining=days_remaining,
                amount_kes=float(sub.amount_kes),
            )
            notifications_sent.append({
                "type": "expiry_warning",
                "user_id": sub.user_id,
                "days_remaining": days_remaining,
            })
        except Exception:
            logger.warning(
                '{"event":"sub_lifecycle_notify_failed","type":"expiry_warning","user_id":%d}',
                sub.user_id,
            )

    # ── Find expired subscriptions ────────────────────────────────────────
    expired_result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.expired,
        )
    )
    expired_subs = expired_result.scalars().all()

    for sub in expired_subs:
        try:
            await send_subscription_expired(
                db=db,
                user_id=sub.user_id,
                tier=sub.tier.value if sub.tier else "free",
            )
            notifications_sent.append({
                "type": "expired",
                "user_id": sub.user_id,
            })
        except Exception:
            logger.warning(
                '{"event":"sub_lifecycle_notify_failed","type":"expired","user_id":%d}',
                sub.user_id,
            )

    # ── Agent badge expiring warnings ─────────────────────────────────────
    from app.models.property import AgentProfile

    badge_result = await db.execute(
        select(AgentProfile, User.id)
        .join(User, AgentProfile.user_id == User.id)
        .where(
            AgentProfile.badge_level.isnot(None),
            AgentProfile.subscription_expires_at.isnot(None),
            AgentProfile.subscription_expires_at >= now,
            AgentProfile.subscription_expires_at <= week_from_now,
        )
    )
    badge_rows = badge_result.all()

    for profile_row, uid in badge_rows:
        days_remaining = (profile_row.subscription_expires_at - now).days
        if days_remaining < 0:
            continue
        try:
            await send_agent_badge_expiring_warning(
                db=db,
                user_id=uid,
                badge_level=profile_row.badge_level or "",
                days_remaining=days_remaining,
            )
            notifications_sent.append({
                "type": "badge_expiry_warning",
                "user_id": uid,
                "days_remaining": days_remaining,
                "badge_level": profile_row.badge_level,
            })
        except Exception:
            logger.warning(
                '{"event":"sub_lifecycle_notify_failed","type":"badge_warning","user_id":%d}',
                uid,
            )

    if notifications_sent:
        logger.info(
            '{"event":"sub_lifecycle_notifications_sent","count":%d}',
            len(notifications_sent),
        )

    return notifications_sent


async def _bg_track_subscription_analytics(
    user_id: int,
    event_type: str,
    tier: str,
    amount_kes: float,
    extra: Optional[dict] = None,
) -> None:
    """Fire-and-forget: track subscription analytics event."""
    from app.services.analytics_service import fire_and_forget_track_user_event

    try:
        data = {
            "tier": tier,
            "amount_kes": amount_kes,
        }
        if extra:
            data.update(extra)
        await fire_and_forget_track_user_event(
            user_id=user_id,
            event_type=event_type,
            event_data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_subscription_analytics_failed","user_id":%d,"event_type":"%s"}',
            user_id, event_type,
        )


async def _bg_emit_subscription_event(sub, action: str) -> None:
    """Fire-and-forget: emit subscription event."""
    from app.services.event_bus import emit_event, EVENT_SUBSCRIPTION_CREATED

    try:
        data = {
            "subscription_id": sub.id,
            "tier": sub.tier.value if sub.tier else "unknown",
            "action": action,
            "amount_kes": float(sub.amount_kes),
        }
        await emit_event(
            event_type=EVENT_SUBSCRIPTION_CREATED,
            user_id=sub.user_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_subscription_event_failed","subscription_id":%d,"action":"%s"}',
            sub.id, action,
        )
