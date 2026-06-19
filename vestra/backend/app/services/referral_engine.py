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
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.redis import cache_get, cache_set, cache_delete

logger = logging.getLogger("vestra")

# ── Referral Rewards ──────────────────────────────────────────────────────────

REWARDS = {
    # (action, reward_kes, reward_type, description)
    "signup_verified":      {"kes": 50,   "type": "credit",   "desc": "Friend signs up & verifies email"},
    "first_listing":        {"kes": 200,  "type": "credit",   "desc": "Friend creates first property listing"},
    "first_verification":   {"kes": 100,  "type": "credit",   "desc": "Friend runs first AI verification"},
    "first_payment":        {"kes": 150,  "type": "credit",   "desc": "Friend makes first payment"},
    "subscription":         {"kes": 500,  "type": "cash",     "desc": "Friend subscribes to paid plan (you get KES 500)"},
    "property_sold":        {"kes": 1000, "type": "cash",     "desc": "Friend's property sells through Vestra"},
    "agent_onboarded":      {"kes": 2000, "type": "cash",     "desc": "You refer a licensed agent who subscribes"},
}

# Referral code prefix
REFERRAL_CODE_PREFIX = "VST"


async def generate_referral_code(db: AsyncSession, user_id: int) -> str:
    """Generate a unique referral code for a user."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    # Create code from name + random suffix
    name_part = user.full_name.replace(" ", "").upper()[:4]
    suffix = uuid.uuid4().hex[:4].upper()
    code = f"{REFERRAL_CODE_PREFIX}{name_part}{suffix}"

    # Store in Redis: referral_code → user_id
    await cache_set(f"vestra:refcode:{code}", user_id, ttl=None)  # Permanent

    logger.info('{"event":"referral_code_generated","user_id":%d,"code":"%s"}', user_id, code)
    return code


async def get_referrer_id(db: AsyncSession, code: str) -> Optional[int]:
    """Get the user_id associated with a referral code."""
    referrer_id = await cache_get(f"vestra:refcode:{code}")
    return int(referrer_id) if referrer_id else None


async def track_referral_signup(
    db: AsyncSession, new_user_id: int, referral_code: str,
) -> Optional[dict]:
    """Track a new user who signed up via referral link."""
    referrer_id = await get_referrer_id(db, referral_code)
    if not referrer_id or referrer_id == new_user_id:
        return None

    # Create referral record
    from app.models.referral import Referral

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


async def award_referral_reward(
    db: AsyncSession, user_id: int, action: str,
) -> Optional[dict]:
    """
    Award a referral reward when a referred user completes a valuable action.
    Called after: email verify, first listing, first verification, subscription, etc.
    """
    from app.models.referral import Referral

    if action not in REWARDS:
        return None

    # Find who referred this user
    result = await db.execute(
        select(Referral).where(
            Referral.referred_user_id == user_id,
            Referral.status == "signed_up",
        )
    )
    referral = result.scalar_one_or_none()
    if not referral:
        return None

    # Check if this action was already awarded for this referral (idempotency)
    from app.models.referral import ReferralReward
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
    referral.rewards_earned += reward["kes"]
    referral.total_rewards += reward["kes"]

    if action == "subscription":
        referral.status = "converted"

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
        "total_earned": referral.total_rewards,
    }


async def get_user_referral_stats(db: AsyncSession, user_id: int) -> dict:
    """Get a user's referral performance: earnings, referrals, leaderboard position."""
    from app.models.referral import Referral

    # Total referrals
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
        select(func.sum(Referral.total_rewards)).where(Referral.referrer_id == user_id)
    )
    total_earned = result.scalar_one() or 0

    # Referral code
    code = None  # Look up from Redis? Or store on user model
    # For now, generate if needed

    return {
        "total_referrals": total_referrals,
        "converted_referrals": converted,
        "total_earned_kes": float(total_earned),
        "referral_code": code,
        "rewards_breakdown": REWARDS,
        "share_link": f"https://vestra.co.ke/ref/{code}" if code else None,
    }


async def get_referral_leaderboard(db: AsyncSession, limit: int = 20) -> list:
    """Top referrers leaderboard — gamification for viral growth."""
    from app.models.referral import Referral
    from app.models.user import User

    result = await db.execute(
        select(
            Referral.referrer_id,
            func.count(Referral.id).label("total_refs"),
            func.sum(Referral.total_rewards).label("earnings"),
        )
        .group_by(Referral.referrer_id)
        .order_by(func.sum(Referral.total_rewards).desc())
        .limit(limit)
    )
    rows = result.all()

    leaderboard = []
    for rank, (ref_id, count, earnings) in enumerate(rows, 1):
        user_result = await db.execute(select(User).where(User.id == ref_id))
        user = user_result.scalar_one_or_none()
        leaderboard.append({
            "rank": rank,
            "user_id": ref_id,
            "name": user.full_name.split(" ")[0] if user else "User",
            "referrals": count,
            "earnings_kes": float(earnings or 0),
        })

    return leaderboard


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
