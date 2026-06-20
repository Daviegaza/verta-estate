import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.property import (
    PropertyCreate, PropertyUpdate, PropertyResponse,
    PropertyListResponse, PropertySearch
)
from app.services.property_service import (
    create_property, get_property_by_id, update_property,
    delete_property, search_properties, get_owner_properties,
    increment_property_views, count_user_listings_this_month,
    FREE_LISTINGS_PER_MONTH_UNSUBSCRIBED, LISTING_FEE_KES,
)
from app.services.ai_service import generate_ai_property_search
from app.services.subscription_service import get_user_subscription
from app.services.analytics_service import fire_and_forget_track_search, fire_and_forget_track_user_event
from app.models.user import UserRole
from app.models.property import PropertyType, ListingType, PropertyStatus

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_property(
    data: PropertyCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new property listing. Enforces subscription limits."""
    try:
        prop = await create_property(db, current_user.id, data)
        return _prop_to_dict(prop)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))


@router.get("/")
async def list_properties(
    query: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    property_type: Optional[PropertyType] = Query(None),
    listing_type: Optional[ListingType] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    bedrooms: Optional[int] = Query(None),
    verified_only: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    search = PropertySearch(
        query=query, city=city, county=county,
        property_type=property_type, listing_type=listing_type,
        min_price=min_price, max_price=max_price,
        bedrooms=bedrooms, verified_only=verified_only,
        page=page, size=size,
    )
    result = await search_properties(db, search)
    # ── Fire-and-forget: track search analytics ──────────────────────────
    asyncio.create_task(
        fire_and_forget_track_search(
            user_id=None,  # public searches are not authenticated
            query=search.query or "",
            filters_applied={"city": search.city, "county": search.county,
                             "property_type": search.property_type,
                             "listing_type": search.listing_type,
                             "min_price": search.min_price,
                             "max_price": search.max_price,
                             "bedrooms": search.bedrooms,
                             "verified_only": search.verified_only},
            results_count=result["total"],
            session_id="public",
        )
    )
    # Items may already be dicts (from cache) or ORM objects (fresh)
    items_data = result["items"]
    if items_data and isinstance(items_data[0], dict):
        serialized_items = items_data  # Already cached as dicts
    else:
        serialized_items = [_prop_to_dict(item) for item in items_data]
    return {
        "items": serialized_items,
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "size": result["size"],
    }


@router.get("/ai-search", response_model=dict)
async def ai_property_search(
    q: str = Query(..., description="Natural language search query"),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered property search — works for everyone (auth optional for personalized results)."""
    from app.services.smart_ai_service import smart_search
    result = await smart_search(db, q, current_user_id=None)
    return result


@router.get("/my")
async def my_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_owner_properties(db, current_user.id, skip=skip, limit=limit)
    return {
        "items": [_prop_to_dict(p) for p in result["items"]],
        "total": result["total"],
    }


def _prop_to_dict(prop) -> dict:
    """Convert ORM object to dict safely while session is active."""
    return {
        "id": prop.id, "owner_id": prop.owner_id, "title": prop.title,
        "description": prop.description, "property_type": prop.property_type,
        "listing_type": prop.listing_type, "status": prop.status,
        "address": prop.address, "city": prop.city, "county": prop.county,
        "country": prop.country, "latitude": prop.latitude, "longitude": prop.longitude,
        "price": prop.price, "currency": prop.currency, "price_negotiable": prop.price_negotiable,
        "bedrooms": prop.bedrooms, "bathrooms": prop.bathrooms, "size_sqft": prop.size_sqft,
        "year_built": prop.year_built, "amenities": prop.amenities or [],
        "images": prop.images or [], "trust_score": prop.trust_score,
        "is_verified": prop.is_verified, "verification_badge": prop.verification_badge,
        "is_featured": prop.is_featured if hasattr(prop, 'is_featured') else False,
        "featured_expires_at": prop.featured_expires_at.isoformat() if hasattr(prop, 'featured_expires_at') and prop.featured_expires_at else None,
        "views": prop.views, "inquiries": prop.inquiries,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
    }


@router.get("/{property_id}")
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # ── Fire-and-forget: track property view event ────────────────────────
    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=None,
            event_type="view",
            event_data={"property_id": property_id, "title": prop.get("title") if isinstance(prop, dict) else getattr(prop, "title", "")},
        )
    )
    # Handle both dict (cached) and ORM object (fresh)
    if isinstance(prop, dict):
        result = prop
    else:
        result = _prop_to_dict(prop)
        # Only increment views on fresh DB reads (not cached)
        await increment_property_views(db, property_id)
    return result


@router.put("/{property_id}")
async def update_property_endpoint(
    property_id: int,
    data: PropertyUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await update_property(db, prop, data)
    return _prop_to_dict(updated)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_endpoint(
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    await delete_property(db, prop)


@router.post("/{property_id}/publish")
async def publish_property(
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update = PropertyUpdate(status=PropertyStatus.active)
    updated = await update_property(db, prop, update)
    return _prop_to_dict(updated)


# ── Featured Listings ────────────────────────────────────────────────────────

@router.post("/{property_id}/feature")
async def feature_property(
    property_id: int,
    phone_number: str = Query(..., description="M-Pesa phone number 2547XXXXXXXX"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Purchase 30-day featured placement for a property.
    Featured listings appear at the top of search results.
    Cost: KES 1,000 for 30 days.
    """
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if prop.status != PropertyStatus.active:
        raise HTTPException(status_code=400, detail="Only active listings can be featured")

    from app.services.payment_service import initiate_mpesa_payment
    from app.models.payment import PaymentPurpose

    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=phone_number,
        amount=1000.0,  # KES 1,000 for featured listing
        purpose=PaymentPurpose.listing_fee,
        reference_id=property_id,
        description="Featured Listing",
    )

    return {
        "message": "M-Pesa STK Push sent for featured listing (KES 1,000 / 30 days).",
        "payment_id": payment.id,
        "checkout_request_id": payment.mpesa_checkout_request_id,
        "property_id": property_id,
        "amount": 1000,
        "duration_days": 30,
        "status": "payment_pending",
    }


@router.get("/listing-fee/info")
async def listing_fee_info(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get listing fee and usage info for the current user."""
    from datetime import datetime, timezone
    sub = await get_user_subscription(db, current_user.id)
    tier = sub.get("tier", "free") if sub else "free"
    count_this_month = await count_user_listings_this_month(db, current_user.id)

    # Get limit from subscription
    from app.services.subscription_service import get_listing_limit
    limit = await get_listing_limit(db, current_user.id, current_user.role.value)

    return {
        "listings_this_month": count_this_month,
        "listing_limit": limit,
        "free_listings_remaining": max(0, limit - count_this_month),
        "listing_fee_kes": LISTING_FEE_KES,
        "free_listings_for_unsubscribed": FREE_LISTINGS_PER_MONTH_UNSUBSCRIBED,
        "current_tier": tier,
        "message": (
            f"You have used {count_this_month}/{limit} listings this month."
            if limit < 999999 else
            f"You have unlimited listings."
        ),
    }
