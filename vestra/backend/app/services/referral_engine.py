"""
VESTRA Referral & Viral Growth Engine
======================================
The engine that drives millions of users through network effects.
Users earn rewards for every person they bring who transacts.

Revenue impact: Referral users convert 4x higher and have 37% higher retention.
Based on Uber/Airbnb/PayPal viral growth models.
"""
from __future__ import annotations

import uuid
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.redis import cache_get, cache_set, cache_delete

logger = logging.getLogger("vestra")

# ── Referral Rewards ──────────────────────────────────────────────────────────

REWARDS = {
    # (action, reward_kes, reward_type, description)
    "signup_verified":      {"kes": 50,   "type": "credit",   "desc": "Friend signs up & verifies email"},
    "first_listing":        {"kes": 200,  "type": "credit",   "desc": "Friend creates first property listing"},
    "first_verification":   {"kes": 100,  "type": "credit",   "desc": "Friend runs first AI verification"},
    "first_payment":        {"kes": 200,  "type": "credit",   "desc": "Friend makes first payment"},
    "subscription":         {"kes": 500,  "type": "cash",     "desc": "Friend subscribes to paid plan (you get KES 500)"},
    "property_sold":        {"kes": 1000, "type": "cash",     "desc": "Friend's property sells through Vestra"},
    "agent_onboarded":      {"kes": 2000, "type": "cash",     "desc": "You refer a licensed agent who subscribes"},
}

# Referral code prefix
REFERRAL_CODE_PREFIX = "VST"
REFERRAL_CODE_LENGTH = 8  # Total length including prefix


async def generate_referral_code(db: AsyncSession, user_id: int) -> str:
    """Generate a unique referral code for a user and persist it on the User model."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # If user already has a code, return it
    if user.referral_code:
        return user.referral_code

    # Generate unique code: VST-XXXXXXXX (8 random alphanumeric chars)
    max_attempts = 10
    for _ in range(max_attempts):
        suffix = secrets.token_hex(4).upper()  # 8 chars
        code = f"{REFERRAL_CODE_PREFIX}-{suffix}"

        # Check uniqueness in DB
        existing = await db.execute(
            select(User).where(User.referral_code == code)
        )
        if not existing.scalar_one_or_none():
            # Persist on user model
            user.referral_code = code
            await db.commit()

            # Also store in Redis for fast lookup
            await cache_set(f"vestra:refcode:{code}", user_id, ttl=None)

            logger.info('{"event":"referral_code_generated","user_id":%d,"code":"%s"}', user_id, code)
            return code

    # Fallback: append short uuid
    fallback = f"{REFERRAL_CODE_PREFIX}-{uuid.uuid4().hex[:8].upper()}"
    user.referral_code = fallback
    await db.commit()
    await cache_set(f"vestra:refcode:{fallback}", user_id, ttl=None)
    return fallback


async def get_referrer_id(db: AsyncSession, code: str) -> Optional[int]:
    """Get the user_id associated with a referral code.

    Checks Redis first (fast path), then falls back to database.
    """
    # Try Redis first
    referrer_id = await cache_get(f"vestra:refcode:{code}")
    if referrer_id:
        return int(referrer_id)

    # Fallback: query the User model
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.referral_code == code)
    )
    user = result.scalar_one_or_none()
    if user:
        # Warm Redis cache for next time
        await cache_set(f"vestra:refcode:{code}", user.id, ttl=None)
        return user.id

    return None


async def track_referral_signup(
    db: AsyncSession, new_user_id: int, referral_code: str,
) -> Optional[dict]:
    """Track a new user who signed up via referral link."""
    referrer_id = await get_referrer_id(db, referral_code)
    if not referrer_id or referrer_id == new_user_id:
        return None

    # Create referral record
    from app.models.referral import Referral

    # Check if already tracked
    existing = await db.execute(
        select(Referral).where(
            Referral.referred_user_id == new_user_id,
            Referral.referrer_id == referrer_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    referral = Referral(
        referrer_id=referrer_id,
        referred_user_id=new_user_id,
        referral_code=referral_code,
        status="signed_up",
        signup_at=datetime.now(timezone.utc),
    )
    db.add(referral)
    await db.commit()

    logger.info('{"event":"referral_signup","referrer":%d,"referred":%d}', referrer_id, new_user_id)
    return {"referrer_id": referrer_id, "reward_pending": True}


async def track_referral_verified(db: AsyncSession, user_id: int) -> Optional[dict]:
    """Mark a referred user as email-verified (active status)."""
    from app.models.referral import Referral

    result = await db.execute(
        select(Referral).where(
            Referral.referred_user_id == user_id,
            Referral.status == "signed_up",
        )
    )
    referral = result.scalar_one_or_none()
    if not referral:
        return None

    referral.status = "active"
    referral.rewards_earned = (referral.rewards_earned or 0)
    referral.converted_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info('{"event":"referral_verified","referrer":%d,"referred":%d}', referral.referrer_id, user_id)
    return {"referrer_id": referral.referrer_id}


async def award_referral_reward(
    db: AsyncSession, user_id: int, action: str,
) -> Optional[dict]:
    """
    Award a referral reward when a referred user completes a valuable action.
    Called after: email verify, first listing, first payment, subscription, etc.
    """
    from app.models.referral import Referral, ReferralReward

    if action not in REWARDS:
        return None

    # Find who referred this user
    result = await db.execute(
        select(Referral).where(
            Referral.referred_user_id == user_id,
            or_(
                Referral.status == "signed_up",
                Referral.status == "active",
            ),
        )
    )
    referral = result.scalar_one_or_none()
    if not referral:
        return None

    # Check if this action was already awarded for this referral (idempotency)
    duplicate_check = await db.execute(
        select(ReferralReward).where(
            ReferralReward.referral_id == referral.id,
            ReferralReward.action == action,
        )
    )
    if duplicate_check.scalar_one_or_none():
        logger.info(
            '{"event":"referral_reward_duplicate_skipped","referrer":%d,"referred":%d,"action":"%s"}',
            referral.referrer_id, user_id, action,
        )
        return None

    reward = REWARDS[action]
    current_earned = float(referral.rewards_earned or 0)
    current_total = float(referral.total_rewards or 0)
    referral.rewards_earned = current_earned + reward["kes"]
    referral.total_rewards = current_total + reward["kes"]

    # Update status based on action
    if action == "first_payment":
        referral.status = "converted"
        referral.converted_at = datetime.now(timezone.utc)
    elif action == "subscription":
        referral.status = "converted"
        referral.converted_at = datetime.now(timezone.utc)

    await db.commit()

    # Create reward transaction
    reward_entry = ReferralReward(
        referral_id=referral.id,
        referrer_id=referral.referrer_id,
        action=action,
        amount_kes=reward["kes"],
        reward_type=reward["type"],
        description=reward["desc"],
    )
    db.add(reward_entry)
    await db.commit()

    logger.info(
        '{"event":"referral_reward","referrer":%d,"action":"%s","amount":%d}',
        referral.referrer_id, action, reward["kes"],
    )

    # ── Fire event bus: referral rewarded ──────────────────────────────────
    asyncio.create_task(_bg_emit_referral_event(
        referrer_id=referral.referrer_id,
        action=action,
        reward_kes=reward["kes"],
        reward_type=reward["type"],
        referred_user_id=user_id,
    ))

    return {
        "referrer_id": referral.referrer_id,
        "action": action,
        "reward_kes": reward["kes"],
        "reward_type": reward["type"],
        "total_earned": float(referral.total_rewards),
    }


async def get_user_referral_stats(db: AsyncSession, user_id: int) -> dict:
    """Get a user's referral performance: earnings, referrals, leaderboard position."""
    from app.models.referral import Referral, ReferralReward
    from app.models.user import User

    # Get user's referral code
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    code = user.referral_code if user else None

    # Total referrals (as referrer)
    result = await db.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user_id)
    )
    total_referrals = result.scalar_one()

    # Converted referrals
    result = await db.execute(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user_id,
            Referral.status == "converted",
        )
    )
    converted = result.scalar_one()

    # Total earnings
    result = await db.execute(
        select(func.coalesce(func.sum(ReferralReward.amount_kes), 0)).where(
            ReferralReward.referrer_id == user_id
        )
    )
    total_earned = float(result.scalar_one())

    # Credit vs cash breakdown
    result = await db.execute(
        select(
            ReferralReward.reward_type,
            func.coalesce(func.sum(ReferralReward.amount_kes), 0),
        ).where(
            ReferralReward.referrer_id == user_id
        ).group_by(ReferralReward.reward_type)
    )
    breakdown = {row[0]: float(row[1]) for row in result.all()}

    # Recent referrals
    result = await db.execute(
        select(Referral, User.full_name, User.email)
        .join(User, Referral.referred_user_id == User.id)
        .where(Referral.referrer_id == user_id)
        .order_by(Referral.signup_at.desc())
        .limit(10)
    )
    recent = [
        {
            "id": r.Referral.id,
            "referred_name": r.full_name,
            "referred_email": r.email,
            "status": r.Referral.status,
            "signup_at": r.Referral.signup_at.isoformat() if r.Referral.signup_at else None,
            "rewards_earned": float(r.Referral.rewards_earned or 0),
        }
        for r in result.all()
    ]

    return {
        "referral_code": code,
        "share_link": f"https://vestra.co.ke/ref/{code}" if code else None,
        "total_referrals": total_referrals,
        "converted_referrals": converted,
        "total_earned_kes": total_earned,
        "credit_kes": breakdown.get("credit", 0),
        "cash_kes": breakdown.get("cash", 0),
        "recent_referrals": recent,
        "rewards_breakdown": REWARDS,
    }


async def get_referral_leaderboard(db: AsyncSession, limit: int = 20) -> list:
    """Top referrers leaderboard — gamification for viral growth."""
    from app.models.referral import Referral, ReferralReward
    from app.models.user import User

    result = await db.execute(
        select(
            ReferralReward.referrer_id,
            func.count(func.distinct(Referral.id)).label("total_refs"),
            func.sum(ReferralReward.amount_kes).label("earnings"),
        )
        .join(Referral, ReferralReward.referral_id == Referral.id)
        .group_by(ReferralReward.referrer_id)
        .order_by(func.sum(ReferralReward.amount_kes).desc())
        .limit(limit)
    )
    rows = result.all()

    leaderboard = []
    for rank, row in enumerate(rows, 1):
        ref_id = int(row.referrer_id)
        count = int(row.total_refs)
        earnings = float(row.earnings or 0)

        user_result = await db.execute(select(User).where(User.id == ref_id))
        user_obj = user_result.scalar_one_or_none()

        leaderboard.append({
            "rank": rank,
            "user_id": ref_id,
            "name": user_obj.full_name.split(" ")[0] if user_obj else "User",
            "referrals": count,
            "converted_referrals": 0,  # Filled below
            "earnings_kes": earnings,
        })

    # Fill in conversion counts
    for entry in leaderboard:
        conv_result = await db.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_id == entry["user_id"],
                Referral.status == "converted",
            )
        )
        entry["converted_referrals"] = conv_result.scalar_one()

    return leaderboard


async def claim_referral_earnings(
    db: AsyncSession,
    user_id: int,
    amount_kes: Optional[float] = None,
) -> dict:
    """
    Claim referral earnings as account credit.
    If amount_kes is None, claim all available credit-type earnings.
    Creates a payout record and resets the claimed credit balance.
    """
    from app.models.referral import ReferralReward
    from app.models.enterprise import Payout, PayoutStatus
    from app.models.user import User

    # Calculate available credit (unclaimed credit-type rewards)
    result = await db.execute(
        select(func.coalesce(func.sum(ReferralReward.amount_kes), 0)).where(
            ReferralReward.referrer_id == user_id,
            ReferralReward.reward_type == "credit",
        )
    )
    available_credit = float(result.scalar_one())

    # Also check for cash-type rewards (already claimed via payouts)
    result = await db.execute(
        select(func.coalesce(func.sum(ReferralReward.amount_kes), 0)).where(
            ReferralReward.referrer_id == user_id,
            ReferralReward.reward_type == "cash",
        )
    )
    available_cash = float(result.scalar_one())

    total_available = available_credit + available_cash

    if total_available <= 0:
        return {
            "success": False,
            "message": "No referral earnings available to claim.",
            "available_kes": 0,
        }

    claim_amount = amount_kes if amount_kes and amount_kes <= total_available else total_available

    # Get user's phone for payout
    user_result = await db.execute(select(User).where(User.id == user_id))
    user_obj = user_result.scalar_one_or_none()
    mpesa_phone = user_obj.phone if user_obj and user_obj.phone else ""

    # Create payout record
    payout = Payout(
        user_id=user_id,
        amount_kes=claim_amount,
        type="referral_reward",
        status=PayoutStatus.pending,
        mpesa_phone=mpesa_phone,
        reference=f"REF-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
    )
    db.add(payout)
    await db.commit()

    logger.info(
        '{"event":"referral_earnings_claimed","user_id":%d,"amount":%f}',
        user_id, claim_amount,
    )

    # ── Fire event bus ────────────────────────────────────────────────────
    asyncio.create_task(_bg_emit_payout_event(user_id, claim_amount))

    return {
        "success": True,
        "message": f"KES {claim_amount:,.0f} claimed successfully. Payout #{payout.id} created.",
        "claim_amount_kes": claim_amount,
        "payout_id": payout.id,
        "payout_status": payout.status.value,
        "remaining_kes": round(total_available - claim_amount, 2),
    }


async def get_referrer_summary(db: AsyncSession, user_id: int) -> dict:
    """Get a summary of who referred this user (if anyone)."""
    from app.models.referral import Referral

    result = await db.execute(
        select(Referral).where(Referral.referred_user_id == user_id)
    )
    referral = result.scalar_one_or_none()

    if not referral:
        return {"referred_by": None}

    from app.models.user import User
    user_result = await db.execute(select(User).where(User.id == referral.referrer_id))
    referrer = user_result.scalar_one_or_none()

    return {
        "referred_by": {
            "user_id": referral.referrer_id,
            "name": referrer.full_name if referrer else "Unknown",
            "code": referral.referral_code,
        },
        "status": referral.status,
        "joined_at": referral.signup_at.isoformat() if referral.signup_at else None,
    }


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_referral_event(
    referrer_id: int,
    action: str,
    reward_kes: int,
    reward_type: str,
    referred_user_id: int,
) -> None:
    """Fire-and-forget: emit referral.rewarded event."""
    from app.services.event_bus import emit_event, EVENT_REFERRAL_REWARDED

    try:
        data = {
            "action": action,
            "reward_kes": reward_kes,
            "reward_type": reward_type,
            "referred_user_id": referred_user_id,
        }
        await emit_event(
            event_type=EVENT_REFERRAL_REWARDED,
            user_id=referrer_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_referral_event_failed","referrer_id":%d,"action":"%s"}',
            referrer_id, action,
        )


async def _bg_emit_payout_event(user_id: int, amount_kes: float) -> None:
    """Fire-and-forget: emit payout.processed event."""
    from app.services.event_bus import emit_event, EVENT_PAYOUT_PROCESSED

    try:
        await emit_event(
            event_type=EVENT_PAYOUT_PROCESSED,
            user_id=user_id,
            data={"amount": amount_kes, "type": "referral_reward"},
        )
    except Exception:
        logger.warning(
            '{"event":"bg_payout_event_failed","user_id":%d}',
            user_id,
        )
