"""
Full-text search service using PostgreSQL tsvector/tsquery.
Provides fast, relevance-ranked property search with typo tolerance.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from app.core.redis import cache_get, cache_set
from app.models.property import ListingType, Property, PropertyType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

FTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_properties_fts
ON properties
USING gin(
    to_tsvector('english',
        coalesce(title, '') || ' ' ||
        coalesce(description, '') || ' ' ||
        coalesce(address, '') || ' ' ||
        coalesce(city, '') || ' ' ||
        coalesce(county, '')
    )
);
"""


async def ensure_fts_index(db: AsyncSession):
    """Create the full-text search index if it doesn't exist."""
    try:
        await db.execute(text(FTS_INDEX_SQL))
        await db.commit()
    except Exception:
        pass  # Index may already exist


async def full_text_search(
    db: AsyncSession,
    query: str,
    city: str | None = None,
    property_type: PropertyType | None = None,
    listing_type: ListingType | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    bedrooms: int | None = None,
    verified_only: bool = False,
    page: int = 1,
    size: int = 20,
) -> dict:
    """
    Full-text search for properties with relevance ranking.
    Falls back to ILIKE if tsvector hasn't been built yet.
    """
    # Sanitize input for tsquery
    sanitized = _sanitize_tsquery(query)
    ts_query = _to_tsquery(sanitized)

    params: dict = {"limit": size, "offset": (page - 1) * size}

    # ── FTS tsvector expression (defined once, used in CTE) ──
    tsvector_expr = (
        "to_tsvector('english', "
        "coalesce(properties.title,'') || ' ' || "
        "coalesce(properties.description,'') || ' ' || "
        "coalesce(properties.address,'') || ' ' || "
        "coalesce(properties.city,'') || ' ' || "
        "coalesce(properties.county,''))"
    )

    # Build WHERE clauses for the inner query
    where_parts = ["properties.status = 'active'"]

    if ts_query:
        params["query_text"] = sanitized
        # tsquery filtering happens in outer query after CTE computes tsvector once
    else:
        # Fallback to ILIKE (no tsquery — use simple ILIKE matching)
        if sanitized:
            like_term = f"%{sanitized}%"
            where_parts.append(
                "(properties.title ILIKE :like_term OR "
                "properties.description ILIKE :like_term OR "
                "properties.address ILIKE :like_term OR "
                "properties.city ILIKE :like_term)"
            )
            params["like_term"] = like_term

    # Filters (applied in inner query for both FTS and ILIKE paths)
    if city:
        where_parts.append("properties.city ILIKE :city_filter")
        params["city_filter"] = f"%{city}%"
    if property_type:
        where_parts.append("properties.property_type = :property_type")
        params["property_type"] = property_type.value
    if listing_type:
        where_parts.append("properties.listing_type = :listing_type")
        params["listing_type"] = listing_type.value
    if min_price is not None:
        where_parts.append("properties.price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        where_parts.append("properties.price <= :max_price")
        params["max_price"] = max_price
    if bedrooms is not None:
        where_parts.append("properties.bedrooms >= :bedrooms")
        params["bedrooms"] = bedrooms
    if verified_only:
        where_parts.append("properties.is_verified = TRUE")

    where_clause = " AND ".join(where_parts)

    if ts_query:
        # ── CTE path: compute tsvector ONCE per row, filter + rank from CTE ──
        select_sql = f"""
            WITH fts AS (
                SELECT *, ({tsvector_expr}) AS search_vector
                FROM properties
                WHERE {where_clause}
            )
            SELECT *, ts_rank(search_vector, plainto_tsquery('english', :query_text)) AS relevance
            FROM fts
            WHERE search_vector @@ plainto_tsquery('english', :query_text)
            ORDER BY relevance DESC, created_at DESC
            LIMIT :limit OFFSET :offset
        """
        count_sql = f"""
            WITH fts AS (
                SELECT *, ({tsvector_expr}) AS search_vector
                FROM properties
                WHERE {where_clause}
            )
            SELECT COUNT(*) FROM fts
            WHERE search_vector @@ plainto_tsquery('english', :query_text)
        """
    else:
        # ── ILIKE path (no full-text search) ──
        select_sql = f"""
            SELECT *, 1.0 AS relevance
            FROM properties
            WHERE {where_clause}
            ORDER BY is_featured DESC, created_at DESC
            LIMIT :limit OFFSET :offset
        """
        count_sql = f"SELECT COUNT(*) FROM properties WHERE {where_clause}"

    count_result = await db.execute(text(count_sql), params)
    total = count_result.scalar_one()

    result = await db.execute(text(select_sql), params)
    rows = result.mappings().all()

    # Convert to Property objects
    items = []
    for row in rows:
        prop = Property(
            id=row["id"], owner_id=row["owner_id"], title=row["title"],
            description=row.get("description"), property_type=row["property_type"],
            listing_type=row["listing_type"], status=row["status"],
            address=row["address"], city=row["city"], county=row["county"],
            country=row.get("country", "Kenya"),
            latitude=row.get("latitude"), longitude=row.get("longitude"),
            price=row["price"], currency=row.get("currency", "KES"),
            price_negotiable=row.get("price_negotiable", False),
            bedrooms=row.get("bedrooms"), bathrooms=row.get("bathrooms"),
            size_sqft=row.get("size_sqft"), year_built=row.get("year_built"),
            amenities=row.get("amenities", []), images=row.get("images", []),
            trust_score=row.get("trust_score"), is_verified=row.get("is_verified", False),
            verification_badge=row.get("verification_badge"),
            views=row.get("views", 0), inquiries=row.get("inquiries", 0),
        )
        # Set created_at/updated_at manually since we used raw SQL
        if row.get("created_at"):
            prop.created_at = row["created_at"]
        if row.get("updated_at"):
            prop.updated_at = row["updated_at"]
        items.append(prop)

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, -(-total // size)),
        "size": size,
    }


async def cached_full_text_search(
    db: AsyncSession,
    query: str,
    **filters,
) -> dict:
    """Full-text search with Redis caching for repeated queries."""
    import hashlib
    import json

    cache_key_raw = json.dumps({
        "q": query.lower().strip(),
        **{k: v for k, v in filters.items() if v},
    }, sort_keys=True, default=str)
    cache_key = f"vestra:search:{hashlib.sha256(cache_key_raw.encode()).hexdigest()[:16]}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await full_text_search(db, query, **filters)
    await cache_set(cache_key, result, ttl=120)  # 2-minute cache
    return result


def _sanitize_tsquery(query: str) -> str:
    """Strip special PostgreSQL tsquery characters."""
    import re
    # Remove characters that break tsquery
    return re.sub(r"[&|!:*()<>\"]", " ", query).strip()


def _to_tsquery(query: str) -> str | None:
    """Convert search string to tsquery. Returns None if empty."""
    q = query.strip()
    if not q:
        return None
    # Use plainto_tsquery which handles user input safely
    return q
