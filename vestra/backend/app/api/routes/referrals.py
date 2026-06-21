"""
Referral API Routes — referral code management, leaderboard, and payout claiming.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.services.analytics_service import fire_and_forget_track_user_event
from app.services.referral_engine import (
    claim_referral_earnings,
    get_referral_leaderboard,
    get_referrer_summary,
    get_user_referral_stats,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/code")
async def get_my_referral_code(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's referral code and stats.
    Returns: referral code, share link, signups, conversions, earnings.
    """
    # Ensure referral code exists
    from app.models.user import User
    from app.services.referral_engine import generate_referral_code

    user_result = await db.execute(
        __import__("sqlalchemy").select(User).where(User.id == current_user.id)
    )
    user = user_result.scalar_one_or_none()

    if not user.referral_code:
        await generate_referral_code(db, current_user.id)

    stats = await get_user_referral_stats(db, current_user.id)

    # Also get who referred this user
    referred_by_info = await get_referrer_summary(db, current_user.id)

    # Track analytics event
    asyncio.create_task(  # noqa: RUF006
        fire_and_forget_track_user_event(
            user_id=current_user.id,
            event_type="referral_code_viewed",
            event_data={"referral_code": stats.get("referral_code")},
        )
    )

    return {
        **stats,
        "referred_by": referred_by_info.get("referred_by"),
    }


@router.get("/leaderboard")
async def referral_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top referrers leaderboard — sorted by conversion earnings."""
    leaderboard = await get_referral_leaderboard(db, limit=limit)
    return {
        "items": leaderboard,
        "total": len(leaderboard),
    }


@router.post("/claim")
async def claim_earnings(
    amount_kes: float | None = Query(None, description="Amount to claim, or null for all"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim referral earnings as account credit / payout."""
    result = await claim_referral_earnings(db, current_user.id, amount_kes)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/admin/summary")
async def admin_referral_summary(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin view: top-level referral program stats."""
    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from app.models.enterprise import Payout
    from app.models.referral import Referral, ReferralReward

    # Total referral signups
    total_signups = await db.execute(sa_select(sa_func.count(Referral.id)))
    total_signups = total_signups.scalar_one()

    # Total conversions
    total_conversions = await db.execute(
        sa_select(sa_func.count(Referral.id)).where(Referral.status == "converted")
    )
    total_conversions = total_conversions.scalar_one()

    # Total rewards paid out
    total_rewards = await db.execute(
        sa_select(sa_func.coalesce(sa_func.sum(ReferralReward.amount_kes), 0))
    )
    total_rewards = float(total_rewards.scalar_one())

    # Total payouts made
    total_payouts = await db.execute(
        sa_select(sa_func.coalesce(sa_func.sum(Payout.amount_kes), 0)).where(
            Payout.type == "referral_reward",
            Payout.status == "completed",
        )
    )
    total_payouts = float(total_payouts.scalar_one())

    # Active referrers (users who referred at least 1 person)
    active_referrers = await db.execute(
        sa_select(sa_func.count(sa_func.distinct(Referral.referrer_id)))
    )
    active_referrers = active_referrers.scalar_one()

    return {
        "total_signups": total_signups,
        "total_conversions": total_conversions,
        "conversion_rate_pct": round((total_conversions / max(total_signups, 1)) * 100, 1),
        "total_rewards_kes": total_rewards,
        "total_payouts_kes": total_payouts,
        "active_referrers": active_referrers,
    }
