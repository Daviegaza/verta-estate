"""
Analytics Service — data collection pipeline for ML models and business intelligence.
Tracks every user action, search query, property view, verification outcome,
price change, and payment behavior.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, case, and_

from app.models.analytics import UserEvent, PriceChange, VerificationOutcome, SearchAnalytics
from app.models.user import User

logger = logging.getLogger("vestra")

# ── Event Type Constants ───────────────────────────────────────────────────────

# User lifecycle
EVENT_REGISTRATION = "registration"
EVENT_EMAIL_VERIFIED = "email_verified"
EVENT_KYC_SUBMITTED = "kyc_submitted"
EVENT_KYC_APPROVED = "kyc_approved"

# Property engagement
EVENT_PROPERTY_VIEWED = "property_viewed"
EVENT_PROPERTY_FAVORITED = "property_favorited"
EVENT_PROPERTY_INQUIRED = "property_inquired"

# Search
EVENT_SEARCH_PERFORMED = "search_performed"
EVENT_SEARCH_RESULT_CLICKED = "search_result_clicked"

# Payments
EVENT_PAYMENT_INITIATED = "payment_initiated"
EVENT_PAYMENT_COMPLETED = "payment_completed"
EVENT_PAYMENT_FAILED = "payment_failed"

# Subscriptions
EVENT_SUBSCRIPTION_STARTED = "subscription_started"
EVENT_SUBSCRIPTION_UPGRADED = "subscription_upgraded"
EVENT_SUBSCRIPTION_CANCELLED = "subscription_cancelled"

# Verification
EVENT_VERIFICATION_REQUESTED = "verification_requested"
EVENT_VERIFICATION_COMPLETED = "verification_completed"

# Referral
EVENT_REFERRAL_SHARED = "referral_shared"
EVENT_REFERRAL_SIGNUP = "referral_signup"
EVENT_REFERRAL_CONVERTED = "referral_converted"

# ── User Events ──────────────────────────────────────────────────────────────────

async def track_event(
    db: AsyncSession,
    user_id: Optional[int],
    session_id: str,
    event_type: str,
    event_data: dict | None = None,
    client_timestamp: datetime | None = None,
) -> UserEvent:
    """Track a user behavior event for analytics and ML training."""
    event = UserEvent(
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        event_data=event_data or {},
        client_timestamp=client_timestamp or datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()
    return event


async def get_user_events(
    db: AsyncSession, user_id: int, event_type: str | None = None, limit: int = 100,
) -> list[UserEvent]:
    """Get recent events for a user."""
    query = select(UserEvent).where(UserEvent.user_id == user_id)
    if event_type:
        query = query.where(UserEvent.event_type == event_type)
    result = await db.execute(query.order_by(UserEvent.created_at.desc()).limit(limit))
    return result.scalars().all()


# ── Price Changes ───────────────────────────────────────────────────────────────

async def track_price_change(
    db: AsyncSession,
    property_id: int,
    old_price: float,
    new_price: float,
    changed_by_id: int,
    reason: str | None = None,
) -> PriceChange:
    """Track a price change for ML price prediction models."""
    change = PriceChange(
        property_id=property_id,
        old_price=old_price,
        new_price=new_price,
        changed_by_id=changed_by_id,
        reason=reason,
    )
    db.add(change)
    await db.commit()
    return change


async def get_price_history(db: AsyncSession, property_id: int) -> list[PriceChange]:
    """Get price change history for a property."""
    result = await db.execute(
        select(PriceChange)
        .where(PriceChange.property_id == property_id)
        .order_by(PriceChange.created_at.desc())
    )
    return result.scalars().all()


# ── Verification Outcomes ───────────────────────────────────────────────────────

async def track_verification_outcome(
    db: AsyncSession,
    verification_id: int,
    ai_prediction: dict,
    human_decision: str,
    was_correct: bool | None = None,
    ground_truth_notes: str | None = None,
) -> VerificationOutcome:
    """Track AI vs human decisions for model evaluation."""
    outcome = VerificationOutcome(
        verification_id=verification_id,
        ai_prediction=ai_prediction,
        human_decision=human_decision,
        was_correct=was_correct,
        ground_truth_notes=ground_truth_notes,
    )
    db.add(outcome)
    await db.commit()
    return outcome


async def get_ai_accuracy_stats(db: AsyncSession) -> dict:
    """Get AI prediction accuracy statistics."""
    total = await db.execute(select(func.count(VerificationOutcome.id)))
    correct = await db.execute(
        select(func.count(VerificationOutcome.id)).where(VerificationOutcome.was_correct == True)
    )
    return {
        "total_predictions": total.scalar_one(),
        "correct_predictions": correct.scalar_one(),
        "accuracy_pct": round(
            (correct.scalar_one() / max(total.scalar_one(), 1)) * 100, 1
        ),
    }


# ── Search Analytics ────────────────────────────────────────────────────────────

async def track_search(
    db: AsyncSession,
    user_id: Optional[int],
    query: str,
    session_id: str,
    filters_applied: dict | None = None,
    results_count: int = 0,
    clicked_property_id: int | None = None,
) -> SearchAnalytics:
    """Track a search query for search relevance improvement."""
    search = SearchAnalytics(
        user_id=user_id,
        query=query,
        session_id=session_id,
        filters_applied=filters_applied or {},
        results_count=results_count,
        clicked_property_id=clicked_property_id,
    )
    db.add(search)
    await db.commit()
    return search


async def get_top_searches(db: AsyncSession, limit: int = 20) -> list:
    """Get most popular search queries."""
    result = await db.execute(
        select(SearchAnalytics.query, func.count(SearchAnalytics.id).label('count'))
        .group_by(SearchAnalytics.query)
        .order_by(func.count(SearchAnalytics.id).desc())
        .limit(limit)
    )
    return [{"query": row.query, "count": row.count} for row in result.all()]


# ── Conversion Funnel ──────────────────────────────────────────────────────────


async def get_conversion_funnel(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[dict]:
    """
    Get conversion funnel: visitor -> registered -> verified -> made_payment -> subscribed.

    Returns a list of funnel stages with counts, each stage filtering down from the previous.
    """
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=90)

    # Stage 1: All users (registered)
    total_users = await db.execute(
        select(func.count(User.id)).where(
            User.created_at >= start_date,
            User.created_at <= end_date,
        )
    )
    registered = total_users.scalar_one()

    # Stage 2: Verified email
    verified = await db.execute(
        select(func.count(User.id)).where(
            User.is_verified == True,
            User.created_at >= start_date,
            User.created_at <= end_date,
        )
    )
    verified_count = verified.scalar_one()

    # Stage 3: Made at least one payment
    from app.models.payment import Payment, PaymentStatus
    paid_users = await db.execute(
        select(func.count(func.distinct(Payment.user_id))).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
        )
    )
    paid_count = paid_users.scalar_one()

    # Stage 4: Has active subscription
    from app.models.subscription import Subscription, SubscriptionStatus
    subscribed_users = await db.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trialing]),
            Subscription.created_at >= start_date,
            Subscription.created_at <= end_date,
        )
    )
    subscribed_count = subscribed_users.scalar_one()

    # Stage 5: KYC approved
    from app.models.kyc_notification import KYCVerification, KYCStatus
    kyc_approved = await db.execute(
        select(func.count(func.distinct(KYCVerification.user_id))).where(
            KYCVerification.status == KYCStatus.approved,
            KYCVerification.created_at >= start_date,
            KYCVerification.created_at <= end_date,
        )
    )
    kyc_count = kyc_approved.scalar_one()

    stages = [
        {"stage": "Registered", "count": registered, "conversion_pct": 100.0},
        {"stage": "Email Verified", "count": verified_count, "conversion_pct": _pct(verified_count, registered)},
        {"stage": "KYC Approved", "count": kyc_count, "conversion_pct": _pct(kyc_count, registered)},
        {"stage": "Made Payment", "count": paid_count, "conversion_pct": _pct(paid_count, registered)},
        {"stage": "Subscribed", "count": subscribed_count, "conversion_pct": _pct(subscribed_count, registered)},
    ]

    return stages


# ── Cohort Retention ──────────────────────────────────────────────────────────


async def get_cohort_retention(db: AsyncSession, weeks: int = 8) -> list[dict]:
    """
    Weekly user retention cohorts.

    Groups users by the week they registered, then shows what percentage
    were active (made a payment, created a listing, or logged an event)
    in each subsequent week.

    Returns a list of cohort rows, each with:
      - cohort_week: ISO week string (e.g., "2026-W20")
      - total_users: number of users who registered that week
      - periods: list of dicts with week_offset, active_users, retention_pct
    """
    from app.models.payment import Payment, PaymentStatus

    now = datetime.now(timezone.utc)

    # Get all users with their registration weeks
    all_users = await db.execute(
        select(
            User.id,
            func.date_trunc('week', User.created_at).label('cohort_week'),
        ).order_by(User.created_at.desc())
    )
    user_rows = all_users.all()

    if not user_rows:
        return []

    # Build cohort buckets: cohort_week -> set of user_ids
    cohorts = {}
    for row in user_rows:
        week_key = row.cohort_week.strftime('%Y-W%V')
        if week_key not in cohorts:
            cohorts[week_key] = {"users": set(), "total": 0}
        cohorts[week_key]["users"].add(row.id)
        cohorts[week_key]["total"] += 1

    # Get all payment activity (as proxy for "active")
    payments = await db.execute(
        select(Payment.user_id, Payment.created_at).where(
            Payment.status == PaymentStatus.completed,
        )
    )
    payment_rows = payments.all()

    # Build user activity map: user_id -> set of week offsets from their cohort
    from collections import defaultdict
    user_activity = defaultdict(set)

    for user_id, cohort_week_key in ((r.id, r.cohort_week.strftime('%Y-W%V')) for r in user_rows):
        for _, created_at in payment_rows:
            if _ == user_id:
                payment_week = created_at.strftime('%Y-W%V')
                # Calculate week offset
                try:
                    from datetime import date
                    cohort_start = _parse_iso_week(cohort_week_key)
                    payment_start = _parse_iso_week(payment_week)
                    if payment_start >= cohort_start:
                        offset = int((payment_start - cohort_start).days / 7)
                        if offset <= weeks:
                            user_activity[(user_id, cohort_week_key)].add(offset)
                except (ValueError, IndexError):
                    pass

    # Build response
    result = []
    sorted_cohorts = sorted(cohorts.keys(), reverse=True)[:weeks * 2]  # Show recent cohorts

    for cohort_key in sorted_cohorts:
        cohort = cohorts[cohort_key]
        total = cohort["total"]
        if total == 0:
            continue

        periods = []
        for offset in range(weeks + 1):
            active = 0
            for uid in cohort["users"]:
                if offset in user_activity.get((uid, cohort_key), set()):
                    active += 1

            periods.append({
                "week_offset": offset,
                "active_users": active,
                "retention_pct": round((active / max(total, 1)) * 100, 1),
            })

        result.append({
            "cohort_week": cohort_key,
            "total_users": total,
            "periods": periods,
        })

    return result


# ── Event type aggregation ─────────────────────────────────────────────────────


async def get_event_counts_by_type(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
) -> list[dict]:
    """Get count of events grouped by event_type."""
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)

    result = await db.execute(
        select(
            UserEvent.event_type,
            func.count(UserEvent.id).label('count'),
        )
        .where(
            UserEvent.created_at >= start_date,
            UserEvent.created_at <= end_date,
        )
        .group_by(UserEvent.event_type)
        .order_by(func.count(UserEvent.id).desc())
        .limit(limit)
    )
    return [
        {"event_type": row.event_type, "count": row.count}
        for row in result.all()
    ]


async def get_daily_active_users(
    db: AsyncSession,
    days: int = 30,
) -> list[dict]:
    """Get daily active users (users with any event in a given day)."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc('day', UserEvent.created_at).label('day'),
            func.count(func.distinct(UserEvent.user_id)).label('dau'),
        )
        .where(
            UserEvent.created_at >= start,
            UserEvent.user_id.isnot(None),
        )
        .group_by(text('day'))
        .order_by(text('day'))
    )
    return [
        {"date": row.day.strftime('%Y-%m-%d'), "dau": row.dau}
        for row in result.all()
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _pct(part: int, total: int) -> float:
    """Calculate percentage, avoiding division by zero."""
    return round((part / max(total, 1)) * 100, 1)


def _parse_iso_week(iso_key: str) -> date:
    """Parse 'YYYY-WNN' ISO week string to a date (Monday of that week)."""
    from datetime import date
    year, week = iso_key.split('-W')
    # Python's isoweek calculation
    first_of_jan = date(int(year), 1, 1)
    # Find the first Monday of the year
    days_to_first_monday = (7 - first_of_jan.weekday()) % 7
    first_monday = first_of_jan + timedelta(days=days_to_first_monday)
    return first_monday + timedelta(weeks=int(week) - 1)


async def get_search_conversion_rate(db: AsyncSession) -> dict:
    """Get search-to-click conversion rate."""
    total = await db.execute(select(func.count(SearchAnalytics.id)))
    with_clicks = await db.execute(
        select(func.count(SearchAnalytics.id)).where(SearchAnalytics.clicked_property_id.isnot(None))
    )
    total_count = total.scalar_one()
    click_count = with_clicks.scalar_one()
    return {
        "total_searches": total_count,
        "searches_with_clicks": click_count,
        "ctr_pct": round((click_count / max(total_count, 1)) * 100, 1),
    }


# ── Fire-and-Forget Wrappers ─────────────────────────────────────────────────────
# These create their own DB sessions so callers can fire them via
# asyncio.create_task() without blocking the request path.


async def fire_and_forget_track_search(
    user_id: Optional[int],
    query: str,
    filters_applied: Optional[dict] = None,
    results_count: int = 0,
    clicked_property_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> None:
    """Fire-and-forget: record a search with its own DB session."""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await track_search(
                db,
                user_id=user_id,
                query=query,
                session_id=session_id or "unknown",
                filters_applied=filters_applied or {},
                results_count=results_count,
                clicked_property_id=clicked_property_id,
            )
    except Exception:
        logger.warning(
            '{"event":"ff_track_search_failed","query":"%s"}',
            query[:100] if query else "",
            exc_info=True,
        )


async def fire_and_forget_track_user_event(
    user_id: Optional[int],
    event_type: str,
    event_data: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """Fire-and-forget: record a user event with its own DB session."""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await track_event(
                db,
                user_id=user_id,
                session_id=session_id or "unknown",
                event_type=event_type,
                event_data=event_data or {},
                client_timestamp=datetime.now(timezone.utc),
            )
    except Exception:
        logger.warning(
            '{"event":"ff_track_user_event_failed","event_type":"%s"}',
            event_type,
            exc_info=True,
        )


async def fire_and_forget_track_price_change(
    property_id: int,
    old_price: float,
    new_price: float,
    changed_by_id: int,
    reason: Optional[str] = None,
) -> None:
    """Fire-and-forget: record a price change with its own DB session."""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await track_price_change(
                db,
                property_id=property_id,
                old_price=old_price,
                new_price=new_price,
                changed_by_id=changed_by_id,
                reason=reason,
            )
    except Exception:
        logger.warning(
            '{"event":"ff_track_price_change_failed","property_id":%d}',
            property_id,
            exc_info=True,
        )


async def fire_and_forget_track_verification_outcome(
    verification_id: int,
    ai_prediction: dict,
    human_decision: str,
    was_correct: Optional[bool] = None,
    ground_truth_notes: Optional[str] = None,
) -> None:
    """Fire-and-forget: record a verification outcome with its own DB session."""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await track_verification_outcome(
                db,
                verification_id=verification_id,
                ai_prediction=ai_prediction,
                human_decision=human_decision,
                was_correct=was_correct,
                ground_truth_notes=ground_truth_notes,
            )
    except Exception:
        logger.warning(
            '{"event":"ff_track_verification_outcome_failed","verification_id":%d}',
            verification_id,
            exc_info=True,
        )
