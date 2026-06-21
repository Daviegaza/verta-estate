"""
Review Service — user reviews for agents, landlords, and properties.
Builds trust by allowing verified transaction participants to rate each other.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select

from app.models.trust_safety import Review

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")


async def create_review(
    db: AsyncSession,
    reviewer_id: int,
    subject_id: int,
    rating: int,
    title: str | None = None,
    body: str | None = None,
    property_id: int | None = None,
    is_verified_transaction: bool = False,
) -> Review:
    """Create a review. Validates rating 1-5 and prevents self-reviews."""
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5")
    if reviewer_id == subject_id:
        raise ValueError("Cannot review yourself")

    # Check for duplicate review
    existing = await db.execute(
        select(Review).where(
            and_(
                Review.reviewer_id == reviewer_id,
                Review.subject_id == subject_id,
                Review.property_id == property_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("You have already reviewed this subject for this property")

    review = Review(
        reviewer_id=reviewer_id,
        subject_id=subject_id,
        property_id=property_id,
        rating=rating,
        title=title,
        body=body,
        is_verified_transaction=is_verified_transaction,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    logger.info(
        '{"event":"review_created","id":%d,"reviewer":%d,"subject":%d,"rating":%d}',
        review.id, reviewer_id, subject_id, rating,
    )
    return review


async def get_reviews_for_subject(
    db: AsyncSession, subject_id: int, limit: int = 20,
) -> dict:
    """Get all reviews for a subject (agent, landlord, etc.) with aggregate stats."""
    result = await db.execute(
        select(Review)
        .where(Review.subject_id == subject_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    reviews = result.scalars().all()

    # Aggregate stats
    stats_result = await db.execute(
        select(
            func.count(Review.id),
            func.avg(Review.rating),
            func.count(Review.id).filter(Review.rating >= 4),
        ).where(Review.subject_id == subject_id)
    )
    total, avg_rating, positive_count = stats_result.one()

    return {
        "subject_id": subject_id,
        "total_reviews": total or 0,
        "average_rating": round(float(avg_rating or 0), 1),
        "positive_pct": round((positive_count / total * 100) if total else 0, 1),
        "reviews": [_serialize_review(r) for r in reviews],
    }


async def get_reviews_by_user(
    db: AsyncSession, reviewer_id: int, limit: int = 20,
) -> list[dict]:
    """Get all reviews written by a user."""
    result = await db.execute(
        select(Review)
        .where(Review.reviewer_id == reviewer_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    return [_serialize_review(r) for r in result.scalars().all()]


async def get_review_stats_for_property(
    db: AsyncSession, property_id: int,
) -> dict:
    """Get review stats for a specific property."""
    result = await db.execute(
        select(
            func.count(Review.id),
            func.avg(Review.rating),
        ).where(Review.property_id == property_id)
    )
    total, avg_rating = result.one()

    return {
        "property_id": property_id,
        "total_reviews": total or 0,
        "average_rating": round(float(avg_rating or 0), 1),
    }


async def get_top_rated_agents(
    db: AsyncSession, limit: int = 10, min_reviews: int = 3,
) -> list[dict]:
    """Get top-rated agents based on review scores."""
    result = await db.execute(
        select(
            Review.subject_id,
            func.count(Review.id).label("total"),
            func.avg(Review.rating).label("avg_rating"),
        )
        .group_by(Review.subject_id)
        .having(func.count(Review.id) >= min_reviews)
        .order_by(func.avg(Review.rating).desc())
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "subject_id": row.subject_id,
            "total_reviews": row.total,
            "average_rating": round(float(row.avg_rating), 1),
        }
        for row in rows
    ]


# ── Internal Helpers ──────────────────────────────────────────────────────────────

def _serialize_review(r: Review) -> dict:
    return {
        "id": r.id,
        "reviewer_id": r.reviewer_id,
        "subject_id": r.subject_id,
        "property_id": r.property_id,
        "rating": r.rating,
        "title": r.title,
        "body": r.body,
        "is_verified_transaction": r.is_verified_transaction,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
