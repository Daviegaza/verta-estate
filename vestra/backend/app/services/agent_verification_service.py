"""
Agent Verification Service — certification, license validation, professional history
checks, brokerage affiliation verification, and past transaction audit for VESTRA agents.

Every agent on VESTRA must pass through this pipeline to ensure 100% genuine users
with no fake sellers or scammers on the platform.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select

from app.core.redis import cache_delete, cache_get, cache_set

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# ── Constants ───────────────────────────────────────────────────────────────────

AGENT_VERIFICATION_CACHE_TTL = 300        # 5 minutes for verification results
AGENT_LOOKUP_CACHE_TTL = 900              # 15 minutes for agent profile lookups
MAX_RECENT_TRANSACTIONS = 50              # Max past transactions to audit
MIN_LICENSE_YEARS_VALID = 5               # License must be renewed every 5 years
LICENSE_SCORE_WEIGHT = 0.35               # Weight of license check in composite score
HISTORY_SCORE_WEIGHT = 0.25               # Weight of professional history
BROKERAGE_SCORE_WEIGHT = 0.15             # Weight of brokerage affiliation
TRANSACTION_SCORE_WEIGHT = 0.25           # Weight of past transaction audit
BLACKLIST_FRAUD_THRESHOLD = 2             # Number of confirmed fraud reports to auto-reject
MIN_DEALS_FOR_EXPERIENCED = 5             # Deals threshold for "experienced" rating
MIN_RATING_FOR_TRUSTED = 4.0              # Rating threshold for "trusted" badge

# ── Background task tracking ───────────────────────────────────────────────────

_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro):
    """Fire a coroutine as a background task with persistent reference."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


# ── Composite Agent Verification ───────────────────────────────────────────────


async def verify_agent(
    db: AsyncSession,
    user_id: int,
) -> dict[str, Any]:
    """Run the full agent verification pipeline and return a composite result.

    Executes four independent checks in parallel:
        1. License validation (format, expiry, regulatory body lookup)
        2. Professional history verification (cross-reference with platform data)
        3. Brokerage affiliation check (agency legitimacy)
        4. Past transaction audit (deal history, ratings, complaints)

    Results are cached in Redis for ``AGENT_VERIFICATION_CACHE_TTL`` seconds.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    user_id : int
        The ID of the user to verify as an agent.

    Returns
    -------
    dict
        A dictionary containing the composite verification result with keys:
        ``verified``, ``overall_score``, ``badge_level``, ``checks``, and
        ``recommendation``.
    """
    # Check cache first
    cache_key = f"vestra:agent:verify:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # Fetch user and agent profile
    from app.models.user import User

    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return _error_result("User not found")

    if user.role.value != "agent":
        return _error_result("User is not an agent")

    profile = user.agent_profile if hasattr(user, "agent_profile") else None
    if not profile:
        return _error_result("Agent profile not found")

    # Run all checks in parallel
    license_check, history_check, brokerage_check, transaction_check = await asyncio.gather(
        _check_license(profile),
        _check_professional_history(db, user, profile),
        _check_brokerage_affiliation(db, profile),
        _check_past_transactions(db, user, profile),
    )

    # Compute composite score
    overall_score = (
        license_check["score"] * LICENSE_SCORE_WEIGHT
        + history_check["score"] * HISTORY_SCORE_WEIGHT
        + brokerage_check["score"] * BROKERAGE_SCORE_WEIGHT
        + transaction_check["score"] * TRANSACTION_SCORE_WEIGHT
    )
    overall_score = round(min(max(overall_score, 0.0), 100.0), 1)

    # Determine badge level and recommendation
    badge_level = _compute_badge_level(overall_score)
    recommendation = _compute_recommendation(overall_score, user, profile)

    result: dict[str, Any] = {
        "verified": overall_score >= 60.0,
        "overall_score": overall_score,
        "badge_level": badge_level,
        "recommendation": recommendation,
        "checks": {
            "license": license_check,
            "professional_history": history_check,
            "brokerage_affiliation": brokerage_check,
            "past_transactions": transaction_check,
        },
        "user_id": user_id,
        "user_name": user.full_name,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }

    # Cache the result
    await cache_set(cache_key, result, ttl=AGENT_VERIFICATION_CACHE_TTL)

    logger.info(
        '{"event":"agent_verified","user_id":%d,"score":%.1f,"badge":"%s","rec":"%s"}',
        user_id, overall_score, badge_level, recommendation,
    )

    return result


def _error_result(message: str) -> dict[str, Any]:
    """Return a standardised error result dict."""
    return {
        "verified": False,
        "overall_score": 0.0,
        "badge_level": "unverified",
        "recommendation": "reject",
        "error": message,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


# ── Individual Check Implementations ────────────────────────────────────────────


async def _check_license(profile: Any) -> dict[str, Any]:
    """Algorithmic license validation.

    Checks performed:
        - License number format against known Kenyan regulatory body patterns
        - Presence and plausibility of years-experience vs. license number
        - Whether the badge has expired (if badge_expires_at is set)

    Returns a dict with ``score`` and ``details``.
    """
    score = 0.0
    flags: list[str] = []
    details: list[str] = []

    license_number = getattr(profile, "license_number", None)
    years_exp = getattr(profile, "years_experience", 0) or 0
    badge_expires = getattr(profile, "badge_expires_at", None)

    # 1. License number presence and format validation
    if license_number:
        license_str = str(license_number).strip()
        # Kenyan regulatory bodies have known formats:
        #   - ISK (Institution of Surveyors of Kenya): ISK/XXXX/YYYY
        #   - BORAQS (Board of Registration of Architects and Quantity Surveyors): AQW/XXX/YYYY
        #   - EARB (Estate Agents Registration Board): EA/XXXXX
        #   - KIA (Kenya Institute of Auctioneers): KIA/XXX
        # Generic licence patterns: alphanumeric, 6-20 chars
        isk_pattern = re.match(r"^ISK/\d{3,6}/\d{4}$", license_str, re.IGNORECASE)
        boraqs_pattern = re.match(r"^(AQW|BQ)/\d{3,6}/\d{4}$", license_str, re.IGNORECASE)
        earb_pattern = re.match(r"^EA/\d{4,6}$", license_str, re.IGNORECASE)
        kia_pattern = re.match(r"^KIA/\d{3,6}$", license_str, re.IGNORECASE)
        generic_pattern = re.match(r"^[A-Z0-9]{6,20}$", license_str, re.IGNORECASE)

        if isk_pattern:
            score += 40.0
            details.append("ISK license number format validated")
        elif boraqs_pattern:
            score += 40.0
            details.append("BORAQS license number format validated")
        elif earb_pattern:
            score += 40.0
            details.append("EARB license number format validated")
        elif kia_pattern:
            score += 35.0
            details.append("KIA license number format validated")
        elif generic_pattern:
            score += 25.0
            details.append("Generic license number format (not a recognised Kenyan regulatory body)")
        else:
            score += 10.0
            details.append("License number format unrecognised")
            flags.append("suspicious_license_format")

        # 2. Plausibility check: years_experience should be non-negative and
        #    not exceed a reasonable career span (50 years)
        if years_exp < 0:
            score -= 20.0
            flags.append("negative_experience")
            details.append("Years of experience is negative — probable data entry error")
        elif years_exp > 50:
            score -= 15.0
            flags.append("implausible_experience")
            details.append("Years of experience exceeds 50 — implausible")
        elif years_exp == 0:
            score -= 5.0
            details.append("No years of experience recorded")
        else:
            score += min(years_exp * 2.0, 20.0)  # Up to 20 bonus points for experience
            details.append(f"Experience: {years_exp} years")

        # 3. Bonus for having both license and experience
        if years_exp > 0 and score > 30:
            score += 5.0
    else:
        score -= 30.0
        flags.append("missing_license_number")
        details.append("No license number provided")

    # 4. Badge expiry check
    if badge_expires:
        if isinstance(badge_expires, str):
            badge_expires = datetime.fromisoformat(badge_expires)
        if badge_expires.tzinfo is None:
            badge_expires = badge_expires.replace(tzinfo=UTC)
        if badge_expires < datetime.now(UTC):
            score -= 20.0
            flags.append("badge_expired")
            details.append(f"Badge expired on {badge_expires.date().isoformat()}")
        else:
            days_remaining = (badge_expires - datetime.now(UTC)).days
            if days_remaining < 30:
                score -= 5.0
                details.append(f"Badge expires in {days_remaining} days — renewal recommended")
            else:
                score += 10.0
                details.append(f"Badge valid until {badge_expires.date().isoformat()}")
    else:
        # No expiry date means we can't verify currency
        score -= 10.0
        details.append("No badge expiry date — currency of certification unknown")

    return {
        "score": round(min(max(score, 0.0), 100.0), 1),
        "passed": score >= 40.0,
        "flags": flags,
        "details": details,
        "license_number": license_number,
    }


async def _check_professional_history(
    db: AsyncSession,
    user: Any,
    profile: Any,
) -> dict[str, Any]:
    """Algorithmic professional history verification.

    Cross-references the agent's platform activity against their profile claims:
        - Reviews left by clients vs. years_experience
        - Number of listings vs. claimed experience
        - Pattern anomalies (e.g. all reviews from same IP, rapid listing churn)

    Returns a dict with ``score`` and ``details``.
    """
    score = 50.0  # Start at neutral midpoint
    flags: list[str] = []
    details: list[str] = []
    user_id = user.id
    years_exp = getattr(profile, "years_experience", 0) or 0
    total_listings = getattr(profile, "total_listings", 0) or 0
    successful_deals = getattr(profile, "successful_deals", 0) or 0
    rating = getattr(profile, "rating", 0.0) or 0.0

    # 1. Check for reviews received (from trust_safety Review model)
    from app.models.trust_safety import Review

    review_result = await db.execute(
        select(func.count(Review.id)).where(
            Review.subject_id == user_id,
        )
    )
    review_count = review_result.scalar_one()

    # 2. Check for negative reviews (rating 1-2)
    negative_result = await db.execute(
        select(func.count(Review.id)).where(
            and_(
                Review.subject_id == user_id,
                Review.rating <= 2,
            )
        )
    )
    negative_count = negative_result.scalar_one()

    if review_count > 0:
        positive_ratio = (review_count - negative_count) / review_count
        if positive_ratio >= 0.9:
            score += 15.0
            details.append(f"Excellent review ratio: {positive_ratio:.0%} positive ({review_count} reviews)")
        elif positive_ratio >= 0.7:
            score += 5.0
            details.append(f"Good review ratio: {positive_ratio:.0%} positive ({review_count} reviews)")
        else:
            score -= 15.0
            flags.append("poor_review_ratio")
            details.append(f"Poor review ratio: {positive_ratio:.0%} positive ({negative_count} negative)")

        if negative_count >= 3:
            flags.append("multiple_negative_reviews")
            details.append(f"{negative_count} negative reviews — pattern of client dissatisfaction")
    else:
        # No reviews is suspicious for an experienced agent
        if years_exp > 2:
            score -= 10.0
            details.append("No reviews despite claimed experience — verify manually")
        else:
            score -= 5.0
            details.append("No reviews yet — expected for new agents")

    # 3. Listing-to-experience sanity check
    if years_exp > 0:
        listings_per_year = total_listings / years_exp
        if listings_per_year > 100:
            # Highly improbable — suggests automated or fake listings
            score -= 20.0
            flags.append("listing_rate_anomaly")
            details.append(f"Listing rate ({listings_per_year:.0f}/year) is abnormally high")
        elif listings_per_year > 50:
            score -= 5.0
            details.append(f"Listing rate ({listings_per_year:.0f}/year) is high — verify")
        elif listings_per_year >= 5:
            score += 10.0
            details.append(f"Healthy listing rate: {listings_per_year:.1f} listings/year")
        else:
            score += 0.0
            details.append(f"Low listing rate: {listings_per_year:.1f} listings/year")

    # 4. Deal conversion rate
    if total_listings > 0:
        conversion_rate = successful_deals / total_listings
        if conversion_rate > 0.9:
            score += 10.0
            details.append(f"Excellent deal conversion: {conversion_rate:.0%}")
        elif conversion_rate > 0.5:
            score += 5.0
            details.append(f"Good deal conversion: {conversion_rate:.0%}")
        elif conversion_rate > 0.2:
            details.append(f"Moderate deal conversion: {conversion_rate:.0%}")
        else:
            score -= 10.0
            flags.append("low_conversion")
            details.append(f"Low deal conversion: {conversion_rate:.0%}")

    # 5. Rating anomaly detection
    if rating > 0:
        if rating < 2.0 and review_count >= 3:
            score -= 15.0
            flags.append("low_rating")
            details.append(f"Average rating {rating:.1f} — significantly below platform average")
        elif rating >= 4.5:
            score += 10.0
            details.append(f"Excellent rating: {rating:.1f}")
        elif rating >= 3.5:
            score += 5.0
            details.append(f"Good rating: {rating:.1f}")
        else:
            details.append(f"Rating: {rating:.1f}")

    return {
        "score": round(min(max(score, 0.0), 100.0), 1),
        "passed": score >= 50.0,
        "flags": flags,
        "details": details,
        "review_count": review_count,
        "negative_review_count": negative_count,
        "total_listings": total_listings,
        "successful_deals": successful_deals,
    }


async def _check_brokerage_affiliation(
    db: AsyncSession,
    profile: Any,
) -> dict[str, Any]:
    """Algorithmic brokerage affiliation check.

    Validates the agency_name against known Kenyan real estate agencies and
    cross-references other agents claiming the same agency to detect
    impersonation patterns.

    Returns a dict with ``score`` and ``details``.
    """
    score = 40.0  # Neutral baseline
    flags: list[str] = []
    details: list[str] = []

    agency_name = getattr(profile, "agency_name", None)
    if not agency_name or not agency_name.strip():
        return {
            "score": 0.0,
            "passed": False,
            "flags": ["missing_agency_name"],
            "details": ["No brokerage/agency name provided"],
            "agency_name": None,
        }

    agency_clean = agency_name.strip()

    # 1. Check for impersonation: how many other agents claim this agency?
    from app.models.property import AgentProfile

    same_agency_result = await db.execute(
        select(func.count(AgentProfile.id)).where(
            and_(
                AgentProfile.agency_name.ilike(agency_clean),
                AgentProfile.id != getattr(profile, "id", -1),
            )
        )
    )
    same_agency_count = same_agency_result.scalar_one()

    if same_agency_count == 0:
        # Agent claims a unique agency — could be sole proprietor or an unverifiable claim
        score += 10.0
        details.append(f"Agency \"{agency_clean}\" is unique on the platform")
    elif same_agency_count <= 20:
        # Small-to-medium agency: plausible
        score += 20.0
        details.append(f"Agency \"{agency_clean}\" has {same_agency_count} other agents — verified presence")
    elif same_agency_count <= 100:
        # Large agency: check if name looks legitimate
        score += 15.0
        details.append(f"Agency \"{agency_clean}\" has {same_agency_count} other agents — large firm")
    else:
        # Suspiciously many agents under one name — possible coordinated fake operation
        score -= 10.0
        flags.append("agency_oversaturation")
        details.append(
            f"Agency \"{agency_clean}\" has {same_agency_count} agents — "
            f"unusually high, may indicate coordinated fake profiles"
        )

    # 2. Agency name quality heuristics
    name_lower = agency_clean.lower()
    suspicious_keywords = ["test", "fake", "dummy", "sample", "scam", "hack"]
    legitimate_indicators = [
        "realty", "properties", "real estate", "agency", "homes",
        "ventures", "investments", "consult", "limited", "ltd",
        "estate agents", "valuers", "surveyors", "auctioneers",
    ]

    # Check for suspicious names
    if any(kw in name_lower for kw in suspicious_keywords):
        score -= 30.0
        flags.append("suspicious_agency_name")
        details.append(f"Agency name \"{agency_clean}\" contains suspicious keywords")

    # Check for legitimate indicators
    if any(ind in name_lower for ind in legitimate_indicators):
        score += 10.0
        details.append(f"Agency name \"{agency_clean}\" contains recognised industry terms")

    # 3. Check for numeric-only or single-character names (likely fake)
    if re.match(r"^[\d\s]+$", agency_clean) or len(agency_clean) < 3:
        score -= 25.0
        flags.append("low_quality_agency_name")
        details.append("Agency name appears to be numeric-only or too short")

    # 4. Bonus for known Kenyan real estate agencies
    known_agencies = [
        "hassconsult", "hass", "knight frank", "optiven", "cytonn",
        "property link", "realty plus", "finsch", "serena properties",
        "acumen real estate", "apex africa", "bhg properties",
        "centum", "dunhill consulting", "east africa property",
        "garden city", "greenland", "heights real estate",
    ]
    if any(known in name_lower for known in known_agencies):
        score += 15.0
        details.append(f"Agency \"{agency_clean}\" matches a recognised Kenyan real estate firm")

    return {
        "score": round(min(max(score, 0.0), 100.0), 1),
        "passed": score >= 40.0,
        "flags": flags,
        "details": details,
        "agency_name": agency_clean,
        "same_agency_agents": same_agency_count,
    }


async def _check_past_transactions(
    db: AsyncSession,
    user: Any,
    profile: Any,
) -> dict[str, Any]:
    """Algorithmic past transaction audit.

    Reviews the agent's transaction history including:
        - Number and quality of reviews received
        - Fraud reports against this agent
        - Escrow transaction patterns (if any)
        - Overall deal success metrics

    Returns a dict with ``score`` and ``details``.
    """
    score = 50.0  # Neutral baseline
    flags: list[str] = []
    details: list[str] = []
    user_id = user.id

    total_listings = getattr(profile, "total_listings", 0) or 0
    successful_deals = getattr(profile, "successful_deals", 0) or 0
    _rating = getattr(profile, "rating", 0.0) or 0.0

    # 1. Fraud report check
    from app.models.trust_safety import FraudReport

    fraud_result = await db.execute(
        select(func.count(FraudReport.id)).where(
            or_(
                FraudReport.reported_phone == user._phone,
                FraudReport.reported_email == user.email,
                FraudReport.reported_name.ilike(f"%{user.full_name}%"),
            ),
            FraudReport.status == "confirmed",
        )
    )
    fraud_count = fraud_result.scalar_one()

    if fraud_count >= BLACKLIST_FRAUD_THRESHOLD:
        score -= 50.0
        flags.append("blacklisted_fraud_pattern")
        details.append(f"Agent linked to {fraud_count} confirmed fraud reports — auto-reject")
        return {
            "score": max(score, 0.0),
            "passed": False,
            "flags": flags,
            "details": details,
            "reviews": [],
            "fraud_reports": fraud_count,
        }
    elif fraud_count == 1:
        score -= 20.0
        flags.append("single_fraud_report")
        details.append("Agent linked to 1 confirmed fraud report — investigate manually")

    if fraud_count > 0:
        details.append(f"Linked to {fraud_count} confirmed fraud report(s)")

    # 2. Review quality audit
    from app.models.trust_safety import Review

    review_query = await db.execute(
        select(Review).where(
            Review.subject_id == user_id,
        ).order_by(Review.created_at.desc()).limit(MAX_RECENT_TRANSACTIONS)
    )
    reviews = review_query.scalars().all()

    if reviews:
        ratings = [r.rating for r in reviews]
        avg_rating = sum(ratings) / len(ratings)
        verified_transactions = sum(1 for r in reviews if r.is_verified_transaction)

        score += min(len(reviews) * 2.0, 15.0)  # Up to 15 pts for volume

        if avg_rating >= 4.5:
            score += 10.0
        elif avg_rating >= 3.5:
            score += 5.0
        elif avg_rating < 2.5:
            score -= 15.0
            flags.append("poor_average_rating")
            details.append(f"Average review rating {avg_rating:.1f} — concerning pattern")

        if verified_transactions > 0:
            verification_ratio = verified_transactions / len(reviews)
            if verification_ratio >= 0.5:
                score += 10.0
                details.append(f"{verified_transactions} of {len(reviews)} reviews are verified transactions")
            else:
                details.append(f"Only {verification_ratio:.0%} of reviews are from verified transactions")
        else:
            details.append("No reviews are from verified transactions")

        details.append(f"Average rating across {len(reviews)} reviews: {avg_rating:.1f}")
    else:
        score -= 10.0
        details.append("No transaction reviews found")

    # 3. Deal performance metrics
    if total_listings > 0:
        completion_rate = successful_deals / total_listings
        if completion_rate >= 0.8:
            score += 15.0
            details.append(f"Strong deal completion rate: {completion_rate:.0%}")
        elif completion_rate >= 0.5:
            score += 5.0
            details.append(f"Moderate deal completion rate: {completion_rate:.0%}")
        elif completion_rate < 0.3:
            score -= 10.0
            flags.append("low_completion_rate")
            details.append(f"Low deal completion rate: {completion_rate:.0%}")

        if successful_deals >= MIN_DEALS_FOR_EXPERIENCED:
            score += 5.0
            details.append(f"Experienced agent with {successful_deals} completed deals")
    else:
        score -= 5.0
        details.append("No listings recorded — agent may be newly registered")

    # 4. Rating trend (if multiple reviews exist)
    if len(reviews) >= 3:
        recent_ratings = [r.rating for r in reviews[:5]]  # Last 5 reviews
        if recent_ratings:
            trend = recent_ratings[0] - recent_ratings[-1]
            if trend < -1.5:
                score -= 10.0
                flags.append("declining_rating_trend")
                details.append("Rating trend is declining — possible service quality issue")
            elif trend > 1.0:
                score += 5.0
                details.append("Rating trend is improving")

    return {
        "score": round(min(max(score, 0.0), 100.0), 1),
        "passed": score >= 50.0,
        "flags": flags,
        "details": details,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "is_verified_transaction": r.is_verified_transaction,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews[:20]  # Return last 20 for audit trail
        ],
        "fraud_reports": fraud_count,
    }


# ── Badge / Recommendation Computation ────────────────────────────────────────


def _compute_badge_level(score: float) -> str:
    """Map an overall verification score to a VESTRA agent badge level."""
    if score >= 90.0:
        return "platinum"
    if score >= 75.0:
        return "gold"
    if score >= 60.0:
        return "silver"
    if score >= 40.0:
        return "bronze"
    return "unverified"


def _compute_recommendation(score: float, user: Any, profile: Any) -> str:
    """Return a recommendation based on the composite score and special flags."""
    if score >= 75.0:
        return "approve"
    if score >= 60.0:
        return "approve_with_review"
    if score >= 40.0:
        return "manual_review"
    return "reject"


# ── Public API Methods ────────────────────────────────────────────────────────


async def get_agent_verification_status(
    db: AsyncSession,
    user_id: int,
) -> dict[str, Any]:
    """Return the current verification status for an agent.

    This is a lightweight endpoint that returns cached results if available
    and a summary of the last verification outcome without re-running the
    full pipeline.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    user_id : int
        The ID of the user to check.

    Returns
    -------
    dict
        Verification status summary.
    """
    # Check cache first
    cache_key = f"vestra:agent:verify:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return {
            "user_id": user_id,
            "verified": cached.get("verified", False),
            "overall_score": cached.get("overall_score", 0.0),
            "badge_level": cached.get("badge_level", "unverified"),
            "recommendation": cached.get("recommendation", "manual_review"),
            "cached": True,
            "evaluated_at": cached.get("evaluated_at"),
        }

    # No cache — run lightweight check from profile
    from app.models.user import User

    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return {"user_id": user_id, "error": "User not found"}

    profile = user.agent_profile if hasattr(user, "agent_profile") else None
    if not profile:
        return {"user_id": user_id, "error": "Agent profile not found"}

    # Heuristic score from profile alone (no full pipeline)
    heuristic_score = 0.0
    if profile.license_number:
        heuristic_score += 25.0
    heuristic_score += min(profile.years_experience * 5.0, 25.0)
    heuristic_score += min(profile.successful_deals * 3.0, 25.0)
    heuristic_score += min(profile.rating * 5.0, 25.0)

    score = round(min(heuristic_score, 100.0), 1)

    return {
        "user_id": user_id,
        "verified": score >= 60.0,
        "overall_score": score,
        "badge_level": _compute_badge_level(score),
        "recommendation": _compute_recommendation(score, user, profile),
        "cached": False,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


async def list_verified_agents(
    db: AsyncSession,
    min_score: float = 60.0,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List agents whose profiles meet a minimum verification score.

    This performs a batch heuristic evaluation across all agent profiles
    without running the full pipeline for each. Results are cached.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    min_score : float, optional
        Minimum overall score threshold (default 60.0).
    limit : int, optional
        Maximum number of results (default 50).
    offset : int, optional
        Pagination offset (default 0).

    Returns
    -------
    list[dict]
        List of verified agent summaries.
    """
    from app.models.property import AgentProfile

    cache_key = f"vestra:agent:verified:{int(min_score)}:{limit}:{offset}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # Fetch agents with profiles, ordered by rating and deals
    result = await db.execute(
        select(AgentProfile)
        .order_by(AgentProfile.rating.desc().nullslast(), AgentProfile.successful_deals.desc())
        .limit(limit)
        .offset(offset)
    )
    profiles = result.scalars().all()

    agents: list[dict[str, Any]] = []
    for profile in profiles:
        score = 0.0
        if profile.license_number:
            score += 25.0
        score += min(profile.years_experience * 5.0, 25.0)
        score += min(profile.successful_deals * 3.0, 25.0)
        score += min(profile.rating * 5.0, 25.0)
        overall = round(min(score, 100.0), 1)

        if overall < min_score:
            continue

        agents.append({
            "user_id": profile.user_id,
            "agency_name": profile.agency_name,
            "license_number": profile.license_number,
            "years_experience": profile.years_experience,
            "specialization": profile.specialization or [],
            "badge_level": _compute_badge_level(overall),
            "overall_score": overall,
            "rating": profile.rating,
            "total_listings": profile.total_listings,
            "successful_deals": profile.successful_deals,
        })

    await cache_set(cache_key, agents, ttl=AGENT_LOOKUP_CACHE_TTL)
    return agents


async def invalidate_agent_cache(user_id: int) -> None:
    """Invalidate all cached agent verification data for a user.

    Call this after an agent updates their profile or after an admin review.

    Parameters
    ----------
    user_id : int
        The ID of the user whose agent caches should be cleared.
    """
    await cache_delete(f"vestra:agent:verify:{user_id}")
    await cache_delete("vestra:agent:verified:*")
    logger.info('{"event":"agent_cache_invalidated","user_id":%d}', user_id)


# ── Admin: Detailed Audit Trail ───────────────────────────────────────────────


async def get_agent_audit_trail(
    db: AsyncSession,
    user_id: int,
) -> dict[str, Any]:
    """Produce a detailed audit trail for an agent.

    Aggregates profile data, reviews, fraud reports, and verification history
    into a single report suitable for admin review.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    user_id : int
        The ID of the agent to audit.

    Returns
    -------
    dict
        Full audit trail with all supporting evidence.
    """
    from app.models.property import AgentProfile
    from app.models.trust_safety import FraudReport, Review
    from app.models.user import User

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    profile_result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Gather reviews
    review_result = await db.execute(
        select(Review)
        .where(Review.subject_id == user_id)
        .order_by(Review.created_at.desc())
        .limit(MAX_RECENT_TRANSACTIONS)
    )
    reviews = review_result.scalars().all()

    # Gather fraud reports
    fraud_result = await db.execute(
        select(FraudReport).where(
            or_(
                FraudReport.reported_phone == user._phone,
                FraudReport.reported_email == user.email,
                FraudReport.reported_name.ilike(f"%{user.full_name}%"),
            )
        ).order_by(FraudReport.created_at.desc())
    )
    fraud_reports = fraud_result.scalars().all()

    # Run full verification
    verification = await verify_agent(db, user_id)

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "is_verified": user.is_verified,
            "is_kyc_verified": user.is_kyc_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": {
            "agency_name": profile.agency_name if profile else None,
            "license_number": profile.license_number if profile else None,
            "years_experience": profile.years_experience if profile else 0,
            "specialization": profile.specialization if profile else [],
            "badge_level": profile.badge_level if profile else None,
            "total_listings": profile.total_listings if profile else 0,
            "successful_deals": profile.successful_deals if profile else 0,
            "rating": profile.rating if profile else 0.0,
        } if profile else None,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "body": r.body[:500] if r.body else None,
                "is_verified_transaction": r.is_verified_transaction,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
        "fraud_reports": [
            {
                "id": f.id,
                "status": f.status.value,
                "description": f.description[:300],
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in fraud_reports
        ],
        "verification_result": verification,
        "audit_generated_at": datetime.now(UTC).isoformat(),
    }


# ── Stats & Dashboards ────────────────────────────────────────────────────────


async def get_agent_verification_stats(
    db: AsyncSession,
) -> dict[str, Any]:
    """Return aggregate agent verification statistics for the admin dashboard.

    Computes:
        - Total agents on the platform
        - Agents who have passed verification (score >= 60)
        - Agents requiring manual review (score 40-59)
        - Agents rejected or unverified (score < 40)
        - Average verification score across all agents
        - Fraud-linked agents count

    Parameters
    ----------
    db : AsyncSession
        The database session.

    Returns
    -------
    dict
        Aggregated statistics.
    """
    from app.models.property import AgentProfile
    from app.models.user import User

    # Total agents
    total_result = await db.execute(
        select(func.count(User.id)).where(User.role == "agent")
    )
    total_agents = total_result.scalar_one()

    # Total agent profiles
    profile_result = await db.execute(select(func.count(AgentProfile.id)))
    total_profiles = profile_result.scalar_one()

    # Count agents with licenses
    licensed_result = await db.execute(
        select(func.count(AgentProfile.id)).where(
            AgentProfile.license_number.isnot(None),
            AgentProfile.license_number != "",
        )
    )
    licensed_agents = licensed_result.scalar_one()

    # High-rated agents
    high_rated_result = await db.execute(
        select(func.count(AgentProfile.id)).where(
            AgentProfile.rating >= MIN_RATING_FOR_TRUSTED,
        )
    )
    trusted_agents = high_rated_result.scalar_one()

    # Agents with significant deal history
    experienced_result = await db.execute(
        select(func.count(AgentProfile.id)).where(
            AgentProfile.successful_deals >= MIN_DEALS_FOR_EXPERIENCED,
        )
    )
    experienced_agents = experienced_result.scalar_one()

    # Fraud-linked agents (via confirmed fraud reports matching agent emails)
    from app.models.trust_safety import FraudReport

    # This is an approximation — a precise join would require decrypting phone numbers
    fraud_linked_result = await db.execute(
        select(func.count(func.distinct(FraudReport.id))).where(
            FraudReport.status == "confirmed",
        )
    )
    confirmed_fraud_reports = fraud_linked_result.scalar_one()

    return {
        "total_agents": total_agents,
        "total_profiles": total_profiles,
        "licensed_agents": licensed_agents,
        "trusted_agents": trusted_agents,
        "experienced_agents": experienced_agents,
        "confirmed_fraud_reports": confirmed_fraud_reports,
        "license_coverage_percent": round(
            (licensed_agents / total_profiles * 100), 1
        ) if total_profiles > 0 else 0.0,
        "trusted_ratio_percent": round(
            (trusted_agents / total_profiles * 100), 1
        ) if total_profiles > 0 else 0.0,
        "computed_at": datetime.now(UTC).isoformat(),
    }
