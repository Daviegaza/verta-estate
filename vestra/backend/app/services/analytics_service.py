"""
Analytics Service — data collection pipeline for ML models and business intelligence.
Tracks every user action, search query, property view, verification outcome,
price change, and payment behavior.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.analytics import UserEvent, PriceChange, VerificationOutcome, SearchAnalytics

logger = logging.getLogger("vestra")

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
