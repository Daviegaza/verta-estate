from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, case
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.models.property import Property, PropertyStatus
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearch
from app.core.redis import cache_get, cache_set, cache_delete
import logging

logger = logging.getLogger("vestra")

# Cache TTLs (seconds)
CACHE_TTL_PROPERTY = 300      # 5 min — property detail
CACHE_TTL_LIST = 120           # 2 min — property listings
CACHE_TTL_STATS = 300          # 5 min — admin stats

# Listing fee (KES)
LISTING_FEE_KES = 300
FREE_LISTINGS_PER_MONTH_UNSUBSCRIBED = 3


async def count_user_listings_this_month(db: AsyncSession, user_id: int) -> int:
    """Count how many listings a user has created this calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Property.id)).where(
            Property.owner_id == user_id,
            Property.created_at >= month_start,
        )
    )
    return result.scalar_one()


async def create_property(db: AsyncSession, owner_id: int, data: PropertyCreate) -> Property:
    """
    Create a new property listing.
    Enforces subscription limits before creation.
    """
    # Subscription listing limit check
    from app.services.subscription_service import get_listing_limit, get_user_subscription

    sub = await get_user_subscription(db, owner_id)
    role = "seller"  # default
    if sub:
        # If user has a subscription, get their role from user table
        from app.models.user import User
        user_result = await db.execute(select(User).where(User.id == owner_id))
        user = user_result.scalar_one_or_none()
        if user:
            role = user.role.value

    limit = await get_listing_limit(db, owner_id, role)
    current_count = await count_user_listings_this_month(db, owner_id)

    if current_count >= limit:
        raise ValueError(
            f"Listing limit reached ({limit} per month for your plan). "
            f"Upgrade your subscription to list more properties."
        )

    prop = Property(owner_id=owner_id, **data.model_dump())
    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    # ── Referral reward: first property listing ────────────────────────────
    if current_count == 0:
        from app.services.referral_engine import award_referral_reward
        reward_result = await award_referral_reward(db, owner_id, "first_listing")
        if reward_result:
            logger.info(
                '{"event":"referral_reward_for_listing","referrer":%d,'
                '"user_id":%d,"amount_kes":%d}',
                reward_result["referrer_id"], owner_id,
                reward_result["reward_kes"],
            )
    # Invalidate listing caches (new property changes all listing pages)
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:search:*")
    logger.info('{"event":"property_created","property_id":%d,"owner_id":%d,"count_this_month":%d}',
                prop.id, owner_id, current_count + 1)
    return prop


async def get_property_by_id(db: AsyncSession, property_id: int):
    """
    Get property by ID. Returns a dict (from cache) or ORM object (from DB).
    The routes handle both — they call _prop_to_dict for ORM objects.
    """
    # Try cache first — returns serialized dict
    cache_key = f"vestra:prop:{property_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        # cached is already a dict matching _prop_to_dict output
        return cached

    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if prop:
        # Store already-serialized dict in cache
        from app.api.routes.properties import _prop_to_dict
        prop_dict = _prop_to_dict(prop)
        await cache_set(cache_key, prop_dict, ttl=CACHE_TTL_PROPERTY)
    return prop


def _prop_to_cache_dict(prop: Property) -> dict:
    """Extract serializable fields for caching (avoids ORM session issues)."""
    return {
        "id": prop.id, "owner_id": prop.owner_id, "title": prop.title,
        "description": prop.description, "property_type": prop.property_type,
        "listing_type": prop.listing_type, "status": prop.status,
        "address": prop.address, "city": prop.city, "county": prop.county,
        "country": prop.country, "latitude": prop.latitude, "longitude": prop.longitude,
        "price": prop.price, "currency": prop.currency,
        "price_negotiable": prop.price_negotiable,
        "bedrooms": prop.bedrooms, "bathrooms": prop.bathrooms,
        "size_sqft": prop.size_sqft, "year_built": prop.year_built,
        "amenities": prop.amenities or [], "images": prop.images or [],
        "trust_score": prop.trust_score, "is_verified": prop.is_verified,
        "verification_badge": prop.verification_badge,
        "views": prop.views, "inquiries": prop.inquiries,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
    }


async def update_property(
    db: AsyncSession, prop: Property, data: PropertyUpdate
) -> Property:
    # Track old price before updating (for analytics)
    old_price = prop.price

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    await db.commit()
    await db.refresh(prop)

    # ── Fire-and-forget: track price change if price was updated ─────────
    from app.services.analytics_service import fire_and_forget_track_price_change
    import asyncio

    if data.model_dump(exclude_unset=True).get("price") is not None and old_price != prop.price:
        asyncio.create_task(
            fire_and_forget_track_price_change(
                property_id=prop.id,
                old_price=float(old_price) if old_price else 0,
                new_price=float(prop.price) if prop.price else 0,
                changed_by_id=prop.owner_id,
            )
        )

    # Invalidate cache for this property and listings
    await cache_delete(f"vestra:prop:{prop.id}")
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:search:*")
    return prop


async def delete_property(db: AsyncSession, prop: Property) -> None:
    prop_id = prop.id
    await db.delete(prop)
    await db.commit()
    # Invalidate caches
    await cache_delete(f"vestra:prop:{prop_id}")
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:search:*")


async def search_properties(
    db: AsyncSession, search: PropertySearch
) -> dict:
    """
    Search properties with filters.
    Uses PostgreSQL full-text search when a text query is provided
    for relevance-ranked results. Falls back to filtered listing otherwise.
    """
    # Use full-text search when a text query is present
    if search.query and search.query.strip():
        from app.services.search_service import cached_full_text_search
        return await cached_full_text_search(
            db,
            query=search.query,
            city=search.city,
            property_type=search.property_type,
            listing_type=search.listing_type,
            min_price=search.min_price,
            max_price=search.max_price,
            bedrooms=search.bedrooms,
            verified_only=search.verified_only,
            page=search.page,
            size=search.size,
        )

    # Standard filtered listing (no text query) — check Redis cache
    list_cache_key = f"vestra:list:{_hash_search(search)}"
    list_cached = await cache_get(list_cache_key)
    if list_cached:
        return list_cached

    query = select(Property).where(Property.status == PropertyStatus.active)
    if search.city:
        query = query.where(Property.city.ilike(f"%{search.city}%"))
    if search.county:
        query = query.where(Property.county.ilike(f"%{search.county}%"))
    if search.property_type:
        query = query.where(Property.property_type == search.property_type)
    if search.listing_type:
        query = query.where(Property.listing_type == search.listing_type)
    if search.min_price is not None:
        query = query.where(Property.price >= search.min_price)
    if search.max_price is not None:
        query = query.where(Property.price <= search.max_price)
    if search.bedrooms is not None:
        query = query.where(Property.bedrooms >= search.bedrooms)
    if search.bathrooms is not None:
        query = query.where(Property.bathrooms >= search.bathrooms)
    if search.verified_only:
        query = query.where(Property.is_verified == True)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (search.page - 1) * search.size
    # Sort featured listings first, then by creation date
    query = query.order_by(
        Property.is_featured.desc(),
        Property.created_at.desc()
    ).offset(offset).limit(search.size)

    result = await db.execute(query)
    items = result.scalars().all()

    response = {
        "items": items,
        "total": total,
        "page": search.page,
        "pages": max(1, -(-total // search.size)),
        "size": search.size,
    }

    # Cache serialized version (dicts, not ORM objects — JSON-serializable)
    cache_response = {
        "items": [_prop_to_cache_dict(item) for item in items],
        "total": total,
        "page": search.page,
        "pages": max(1, -(-total // search.size)),
        "size": search.size,
    }
    await cache_set(list_cache_key, cache_response, ttl=CACHE_TTL_LIST)
    return response


def _hash_search(search: PropertySearch) -> str:
    """Hash search params for cache key (no session objects)."""
    import hashlib, json
    raw = json.dumps({
        "q": search.query or "", "city": search.city or "",
        "county": search.county or "", "pt": str(search.property_type or ""),
        "lt": str(search.listing_type or ""), "min_p": search.min_price or 0,
        "max_p": search.max_price or 0, "beds": search.bedrooms or 0,
        "baths": search.bathrooms or 0, "verified": search.verified_only,
        "page": search.page, "size": search.size,
    }, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def get_owner_properties(
    db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 50,
) -> dict:
    """Get properties owned by a user with pagination."""
    count_result = await db.execute(
        select(func.count(Property.id))
        .where(Property.owner_id == owner_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Property)
        .where(Property.owner_id == owner_id)
        .order_by(Property.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return {"items": result.scalars().all(), "total": total}


async def count_properties(db: AsyncSession, status: str = None) -> int:
    query = select(func.count(Property.id))
    if status:
        try:
            query = query.where(Property.status == PropertyStatus(status))
        except ValueError:
            pass
    result = await db.execute(query)
    return result.scalar_one()


async def count_active_listings(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Property.id)).where(Property.status == PropertyStatus.active)
    )
    return result.scalar_one()


async def count_verified_properties(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Property.id)).where(Property.is_verified == True)
    )
    return result.scalar_one()


async def increment_property_views(db: AsyncSession, property_id: int) -> None:
    """Increment view counter inline — avoids loading full Property row (with JSON arrays)."""
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Property)
        .where(Property.id == property_id)
        .values(views=Property.views + 1)
    )
    await db.commit()


# ─── Admin Functions ───────────────────────────────────────────────────────────

async def get_all_properties_admin(
    db: AsyncSession, skip: int = 0, limit: int = 50, status: str = None,
):
    from sqlalchemy.orm import joinedload
    query = select(Property).options(joinedload(Property.owner)).order_by(Property.created_at.desc())
    if status:
        try:
            query = query.where(Property.status == PropertyStatus(status))
        except ValueError:
            pass
    result = await db.execute(query.offset(skip).limit(limit))
    return result.unique().scalars().all()


async def update_property_status(
    db: AsyncSession, property_id: int, new_status: PropertyStatus
) -> Property | None:
    prop = await get_property_by_id(db, property_id)
    if not prop:
        return None
    prop.status = new_status
    if new_status == PropertyStatus.active:
        prop.is_verified = True
        prop.verification_badge = "admin_verified"
    await db.commit()
    await db.refresh(prop)
    # Invalidate caches
    await cache_delete(f"vestra:prop:{prop.id}")
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:admin:stats")
    return prop


async def get_monthly_listing_stats(db: AsyncSession) -> list:
    """Monthly new listings for last 6 months."""
    from datetime import datetime
    result = await db.execute(
        select(
            func.date_trunc('month', Property.created_at).label('month'),
            func.count(Property.id).label('count')
        ).where(
            Property.created_at >= func.date_trunc('month', func.now()) - func.make_interval(0, 6)
        ).group_by('month').order_by('month')
    )
    data = {row.month.strftime('%b'): row.count for row in result.all()}
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    now = datetime.utcnow()
    months = []
    for i in range(5, -1, -1):
        label = month_names[(now.month - 1 - i) % 12]
        months.append({"month": label, "listings": data.get(label, 0)})
    return months


async def get_property_type_distribution(db: AsyncSession) -> list:
    result = await db.execute(
        select(Property.property_type, func.count(Property.id)).group_by(Property.property_type)
    )
    colors = {
        "residential": "#10b981", "commercial": "#3b82f6",
        "land": "#f59e0b", "industrial": "#ef4444",
        "agricultural": "#84cc16", "student_housing": "#8b5cf6",
        "short_stay": "#ec4899",
    }
    return [
        {"name": t.value.replace("_", " ").title() if hasattr(t, 'value') else str(t).title(),
         "value": c, "color": colors.get(t.value if hasattr(t, 'value') else str(t), "#6b7280")}
        for t, c in result.all()
    ]


async def get_city_distribution(db: AsyncSession) -> list:
    result = await db.execute(
        select(Property.city, func.count(Property.id)).group_by(Property.city).order_by(func.count(Property.id).desc()).limit(8)
    )
    return [{"name": city, "value": count} for city, count in result.all()]
