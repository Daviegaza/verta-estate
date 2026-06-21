import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.property import ListingType, PropertyStatus, PropertyType
from app.models.user import UserRole
from app.schemas.property import (
    PropertyCreate,
    PropertySearch,
    PropertyUpdate,
)
from app.services.analytics_service import (
    fire_and_forget_track_search,
    fire_and_forget_track_user_event,
)
from app.services.property_service import (
    FREE_LISTINGS_PER_MONTH_UNSUBSCRIBED,
    LISTING_FEE_KES,
    count_user_listings_this_month,
    create_property,
    delete_property,
    get_owner_properties,
    get_property_by_id,
    increment_property_views,
    search_properties,
    update_property,
)
from app.services.subscription_service import get_user_subscription

logger = logging.getLogger("vestra.properties")

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

        # ── Fire-and-forget: track property_created event ──────────────────
        asyncio.create_task(  # noqa: RUF006
            fire_and_forget_track_user_event(
                user_id=current_user.id,
                event_type="property_created",
                event_data={"property_id": prop.id, "title": prop.title, "city": prop.city},
            )
        )

        # ── Fire-and-forget: send verify property prompt ──────────────────
        asyncio.create_task(  # noqa: RUF006
            _bg_send_verify_property_prompt(
                user_id=current_user.id,
                property_id=prop.id,
                property_title=prop.title,
            )
        )

        return _prop_to_dict(prop)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)) from e


@router.get("/")
async def list_properties(
    query: str | None = Query(None),
    city: str | None = Query(None),
    county: str | None = Query(None),
    property_type: PropertyType | None = Query(None),
    listing_type: ListingType | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    bedrooms: int | None = Query(None),
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
    asyncio.create_task(  # noqa: RUF006
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
    asyncio.create_task(  # noqa: RUF006
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

    # ── Vestima AI price estimate (1-hour cache) ──────────────────────────
    try:
        from app.services.vestima_service import get_cached_vestima_for_property_dict
        vestima = await get_cached_vestima_for_property_dict(db, property_id, result)
        if vestima:
            result["vestima_estimate"] = vestima
    except Exception:
        logger.warning('{"event":"vestima_estimate_failed","property_id":%d}', property_id)

    return result


@router.get("/{property_id}/seo")
async def get_property_seo(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Public SEO metadata for a property listing.
    Returns Open Graph, Twitter Card, and structured data for search engines
    and social media sharing (WhatsApp, Twitter, Facebook, etc.).
    """
    prop = await get_property_by_id(db, property_id)
    if not prop or (isinstance(prop, dict) and not prop.get("is_deleted", True)):
        raise HTTPException(status_code=404, detail="Property not found")

    # Handle both dict and ORM
    if isinstance(prop, dict):
        title = prop.get("title", "")
        desc = prop.get("description", "") or ""
        city = prop.get("city", "")
        price = prop.get("price", 0)
        currency = prop.get("currency", "KES")
        prop_type = prop.get("property_type", "residential")
        listing_type = prop.get("listing_type", "sale")
        trust_score = prop.get("trust_score")
        images = prop.get("images", []) or []
        bedrooms = prop.get("bedrooms")
        bathrooms = prop.get("bathrooms")
        size_sqft = prop.get("size_sqft")
    else:
        title = prop.title
        desc = prop.description or ""
        city = prop.city
        price = float(prop.price) if prop.price else 0
        currency = prop.currency or "KES"
        prop_type = prop.property_type.value if prop.property_type else "residential"
        listing_type = prop.listing_type.value if prop.listing_type else "sale"
        trust_score = prop.trust_score
        images = prop.images or []
        bedrooms = prop.bedrooms
        bathrooms = prop.bathrooms
        size_sqft = prop.size_sqft

    # Build display price
    listing_label = "For Sale" if listing_type == "sale" else "For Rent" if listing_type == "rent" else "For Lease"
    price_display = f"KES {int(price):,}"
    if listing_type == "rent":
        price_display += "/month"

    # Trust badge
    trust_badge = None
    if trust_score is not None:
        t = float(trust_score) if not isinstance(trust_score, (int, float)) else trust_score
        if t >= 90:
            trust_badge = "Platinum Verified"
        elif t >= 75:
            trust_badge = "Gold Verified"
        elif t >= 60:
            trust_badge = "Silver Verified"
        elif t >= 40:
            trust_badge = "Bronze Verified"

    # Description meta (max 160 chars)
    meta_desc = f"{listing_label}: {title} in {city}, {currency} {int(price):,}"
    if trust_badge:
        meta_desc += f" | {trust_badge}"
    meta_desc += f" | {prop_type.capitalize()}"
    if bedrooms:
        meta_desc += f" | {bedrooms}br"
    meta_desc = meta_desc[:160]

    # First image
    og_image = images[0] if images else "https://vestra.co.ke/og-default.jpg"

    # Structured data (JSON-LD for Google)
    structured_data = {
        "@context": "https://schema.org",
        "@type": "SingleFamilyResidence" if prop_type == "residential" else "Place",
        "name": title,
        "description": desc[:300],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": city,
            "addressCountry": "KE",
        },
        "offers": {
            "@type": "Offer",
            "price": int(price),
            "priceCurrency": currency,
        },
    }
    if listing_type == "rent":
        structured_data["offers"]["businessFunction"] = "https://purl.org/goodrelations/v1#LeaseOut"
        structured_data["offers"]["unitText"] = "MONTH"
    if bedrooms:
        structured_data["numberOfBedrooms"] = bedrooms
    if bathrooms:
        structured_data["numberOfBathroomsTotal"] = bathrooms

    return {
        "title": meta_desc[:70],
        "description": meta_desc,
        "openGraph": {
            "title": f"{title} — {price_display}",
            "description": meta_desc,
            "image": og_image,
            "url": f"https://vestra.co.ke/properties/{property_id}",
            "type": "product",
        },
        "twitter": {
            "card": "summary_large_image",
            "title": f"{title} — {price_display}",
            "description": meta_desc,
            "image": og_image,
        },
        "structuredData": structured_data,
        "property": {
            "id": property_id,
            "title": title,
            "price": int(price),
            "priceDisplay": price_display,
            "currency": currency,
            "city": city,
            "listingType": listing_type,
            "listingLabel": listing_label,
            "propertyType": prop_type,
            "trustScore": trust_score,
            "trustBadge": trust_badge,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "sizeSqft": size_sqft,
            "thumbnail": og_image,
        },
    }


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

    from app.models.payment import PaymentPurpose
    from app.services.payment_service import initiate_mpesa_payment

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
            "You have unlimited listings."
        ),
    }


# ── Background helpers ─────────────────────────────────────────────────────────


async def _bg_send_verify_property_prompt(
    user_id: int,
    property_id: int,
    property_title: str,
) -> None:
    """Fire-and-forget: send verify-property notification."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import send_verify_property_prompt

    try:
        async with AsyncSessionLocal() as bg_db:
            await send_verify_property_prompt(
                db=bg_db,
                user_id=user_id,
                property_id=property_id,
                property_title=property_title,
            )
    except Exception:
        logger = __import__("logging").getLogger("vestra")
        logger.warning(
            '{"event":"bg_verify_prompt_failed","user_id":%d,"property_id":%d}',
            user_id, property_id,
        )
