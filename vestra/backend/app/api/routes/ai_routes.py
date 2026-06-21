from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.valuation_service import valuate_property, get_market_insights
from app.services.ai_service import generate_ai_property_search
from app.services.smart_ai_service import smart_search, get_property_smart_insights
from app.services.property_service import get_property_by_id

router = APIRouter(prefix="/ai", tags=["Vestra AI"])


@router.get("/valuate/{property_id}")
async def valuate_property_endpoint(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """AI valuation for any listed property. Requires authentication."""
    prop = await get_property_by_id(db, property_id)
    if not prop:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Property not found")

    result = await valuate_property(
        property_type=prop.property_type.value,
        listing_type=prop.listing_type.value,
        city=prop.city,
        county=prop.county,
        address=prop.address,
        size_sqft=prop.size_sqft,
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        year_built=prop.year_built,
        amenities=prop.amenities or [],
        submitted_price=prop.price,
    )
    return {"property_id": property_id, "valuation": result}


@router.post("/valuate/custom")
async def valuate_custom(
    data: dict,
    current_user=Depends(get_current_user),
):
    """AI valuation for any property data — no listing required. Requires authentication."""
    result = await valuate_property(
        property_type=data.get("property_type", "residential"),
        listing_type=data.get("listing_type", "sale"),
        city=data.get("city", "Nairobi"),
        county=data.get("county", "Nairobi"),
        address=data.get("address", ""),
        size_sqft=data.get("size_sqft"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        year_built=data.get("year_built"),
        amenities=data.get("amenities", []),
        submitted_price=float(data.get("price", 0)),
    )
    return {"valuation": result}


@router.get("/market")
async def market_insights_endpoint(
    city: str = Query(..., description="Kenya city name"),
    listing_type: str = Query("sale", description="sale or rent"),
    current_user=Depends(get_current_user),
):
    """Get Vestra AI market intelligence for any city. Requires authentication."""
    result = await get_market_insights(city, listing_type)
    return {"city": city, "listing_type": listing_type, "insights": result}


@router.get("/search/parse")
async def parse_search_query(
    q: str = Query(..., description="Natural language search query"),
    current_user=Depends(get_current_user),
):
    """Parse a natural language search into structured filters using Vestra AI."""
    result = await generate_ai_property_search(q)
    return result


@router.get("/smart-search")
async def smart_search_endpoint(
    q: str = Query(..., description="Natural language: '3 bedroom apartment in Kilimani under 15 million'"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    ONE-STOP AI SEARCH — the killer feature.

    Type anything. Our AI:
    1. Understands your natural language
    2. Finds matching properties
    3. Ranks them with trust & value insights
    4. Provides market context and smart recommendations

    No external APIs. All runs on Vestra's own AI engine.
    """
    result = await smart_search(db, q, current_user_id=current_user.id)
    return result


@router.get("/insights/{property_id}")
async def property_insights_endpoint(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Deep AI insights for a property: valuation, trust, investment score,
    market comparison, and neighborhood context.
    """
    result = await get_property_smart_insights(db, property_id)
    return result


# ── Vestima Price Estimator ─────────────────────────────────────────────────

@router.get("/vestima/{property_id}")
async def vestima_estimate(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full Vestima price estimate for a listed property.
    Returns estimated value, confidence range, comparables, price per sq ft, and market trend.
    Cached for 1 hour behind the scenes.
    """
    from app.services.vestima_service import get_cached_vestima_estimate
    from fastapi import HTTPException

    result = await get_cached_vestima_estimate(db, property_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"property_id": property_id, "vestima": result}


@router.post("/vestima/custom")
async def vestima_custom_estimate(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Vestima price estimate for any custom property data — no listing required.
    Accepts: city, property_type, listing_type, bedrooms, size_sqft, year_built, amenities, price
    """
    from app.services.vestima_service import estimate_property

    result = await estimate_property(db, data)
    return {"vestima": result}


@router.get("/vestima/history/{property_id}")
async def vestima_estimate_history(
    property_id: int,
    limit: int = Query(5, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Historical Vestima estimates for a property.
    Shows how the AI's valuation has trended over time.
    """
    from app.services.vestima_service import get_vestima_history
    from fastapi import HTTPException

    result = await get_vestima_history(db, property_id, limit=limit)
    if not result:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"property_id": property_id, "history": result}


# ── Suggestions ──────────────────────────────────────────────────────────────

@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., description="Partial search query for autocomplete"),
):
    """
    Smart autocomplete suggestions based on real Kenya real estate patterns.
    No auth required — used by the landing page search box.
    """
    suggestions = _generate_live_suggestions(q)
    return {"query": q, "suggestions": suggestions}


# ── Smart suggestion engine ─────────────────────────────────────────────────

# Curated popular searches that always return results
_POPULAR_SEARCHES = [
    "2 bedroom apartment in Kilimani under 15 million",
    "3 bedroom house in Karen with garden",
    "studio apartment in Westlands for rent under 40k",
    "4 bedroom townhouse in Runda",
    "land for sale in Kitengela",
    "commercial office space in Upper Hill",
    "furnished apartment in Nairobi for short stay",
    "house for sale in Mombasa near the beach",
    "bedsitter in Ruaka for rent under 15k",
    "modern apartment in Lavington with gym and pool",
    "farm land in Kiambu",
    "warehouse for lease in Athi River",
]


def _generate_live_suggestions(query: str) -> list[dict]:
    """Generate contextual suggestions that feel smart."""
    q_lower = query.lower().strip()
    if not q_lower or len(q_lower) < 2:
        return [{"text": s, "type": "popular"} for s in _POPULAR_SEARCHES[:6]]

    results = []

    # Match popular searches
    for s in _POPULAR_SEARCHES:
        if q_lower in s.lower() or any(w in s.lower() for w in q_lower.split()):
            results.append({"text": s, "type": "popular"})

    # City-specific suggestions
    for city in ["Nairobi", "Kilimani", "Karen", "Westlands", "Mombasa", "Kisumu", "Runda", "Kitengela"]:
        if city.lower().startswith(q_lower) or q_lower in city.lower():
            for lt in ["sale", "rent"]:
                results.append({
                    "text": f"property for {lt} in {city}",
                    "type": "city",
                })

    # Bedroom-based suggestions
    import re
    bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', q_lower)
    if bed_match:
        beds = bed_match.group(1)
        results.append({"text": f"{beds} bedroom apartment in Nairobi for sale", "type": "smart"})
        results.append({"text": f"{beds} bedroom house in Karen", "type": "smart"})

    # Return unique, max 8
    seen = set()
    unique = []
    for r in results:
        if r["text"] not in seen:
            seen.add(r["text"])
            unique.append(r)
    return unique[:8] if unique else [{"text": s, "type": "popular"} for s in _POPULAR_SEARCHES[:5]]
