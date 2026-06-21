"""
Trust Scoring Engine — 6-dimension trust profiles for genuine users.

Scores identity, transaction history, community reputation, property
verification, response time, and dispute history.  Cached in Redis.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_, select

from app.core.redis import cache_delete, cache_get, cache_set
from app.models.analytics import UserEvent
from app.models.document import Document, Verification, VerificationStatus
from app.models.payment import Payment, PaymentStatus
from app.models.property import AgentProfile, Property, PropertyStatus
from app.models.trust_safety import (
    Dispute,
    DisputeStatus,
    EscrowStatus,
    EscrowTransaction,
    FraudReport,
    FraudReportStatus,
    Review,
)
from app.models.user import User, UserRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# ── Constants ──────────────────────────────────────────────────────────────────
CACHE_TTL = 900           # 15 minutes
CACHE_PREFIX = "vestra:trust"

# Dimension weights (must sum to 1.0)
W_IDENTITY = 0.20
W_TRANSACTION = 0.25
W_REPUTATION = 0.20
W_PROP_VERIFICATION = 0.15
W_RESPONSE_TIME = 0.10
W_DISPUTE = 0.10

BADGE_PLATINUM = 90.0
BADGE_GOLD = 75.0
BADGE_SILVER = 60.0
BADGE_BRONZE = 40.0


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════


async def compute_user_trust_score(
    db: AsyncSession, user_id: int, *, use_cache: bool = True,
) -> dict:
    """Compute the full 6-dimension trust score for *user_id*.

    Results cached in Redis for 15 min; pass ``use_cache=False`` to force fresh.
    """
    cache_key = f"{CACHE_PREFIX}:user:{user_id}"
    if use_cache:
        cached = await cache_get(cache_key)
        if cached:
            return cached

    scores = await asyncio.gather(
        _score_identity(db, user_id),
        _score_transaction_history(db, user_id),
        _score_community_reputation(db, user_id),
        _score_property_verification(db, user_id),
        _score_response_time(db, user_id),
        _score_dispute_history(db, user_id),
    )

    overall = max(0.0, min(100.0, round(
        scores[0]["score"] * W_IDENTITY + scores[1]["score"] * W_TRANSACTION +
        scores[2]["score"] * W_REPUTATION + scores[3]["score"] * W_PROP_VERIFICATION +
        scores[4]["score"] * W_RESPONSE_TIME + scores[5]["score"] * W_DISPUTE, 1,
    )))

    result = {
        "user_id": user_id,
        "overall_score": overall,
        "badge": _resolve_badge(overall),
        "dimensions": {
            "identity": scores[0],
            "transaction_history": scores[1],
            "community_reputation": scores[2],
            "property_verification": scores[3],
            "response_time": scores[4],
            "dispute_history": scores[5],
        },
        "risk_flags": _collect_risk_flags(*scores),
        "computed_at": datetime.now(UTC).isoformat(),
    }
    await cache_set(cache_key, result, ttl=CACHE_TTL)
    logger.info('{"event":"trust_score_computed","user_id":%d,"overall_score":%.1f,"badge":"%s"}', user_id, overall, result["badge"])
    return result


async def get_bulk_user_trust_scores(
    db: AsyncSession,
    user_ids: list[int],
    *,
    use_cache: bool = True,
) -> list[dict]:
    """Batch-compute trust scores for multiple users concurrently."""
    tasks = [compute_user_trust_score(db, uid, use_cache=use_cache) for uid in user_ids]
    return await asyncio.gather(*tasks)


async def invalidate_user_trust_cache(user_id: int) -> None:
    """Invalidate a user's cached trust score (call after profile/transaction changes)."""
    await cache_delete(f"{CACHE_PREFIX}:user:{user_id}")
    logger.info('{"event":"trust_cache_invalidated","user_id":%d}', user_id)


async def get_trust_scores_for_role(
    db: AsyncSession,
    role: UserRole,
    limit: int = 50,
) -> list[dict]:
    """Return trust scores for all active users with *role*, newest first."""
    result = await db.execute(
        select(User.id)
        .where(User.role == role, User.is_active.is_(True))
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    return await get_bulk_user_trust_scores(db, result.scalars().all(), use_cache=True)


async def get_trust_dashboard_stats(db: AsyncSession) -> dict:
    """Aggregate trust stats for admin dashboard (samples first 200 active users)."""
    sample_ids = (await db.execute(
        select(User.id).where(User.is_active.is_(True)).limit(200)
    )).scalars().all()
    if not sample_ids:
        return {"total_users": 0, "badge_distribution": {}, "average_overall_score": 0.0, "flagged_users_count": 0, "average_score_by_role": {}}

    profiles = await get_bulk_user_trust_scores(db, sample_ids, use_cache=True)
    badge_dist: dict[str, int] = {}
    total_score = 0.0
    flagged = 0
    scores_by_role: dict[str, list[float]] = {}

    for p in profiles:
        badge_dist[p["badge"]] = badge_dist.get(p["badge"], 0) + 1
        total_score += p["overall_score"]
        if p["risk_flags"]:
            flagged += 1
        role_val = (await db.execute(select(User.role).where(User.id == p["user_id"]))).scalar_one_or_none()
        if role_val is not None:
            scores_by_role.setdefault(role_val.value if hasattr(role_val, "value") else str(role_val), []).append(p["overall_score"])

    return {
        "total_users": (await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))).scalar_one(),
        "badge_distribution": badge_dist,
        "average_overall_score": round(total_score / max(1, len(profiles)), 1),
        "flagged_users_count": flagged,
        "average_score_by_role": {r: round(sum(v) / len(v), 1) for r, v in scores_by_role.items() if v},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Dimension scorers
# ═══════════════════════════════════════════════════════════════════════════════


async def _score_identity(db: AsyncSession, user_id: int) -> dict:
    """+30 email, +35 KYC, +20 account-age (ramp 180d), +10 phone, +5 national ID."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        return {"score": 0.0, "details": {"reason": "user_not_found"}}

    score = 0.0
    d: dict[str, Any] = {}
    if user.is_verified:
        score += 30.0
    if user.is_kyc_verified:
        score += 35.0
    if user.created_at:
        age = (datetime.now(UTC) - user.created_at).days
        score += min(20.0, (age / 180.0) * 20.0)
        d["account_age_days"] = age
    if user._phone:
        score += 10.0
        d["has_phone"] = True
    if user._national_id:
        score += 5.0
        d["has_national_id"] = True
    d.update(email_verified=user.is_verified, kyc_verified=user.is_kyc_verified)
    return {"score": round(score, 1), "details": d}


async def _score_transaction_history(db: AsyncSession, user_id: int) -> dict:
    """+25 per completed escrow (max 50), +5 per payment (max 30), -20 x fail rate, volume bonus."""
    escrow_n = (await db.execute(
        select(func.count(EscrowTransaction.id)).where(
            EscrowTransaction.status == EscrowStatus.completed,
            or_(EscrowTransaction.buyer_id == user_id, EscrowTransaction.seller_id == user_id),
        )
    )).scalar_one() or 0

    pr = (await db.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.user_id == user_id, Payment.status == PaymentStatus.completed)
    )).one()
    completed_payments, total_volume = pr[0] or 0, float(pr[1] or 0.0)

    failed_n = (await db.execute(
        select(func.count(Payment.id)).where(Payment.user_id == user_id, Payment.status == PaymentStatus.failed)
    )).scalar_one() or 0

    total_all = completed_payments + failed_n
    fail_rate = failed_n / total_all if total_all > 0 else 0.0
    vol_bonus = 20.0 if total_volume >= 10_000_000 else (10.0 if total_volume >= 5_000_000 else (5.0 if total_volume >= 1_000_000 else 0.0))

    score = max(0.0, min(100.0, escrow_n * 25.0 + completed_payments * 5.0 - fail_rate * 20.0 + vol_bonus))
    return {
        "score": round(score, 1),
        "details": {
            "completed_escrows": escrow_n, "completed_payments": completed_payments,
            "failed_payments": failed_n, "total_volume_kes": total_volume, "failure_rate": round(fail_rate, 3),
        },
    }


async def _score_community_reputation(db: AsyncSession, user_id: int) -> dict:
    """0-60 from rating avg, 0-15 volume, 0-10 verified-txn ratio, 0-15 agent deal-ratio."""
    row = (await db.execute(
        select(func.count(Review.id), func.avg(Review.rating),
               func.count(Review.id).filter(Review.is_verified_transaction.is_(True)))
        .where(Review.subject_id == user_id)
    )).one()
    total, avg_r, verified = row[0] or 0, float(row[1] or 0.0), row[2] or 0
    if total == 0:
        return {"score": 50.0, "details": {"total_reviews": 0, "reason": "insufficient_data"}}

    agent = (await db.execute(
        select(AgentProfile.successful_deals, AgentProfile.total_listings).where(AgentProfile.user_id == user_id)
    )).one_or_none()

    agent_bonus = 0.0
    if agent and agent.total_listings and agent.total_listings > 0:
        agent_bonus = min(15.0, ((agent.successful_deals or 0) / agent.total_listings) * 15.0)

    score = min(100.0, (avg_r / 5.0) * 60.0 + min(15.0, total * 2.5) + (verified / total) * 10.0 + agent_bonus)
    return {
        "score": round(score, 1),
        "details": {"total_reviews": total, "average_rating": round(avg_r, 2),
                     "verified_reviews": verified, "successful_deals": agent.successful_deals if agent else 0},
    }


async def _score_property_verification(db: AsyncSession, user_id: int) -> dict:
    """+40 x verified ratio, +30 x avg trust/100, +15 docs, +15 AI approval ratio."""
    props = (await db.execute(
        select(Property).where(Property.owner_id == user_id, Property.is_deleted.is_(False),
                               Property.status.in_([PropertyStatus.active, PropertyStatus.pending_review]))
    )).scalars().all()
    total = len(props)
    if total == 0:
        return {"score": 50.0, "details": {"total_properties": 0, "reason": "no_listings"}}

    verified = sum(1 for p in props if p.is_verified)
    trust_scores = [p.trust_score for p in props if p.trust_score is not None]
    avg_trust = statistics.mean(trust_scores) if trust_scores else 0.0
    pids = [p.id for p in props]

    doc_n = (await db.execute(
        select(func.count(Document.id)).where(Document.property_id.in_(pids), Document.is_deleted.is_(False))
    )).scalar_one() or 0
    ai_n = (await db.execute(
        select(func.count(Verification.id)).where(Verification.property_id.in_(pids), Verification.status == VerificationStatus.approved)
    )).scalar_one() or 0

    score = min(100.0, (verified / total) * 40.0 + (avg_trust / 100.0) * 30.0 + min(15.0, (doc_n / total) * 5.0) + (ai_n / total) * 15.0)
    return {"score": round(score, 1), "details": {"total_properties": total, "verified_properties": verified,
             "average_trust_score": round(avg_trust, 1), "documents_uploaded": doc_n, "approved_verifications": ai_n}}


async def _score_response_time(db: AsyncSession, user_id: int) -> dict:
    """Median response hours (0-100).  Falls back to account-update recency."""
    def _rt(hrs: float) -> float:
        return 100.0 if hrs <= 1 else (80.0 if hrs <= 4 else (60.0 if hrs <= 12 else (40.0 if hrs <= 24 else (20.0 if hrs <= 48 else 0.0))))

    events = (await db.execute(
        select(UserEvent.event_data).where(UserEvent.user_id == user_id, UserEvent.event_type == "response")
        .order_by(UserEvent.created_at.desc()).limit(50)
    )).scalars().all()

    if events:
        times = [float(d["response_time_hours"]) for d in events if d and d.get("response_time_hours")]
        if times:
            med = statistics.median(times)
            return {"score": _rt(med), "details": {"median_response_time_hours": round(med, 1), "responses_measured": len(times)}}

    updated_at = (await db.execute(select(User.updated_at).where(User.id == user_id))).scalar_one_or_none()
    if updated_at:
        hrs = (datetime.now(UTC) - updated_at).total_seconds() / 3600
        return {"score": _rt(hrs), "details": {"hours_since_last_activity": round(hrs, 1), "proxy": True}}

    return {"score": 50.0, "details": {"reason": "insufficient_data"}}


async def _score_dispute_history(db: AsyncSession, user_id: int) -> dict:
    """-30 per open dispute, -20 resolved-guilty, -25 confirmed fraud. +10 clean bonus."""
    disputes = (await db.execute(
        select(Dispute).where(Dispute.subject_id == user_id, Dispute.subject_type == "user")
    )).scalars().all()

    open_n = sum(1 for d in disputes if d.status in (DisputeStatus.open, DisputeStatus.investigating))
    guilty_n = sum(1 for d in disputes if d.status == DisputeStatus.resolved and d.resolution and "guilty" in d.resolution.lower())

    user_row = (await db.execute(select(User._phone, User.email).where(User.id == user_id))).one_or_none()
    fraud_n = 0
    if user_row:
        conds = []
        if user_row._phone:
            conds.append(FraudReport.reported_phone == user_row._phone)
        if user_row.email:
            conds.append(FraudReport.reported_email == user_row.email)
        if conds:
            fraud_n = (await db.execute(
                select(func.count(FraudReport.id)).where(FraudReport.status == FraudReportStatus.confirmed, or_(*conds))
            )).scalar_one() or 0

    score = max(0.0, 100.0 - (open_n * 30.0 + guilty_n * 20.0 + fraud_n * 25.0))
    if open_n == 0 and guilty_n == 0 and fraud_n == 0:
        score = min(100.0, score + 10.0)

    return {"score": round(score, 1), "details": {"open_disputes": open_n, "resolved_guilty": guilty_n,
             "confirmed_fraud_reports": fraud_n, "total_disputes": len(disputes)}}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _resolve_badge(overall_score: float) -> str:
    if overall_score >= BADGE_PLATINUM:
        return "platinum"
    if overall_score >= BADGE_GOLD:
        return "gold"
    if overall_score >= BADGE_SILVER:
        return "silver"
    if overall_score >= BADGE_BRONZE:
        return "bronze"
    return "untrusted"


def _collect_risk_flags(*dimensions: dict) -> list[str]:
    """Collect risk flags from all dimension score dicts."""
    flags: list[str] = []
    for dim in dimensions:
        d = dim.get("details", {})
        if d.get("failure_rate", 0) > 0.5:
            flags.append("high_payment_failure_rate")
        if d.get("open_disputes", 0) > 0:
            flags.append("has_open_disputes")
        if d.get("confirmed_fraud_reports", 0) > 0:
            flags.append("confirmed_fraud_reports")
        if d.get("failed_payments", 0) > 3:
            flags.append("repeated_failed_payments")
        if d.get("reason") == "no_listings" and dim.get("score", 100) < 50:
            flags.append("no_listings_trust_penalty")
        acct_age = d.get("account_age_days")
        if acct_age is not None and acct_age < 7:
            flags.append("new_account")
    return flags
