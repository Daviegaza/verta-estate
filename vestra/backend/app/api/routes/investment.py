"""
Investment Advisor Routes — VESTRA v4.3.0

AI-powered property investment analysis and recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.investment_advisor import investment_advisor

router = APIRouter(prefix="/investment", tags=["investment"])


@router.get("/analyze")
async def analyze_investment(
    price: float = Query(..., gt=0, description="Property price in KES"),
    city: str = Query(..., min_length=2, description="City name"),
    area: str = Query(default="", description="Area/neighborhood"),
    property_type: str = Query("apartment", description="Property type"),
    bedrooms: int = Query(2, ge=0, le=20),
    monthly_rent_estimate: float | None = Query(None, gt=0, description="Estimated monthly rent in KES"),
    property_size_sqm: float | None = Query(None, gt=0, description="Property size in sq meters"),
    trust_score: float | None = Query(None, ge=0, le=100),
):
    """Analyze a property and get an AI investment recommendation."""
    if not area:
        area = city  # Default to city level if no area specified

    score = await investment_advisor.analyze_property(
        price=price,
        city=city,
        area=area,
        property_type=property_type,
        bedrooms=bedrooms,
        monthly_rent_estimate=monthly_rent_estimate,
        property_size_sqm=property_size_sqm,
        trust_score=trust_score,
    )

    return {
        "success": True,
        "analysis": {
            "overall_score": score.overall,
            "recommendation": score.recommendation,
            "recommendation_emoji": investment_advisor.get_recommendation_emoji(score.recommendation),
            "summary": score.summary,
            "scores": {
                "roi_potential": score.roi_potential,
                "risk_level": score.risk_level,
                "market_timing": score.market_timing,
                "location": score.location_score,
                "cashflow": score.cashflow_score,
            },
            "projected_appreciation": score.appreciation_potential,
            "factors": score.factors,
            "risks": score.risks,
        },
    }


@router.get("/market-conditions")
async def get_market_conditions(
    city: str = Query(..., min_length=2, description="City name"),
):
    """Get current market conditions for a city."""
    conditions = await investment_advisor._get_market_conditions(city)

    return {
        "success": True,
        "city": conditions.city,
        "market_status": conditions.market_status,
        "avg_price_per_sqm": conditions.avg_price_per_sqm,
        "avg_rental_yield": conditions.avg_rental_yield,
        "price_trend": conditions.price_trend,
        "demand_level": conditions.demand_level,
        "supply_level": conditions.supply_level,
        "days_on_market_avg": conditions.days_on_market_avg,
        "investor_sentiment": conditions.investor_sentiment,
    }
