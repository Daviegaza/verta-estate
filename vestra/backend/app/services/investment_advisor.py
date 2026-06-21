"""
AI Investment Recommendation Engine — VESTRA v4.3.0

Analyzes properties and market data to generate personalized investment
recommendations with risk-adjusted return projections.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.ai.engine import VestraAI
from app.core.redis import redis_client

logger = logging.getLogger("vestra.investment_advisor")

# ── Cache TTLs ────────────────────────────────────────────────────────────────
CACHE_TTL_MARKET = 3600  # 1 hour
CACHE_TTL_RECOMMENDATION = 1800  # 30 minutes


@dataclass
class InvestmentScore:
    """Composite investment attractiveness score."""
    overall: float = 0.0  # 0-100
    roi_potential: float = 0.0
    risk_level: float = 0.0  # 0-100, higher = riskier
    market_timing: float = 0.0  # 0-100, how good is the timing
    location_score: float = 0.0
    cashflow_score: float = 0.0
    appreciation_potential: float = 0.0  # annual %
    recommendation: str = ""  # "strong_buy", "buy", "hold", "caution", "avoid"
    summary: str = ""
    factors: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class MarketConditions:
    """Current market conditions for a city/area."""
    city: str
    market_status: str  # "hot", "balanced", "buyers_market"
    avg_price_per_sqm: float
    avg_rental_yield: float
    price_trend: str  # "rising", "stable", "declining"
    demand_level: str  # "high", "medium", "low"
    supply_level: str  # "tight", "balanced", "oversupplied"
    days_on_market_avg: int
    investor_sentiment: float  # 0-100


class InvestmentAdvisor:
    """AI-powered property investment advisor for the Kenyan market."""

    def __init__(self) -> None:
        self._ai = VestraAI()
        self._market_cache: dict[str, MarketConditions] = {}

    async def analyze_property(
        self,
        price: float,
        city: str,
        area: str,
        property_type: str,
        bedrooms: int = 2,
        monthly_rent_estimate: float | None = None,
        property_size_sqm: float | None = None,
        trust_score: float | None = None,
    ) -> InvestmentScore:
        """Analyze a property and return an investment score."""
        score = InvestmentScore()

        # ── 1. Market Conditions ──────────────────────────────────────────
        market = await self._get_market_conditions(city)

        # ── 2. ROI Potential (25%) ────────────────────────────────────────
        if monthly_rent_estimate and price > 0:
            annual_rent = monthly_rent_estimate * 12
            gross_yield = (annual_rent / price) * 100

            if gross_yield > 10:
                score.roi_potential = 90
                score.cashflow_score = 85
            elif gross_yield > 7:
                score.roi_potential = 70
                score.cashflow_score = 65
            elif gross_yield > 5:
                score.roi_potential = 50
                score.cashflow_score = 45
            elif gross_yield > 3:
                score.roi_potential = 30
                score.cashflow_score = 25
            else:
                score.roi_potential = 10
                score.cashflow_score = 10

            score.factors.append(f"Gross rental yield: {gross_yield:.1f}%")
        else:
            # Estimate based on market averages
            score.roi_potential = 50
            score.cashflow_score = 50

        # ── 3. Location Score (20%) ───────────────────────────────────────
        location_scores = {
            "nairobi": {"Karen": 85, "Kilimani": 80, "Lavington": 82, "Westlands": 78, "Kileleshwa": 75,
                        "Runda": 83, "Muthaiga": 88, "Hurlingham": 76, "Parklands": 72, "Eastleigh": 55,
                        "Kasarani": 48, "Roysambu": 50, "Donholm": 45, "Embakasi": 42, "Langata": 65,
                        "Ngong Road": 68, "Ridgeways": 72, "Garden Estate": 70, "South B": 48, "South C": 52},
            "mombasa": {"Nyali": 78, "Bamburi": 62, "Kizingo": 70, "Shanzu": 65, "Diani": 75,
                        "Kilifi": 58, "Malindi": 55, "Watamu": 60, "Mtwapa": 48},
            "kisumu": {"Milimani": 72, "Riat Hills": 68, "Mamboleo": 50, "Kanyakwar": 45},
            "nakuru": {"Milimani": 65, "Section 58": 55, "Lanet": 42, "Njoro": 38},
        }

        area_scores = location_scores.get(city.lower(), {})
        score.location_score = area_scores.get(area, 50)
        score.factors.append(f"Location: {area}, {city} (score: {score.location_score}/100)")

        # ── 4. Risk Assessment (20%) ──────────────────────────────────────
        risks = 0

        if trust_score is not None and trust_score < 50:
            risks += 30
            score.risks.append(f"Low trust score ({trust_score}/100) — potential verification issues")

        if property_type in ("land", "plot") and city.lower() in ("nairobi", "mombasa"):
            risks += 10
            score.risks.append("Land purchases carry title deed verification risk")

        if price > 20_000_000 and score.location_score < 60:
            risks += 15
            score.risks.append("High price point in lower-tier area")

        if market.market_status == "buyers_market":
            risks += 5
            score.risks.append("Buyer's market — expect longer holding periods")
        elif market.market_status == "hot":
            risks += 10
            score.risks.append("Hot market — risk of overpaying")

        if market.days_on_market_avg > 180:
            risks += 10
            score.risks.append(f"Slow market: avg {market.days_on_market_avg} days on market")

        score.risk_level = min(100, max(5, risks + 10))

        # ── 5. Market Timing (15%) ────────────────────────────────────────
        if market.market_status == "balanced":
            score.market_timing = 75
        elif market.market_status == "buyers_market":
            score.market_timing = 60  # Good time to buy but longer holding
        elif market.market_status == "hot":
            score.market_timing = 40  # Be cautious

        if market.price_trend == "rising":
            score.market_timing = min(100, score.market_timing + 15)
        elif market.price_trend == "declining":
            score.market_timing = max(10, score.market_timing - 20)

        score.factors.append(
            f"Market: {market.market_status.replace('_', ' ').title()} "
            f"(days on market: {market.days_on_market_avg})"
        )

        # ── 6. Appreciation Potential ─────────────────────────────────────
        if market.price_trend == "rising":
            score.appreciation_potential = 8.0 + (score.location_score / 20)
        elif market.price_trend == "declining":
            score.appreciation_potential = -2.0
        else:
            score.appreciation_potential = 4.0

        # Cap at reasonable range
        score.appreciation_potential = max(-5.0, min(score.appreciation_potential, 15.0))
        score.factors.append(f"Projected annual appreciation: {score.appreciation_potential:+.1f}%")

        # ── 7. Overall Score ──────────────────────────────────────────────
        score.overall = (
            score.roi_potential * 0.25 +
            score.location_score * 0.20 +
            (100 - score.risk_level) * 0.20 +
            score.market_timing * 0.15 +
            score.cashflow_score * 0.10 +
            (score.appreciation_potential * 5 if score.appreciation_potential > 0 else 0) * 0.10
        )

        score.overall = round(min(100, max(5, score.overall)), 1)

        # ── 8. Recommendation ─────────────────────────────────────────────
        if score.overall >= 80:
            score.recommendation = "strong_buy"
            score.summary = "Excellent investment opportunity. Strong location, good value, and favorable market conditions."
        elif score.overall >= 65:
            score.recommendation = "buy"
            score.summary = "Good investment with solid fundamentals. Perform standard due diligence."
        elif score.overall >= 50:
            score.recommendation = "hold"
            score.summary = "Decent property but consider negotiating price or exploring alternatives."
        elif score.overall >= 35:
            score.recommendation = "caution"
            score.summary = "Proceed with caution. Multiple risk factors identified. Thorough due diligence essential."
        else:
            score.recommendation = "avoid"
            score.summary = "High risk or poor returns. Recommend looking at other opportunities."

        return score

    async def _get_market_conditions(self, city: str) -> MarketConditions:
        """Get cached or computed market conditions for a city."""
        city_key = city.lower().strip()
        cache_key = f"vestra:market_conditions:{city_key}"

        # Check memory cache
        if city_key in self._market_cache:
            return self._market_cache[city_key]

        # Check Redis cache
        try:
            import json
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return MarketConditions(**data)
        except Exception:
            pass

        # Compute from AI engine
        insights = self._ai.market_insights(city)

        conditions = MarketConditions(
            city=city,
            market_status=insights.get("market_status", "balanced"),
            avg_price_per_sqm=insights.get("avg_price_per_sqm", 0),
            avg_rental_yield=insights.get("avg_rental_yield", 5.0),
            price_trend=insights.get("price_trend", "stable"),
            demand_level=insights.get("demand_level", "medium"),
            supply_level=insights.get("supply_level", "balanced"),
            days_on_market_avg=insights.get("days_on_market_avg", 90),
            investor_sentiment=insights.get("investor_sentiment", 50),
        )

        # Cache in memory
        self._market_cache[city_key] = conditions

        # Cache in Redis
        try:
            import json
            await redis_client.set(
                cache_key,
                json.dumps(conditions.__dict__),
                ex=CACHE_TTL_MARKET,
            )
        except Exception:
            pass

        return conditions

    def get_recommendation_emoji(self, recommendation: str) -> str:
        """Get emoji for recommendation level."""
        return {
            "strong_buy": "🏆",
            "buy": "👍",
            "hold": "🤔",
            "caution": "⚠️",
            "avoid": "🚫",
        }.get(recommendation, "❓")

    def get_recommendation_color(self, recommendation: str) -> str:
        """Get Tailwind color class for recommendation."""
        return {
            "strong_buy": "emerald",
            "buy": "green",
            "hold": "blue",
            "caution": "amber",
            "avoid": "red",
        }.get(recommendation, "gray")


# Singleton
investment_advisor = InvestmentAdvisor()
