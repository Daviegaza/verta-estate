"""
valuation_service.py — Vestra Property Valuation
Runs entirely on Vestra's own AI engine. No external APIs.
With Redis caching for expensive computations.
All synchronous AI calls run via run_in_executor to avoid blocking the event loop.
"""
import asyncio
import hashlib
import json
import logging
from app.ai.engine import vestra_ai
from app.core.redis import cache_get, cache_set

logger = logging.getLogger("vestra")


async def _run_in_executor(func, *args, **kwargs):
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def valuate_property(
    property_type: str,
    listing_type: str,
    city: str,
    county: str,
    address: str,
    size_sqft: float | None,
    bedrooms: int | None,
    bathrooms: int | None,
    year_built: int | None,
    amenities: list,
    submitted_price: float,
) -> dict:
    """Valuate a property using Vestra's own AI engine. Cached for 10 min."""
    # Build cache key from inputs (hash for cheap lookup — NOTE: address not in key)
    raw = json.dumps({
        "pt": property_type, "lt": listing_type, "city": city, "county": county,
        "sqft": float(size_sqft or 0), "beds": bedrooms or 0, "baths": bathrooms or 0,
        "yr": year_built or 0, "amen": sorted(amenities), "price": float(submitted_price),
    }, sort_keys=True)
    cache_key = f"vestra:val:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        result = await _run_in_executor(
            vestra_ai.valuate,
            {
                "property_type": property_type,
                "listing_type": listing_type,
                "city": city,
                "address": address,
                "size_sqft": size_sqft,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "year_built": year_built,
                "amenities": amenities,
                "price": submitted_price,
            },
        )
    except Exception as e:
        logger.error('{"event":"valuation_failed","city":"%s","error":"%s"}', city, str(e))
        result = {
            "estimated_value": submitted_price,
            "estimated_value_range": {"low": submitted_price * 0.8, "high": submitted_price * 1.2},
            "error": str(e),
        }

    await cache_set(cache_key, result, ttl=600)  # 10-min cache
    return result


async def get_market_insights(city: str, listing_type: str = "sale") -> dict:
    """Get market insights using Vestra's own AI engine. Cached for 30 min."""
    cache_key = f"vestra:market:{city.lower()}:{listing_type}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        result = await _run_in_executor(
            vestra_ai.market_insights, city, listing_type=listing_type
        )
    except Exception as e:
        logger.error('{"event":"market_insights_failed","city":"%s","error":"%s"}', city, str(e))
        result = {
            "city": city,
            "status": "unavailable",
            "error": str(e),
        }

    await cache_set(cache_key, result, ttl=1800)  # 30-min cache
    return result
