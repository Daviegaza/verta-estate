"""
Review API routes — user reviews for agents, landlords, and properties.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.review_service import (
    create_review,
    get_review_stats_for_property,
    get_reviews_by_user,
    get_reviews_for_subject,
    get_top_rated_agents,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("")
async def write_review(
    subject_id: int = Query(..., description="User ID being reviewed (agent, landlord, etc.)"),
    rating: int = Query(..., ge=1, le=5),
    title: str = Query(None, max_length=255),
    body: str = Query(None, max_length=2000),
    property_id: int = Query(None, description="Associated property if applicable"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Write a review for an agent, landlord, or other user."""
    try:
        review = await create_review(
            db=db,
            reviewer_id=current_user.id,
            subject_id=subject_id,
            rating=rating,
            title=title,
            body=body,
            property_id=property_id,
        )
        return {
            "id": review.id,
            "rating": review.rating,
            "message": "Review submitted successfully.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/subject/{subject_id}")
async def subject_reviews(
    subject_id: int,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get reviews and aggregate rating for a subject (agent, landlord)."""
    return await get_reviews_for_subject(db, subject_id, limit)


@router.get("/my")
async def my_reviews(
    limit: int = Query(20, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reviews written by the current user."""
    return {"items": await get_reviews_by_user(db, current_user.id, limit)}


@router.get("/property/{property_id}")
async def property_review_stats(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get review stats for a specific property."""
    return await get_review_stats_for_property(db, property_id)


@router.get("/top-agents")
async def top_rated_agents(
    limit: int = Query(10, le=50),
    min_reviews: int = Query(3, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Get top-rated agents based on review scores."""
    return {"agents": await get_top_rated_agents(db, limit, min_reviews)}
