"""
Smart AI Service — VESTRA's intelligent property search & recommendation engine.

Combines NLP parsing, semantic search, valuation, market intelligence, and
personalized recommendations into a single unified experience. This is the
"wow factor" that makes VESTRA the best property platform in Africa.

All AI runs on Vestra's own engine — no external APIs, no rate limits,
no costs, instant responses.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import vestra_ai
from app.core.redis import cache_get, cache_set

logger = logging.getLogger("vestra.smart_ai")


async def _run_in_executor(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# ── Smart Search (the killer feature) ───────────────────────────────────────

async def smart_search(
    db: AsyncSession,
    query: str,
    current_user_id: Optional[int] = None,
) -> dict:
    """
    One-stop AI property search. User types natural language,
    we return parsed filters + matching properties + market context + AI recommendations.

    This is the endpoint that makes users say "wow."
    """
    # Step 1: AI parses natural language → structured filters
    parsed = await _run_in_executor(vestra_ai.parse_search, query)

    # Step 2: Search properties using parsed filters
    from app.services.property_service import search_properties
    from app.schemas.property import PropertySearch

    search = PropertySearch(
        query=parsed.get("keywords"),
        city=parsed.get("city"),
        county=parsed.get("county"),
        property_type=parsed.get("property_type"),
        listing_type=parsed.get("listing_type"),
        min_price=parsed.get("min_price"),
        max_price=parsed.get("max_price"),
        bedrooms=parsed.get("bedrooms"),
    )
    results = await search_properties(db, search)

    # Step 3: Serialize results
    from app.api.routes.properties import _prop_to_dict as _serialize

    raw_items = results["items"]
    if raw_items and isinstance(raw_items[0], dict):
        items_data = raw_items
    else:
        items_data = [_serialize(item) for item in raw_items]

    # Step 4: AI ranks and annotates each result
    scored_items = []
    for item in items_data:
        trust_insight = _get_trust_insight(item.get("trust_score", 0))
        price_tip = await _get_price_tip(item, parsed.get("city") or item.get("city", "Nairobi"))
        scored_items.append({
            **item,
            "ai_trust_insight": trust_insight,
            "ai_price_tip": price_tip,
        })

    # Step 5: Market context
    city_for_market = parsed.get("city") or "Nairobi"
    listing_type_for_market = parsed.get("listing_type") or "sale"
    market_context = await _run_in_executor(
        vestra_ai.market_insights, city_for_market, listing_type_for_market
    )

    # Step 6: Smart recommendations based on search intent
    recommendations = _generate_recommendations(query, parsed, items_data)

    return {
        "interpretation": parsed.get("interpretation"),
        "filters_applied": parsed,
        "items": scored_items,
        "total": results["total"],
        "page": results["page"],
        "pages": results["pages"],
        "size": results["size"],
        "market_context": _summarize_market(market_context, city_for_market),
        "ai_recommendations": recommendations,
        "search_tips": _generate_search_tips(parsed, results["total"]),
    }


# ── Smart Property Insights ─────────────────────────────────────────────────

async def get_property_smart_insights(
    db: AsyncSession,
    property_id: int,
) -> dict:
    """
    Get deep AI insights for a single property: valuation, trust analysis,
    investment score, comparable properties, and neighborhood context.
    """
    from app.services.property_service import get_property_by_id

    prop = await get_property_by_id(db, property_id)
    if not prop:
        return {"error": "Property not found"}

    # AI valuation
    valuation = await _run_in_executor(
        vestra_ai.valuate,
        {
            "city": prop.city or "Nairobi",
            "listing_type": prop.listing_type.value if hasattr(prop.listing_type, 'value') else str(prop.listing_type),
            "property_type": prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type),
            "bedrooms": prop.bedrooms,
            "size_sqft": getattr(prop, 'size_sqft', None),
            "year_built": getattr(prop, 'year_built', None),
            "amenities": getattr(prop, 'amenities', []) or [],
            "price": float(prop.price),
        },
    )

    # Trust analysis
    trust_analysis = _analyze_trust_score(
        getattr(prop, 'trust_score', 50),
        getattr(prop, 'is_verified', False),
    )

    # Market comparison
    city = prop.city or "Nairobi"
    market = await _run_in_executor(vestra_ai.market_insights, city)

    return {
        "valuation": valuation,
        "trust_analysis": trust_analysis,
        "market_snapshot": _summarize_market(market, city),
        "investment_verdict": _investment_verdict(valuation),
        "key_facts": _extract_key_facts(prop),
    }


# ── Helper functions ────────────────────────────────────────────────────────

def _get_trust_insight(trust_score: float) -> str:
    if trust_score >= 80:
        return "Highly trusted — verified documents and agent"
    elif trust_score >= 60:
        return "Good standing — most documents verified"
    elif trust_score >= 40:
        return "Proceed with caution — request more documents"
    else:
        return "Low trust — verify independently before transacting"


async def _get_price_tip(item: dict, city: str) -> str:
    price = float(item.get("price", 0))
    bedrooms = item.get("bedrooms", 0)
    listing_type = item.get("listing_type", "sale")

    try:
        tip_data = await _run_in_executor(
            vestra_ai._price.analyse, price, city, listing_type, bedrooms, None
        )
        classification = tip_data[0] if isinstance(tip_data, tuple) else tip_data.get("reasonableness", "fair")
        if classification == "below_market":
            return "Below market average — good value"
        elif classification == "above_market":
            return "Above market average — negotiate if possible"
        else:
            return "Fairly priced for this area"
    except Exception:
        return "Price analysis not available"


def _summarize_market(market_data: dict, city: str) -> str:
    if not market_data:
        return f"The {city} property market is active. Contact an agent for current listings."
    status = market_data.get("status", "active")
    trend = market_data.get("trend", "stable")
    return f"{city.title()} market is {status}. Trend: {trend}. AI-analyzed for you."


def _generate_recommendations(query: str, parsed: dict, items: list) -> list[str]:
    tips = []
    city = parsed.get("city", "")
    bedrooms = parsed.get("bedrooms")
    listing_type = parsed.get("listing_type", "")

    if not items:
        tips.append(f"No properties found matching your criteria in {city or 'your area'}. Try broadening your search.")
        if listing_type == "sale":
            tips.append("Consider looking at rental properties in this area — they're easier to find.")
        if bedrooms and bedrooms > 3:
            tips.append(f"Large homes ({bedrooms}br) are scarce. Try reducing bedroom count or expanding to nearby areas.")
        return tips

    tips.append(f"Found {len(items)} matching properties. All have been AI-analyzed for trust and value.")
    if city:
        tips.append(f"Tip: Properties in {city} typically include service charge. Confirm with agent before committing.")
    if listing_type == "rent":
        tips.append("Remember: Kenyan rental law requires 1 month notice before moving out.")
    else:
        tips.append("Always conduct a Land Registry search before paying for any property.")
    return tips


def _generate_search_tips(parsed: dict, total: int) -> list[str]:
    tips = []
    if total == 0:
        tips.append("Try removing some filters to see more results.")
        tips.append("Check spelling of the city or area name.")
        tips.append("Try searching with fewer keywords.")
    elif total > 50:
        tips.append("Many results found — add more filters to narrow down.")
        tips.append("Use the map view to browse by neighborhood.")
    return tips


def _analyze_trust_score(score: float, is_verified: bool) -> dict:
    level = "high" if score >= 70 else "medium" if score >= 40 else "low"
    return {
        "score": score,
        "level": level,
        "is_verified": is_verified,
        "summary": _get_trust_insight(score),
    }


def _investment_verdict(valuation: dict) -> str:
    score = valuation.get("investment_score", 50)
    if score >= 70:
        return "Strong investment potential — good value, desirable location."
    elif score >= 50:
        return "Moderate investment — fair value, consider long-term appreciation."
    else:
        return "Exercise caution — below-average investment metrics."


def _extract_key_facts(prop) -> list[str]:
    facts = []
    if hasattr(prop, 'bedrooms') and prop.bedrooms:
        facts.append(f"{prop.bedrooms} bedroom{'s' if prop.bedrooms > 1 else ''}")
    if hasattr(prop, 'bathrooms') and prop.bathrooms:
        facts.append(f"{prop.bathrooms} bathroom{'s' if prop.bathrooms > 1 else ''}")
    if hasattr(prop, 'size_sqft') and prop.size_sqft:
        facts.append(f"{prop.size_sqft:,.0f} sq ft")
    if hasattr(prop, 'price'):
        facts.append(f"KES {float(prop.price):,.0f}")
    return facts
