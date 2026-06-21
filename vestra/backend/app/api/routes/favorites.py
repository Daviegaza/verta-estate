"""Favorites & Saved Searches API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.kyc_notification import SavedProperty, SavedSearch

router = APIRouter(prefix="/favorites", tags=["Favorites"])


# ── Saved Properties ──────────────────────────────────────────────────────────

@router.get("/")
async def list_favorites(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved/favorite properties."""
    result = await db.execute(
        select(SavedProperty)
        .where(SavedProperty.user_id == current_user.id)
        .order_by(SavedProperty.created_at.desc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": s.id,
                "property_id": s.property_id,
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in items
        ],
    }


@router.get("/my")
async def list_favorites_enriched(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved properties with full property details (for buyer dashboard)."""
    from sqlalchemy.orm import joinedload

    from app.models.property import Property

    result = await db.execute(
        select(SavedProperty)
        .where(SavedProperty.user_id == current_user.id)
        .order_by(SavedProperty.created_at.desc())
    )
    saved = result.scalars().all()
    property_ids = [s.property_id for s in saved]

    if not property_ids:
        return []

    # Fetch full property details
    result = await db.execute(
        select(Property)
        .options(joinedload(Property.owner))
        .where(Property.id.in_(property_ids))
    )
    props = {p.id: p for p in result.unique().scalars().all()}

    enriched = []
    for s in saved:
        prop = props.get(s.property_id)
        if prop:
            enriched.append({
                "id": prop.id,
                "owner_id": prop.owner_id,
                "owner_name": prop.owner.full_name if prop.owner else None,
                "title": prop.title,
                "description": prop.description,
                "property_type": prop.property_type.value if prop.property_type else None,
                "listing_type": prop.listing_type.value if prop.listing_type else None,
                "status": prop.status.value if prop.status else None,
                "address": prop.address,
                "city": prop.city,
                "county": prop.county,
                "price": float(prop.price) if prop.price else 0,
                "currency": prop.currency or "KES",
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "size_sqft": float(prop.size_sqft) if prop.size_sqft else None,
                "trust_score": float(prop.trust_score) if prop.trust_score else None,
                "is_verified": prop.is_verified,
                "verification_badge": prop.verification_badge,
                "views": prop.views or 0,
                "inquiries": prop.inquiries or 0,
                "images": prop.images or [],
                "amenities": prop.amenities or [],
                "created_at": prop.created_at.isoformat() if prop.created_at else None,
            })

    return enriched


@router.post("/{property_id}")
async def add_favorite(
    property_id: int,
    notes: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a property to favorites."""
    # Check if already saved
    result = await db.execute(
        select(SavedProperty).where(
            SavedProperty.user_id == current_user.id,
            SavedProperty.property_id == property_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"message": "Already in favorites", "id": existing.id}

    saved = SavedProperty(
        user_id=current_user.id,
        property_id=property_id,
        notes=notes,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return {"message": "Added to favorites", "id": saved.id}


@router.delete("/{property_id}")
async def remove_favorite(
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a property from favorites."""
    result = await db.execute(
        delete(SavedProperty).where(
            SavedProperty.user_id == current_user.id,
            SavedProperty.property_id == property_id,
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not in favorites")
    return {"message": "Removed from favorites"}


# ── Saved Searches ────────────────────────────────────────────────────────────

@router.get("/searches")
async def list_saved_searches(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved searches."""
    result = await db.execute(
        select(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "filters": s.filters,
                "notify_email": s.notify_email,
                "notify_whatsapp": s.notify_whatsapp,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in items
        ],
    }


@router.post("/searches")
async def save_search(
    filters: dict,
    name: str | None = None,
    notify_email: bool = True,
    notify_whatsapp: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a search query for alerts."""
    search = SavedSearch(
        user_id=current_user.id,
        name=name,
        filters=filters,
        notify_email=notify_email,
        notify_whatsapp=notify_whatsapp,
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)
    return {"message": "Search saved", "id": search.id}


@router.delete("/searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved search."""
    result = await db.execute(
        delete(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Deleted"}
