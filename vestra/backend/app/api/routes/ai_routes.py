from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.valuation_service import valuate_property, get_market_insights
from app.services.ai_service import generate_ai_property_search
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
