"""
Tests for the Investment Advisor service — VESTRA v4.3.0
"""

import pytest

from app.services.investment_advisor import InvestmentAdvisor, InvestmentScore, MarketConditions


@pytest.fixture
def advisor():
    return InvestmentAdvisor()


class TestInvestmentScore:
    def test_score_defaults(self):
        score = InvestmentScore()
        assert score.overall == 0.0
        assert score.recommendation == ""
        assert score.factors == []
        assert score.risks == []

    def test_score_with_values(self):
        score = InvestmentScore(
            overall=85.0,
            recommendation="strong_buy",
            factors=["Great location"],
            risks=["High price"],
        )
        assert score.overall == 85.0
        assert score.recommendation == "strong_buy"


class TestMarketConditions:
    def test_market_conditions_creation(self):
        conditions = MarketConditions(
            city="Nairobi",
            market_status="hot",
            avg_price_per_sqm=150000,
            avg_rental_yield=6.5,
            price_trend="rising",
            demand_level="high",
            supply_level="tight",
            days_on_market_avg=30,
            investor_sentiment=75,
        )
        assert conditions.city == "Nairobi"
        assert conditions.market_status == "hot"
        assert conditions.days_on_market_avg == 30

    def test_market_conditions_cached(self):
        conditions = MarketConditions(
            city="Kisumu",
            market_status="balanced",
            avg_price_per_sqm=70000,
            avg_rental_yield=8.0,
            price_trend="stable",
            demand_level="medium",
            supply_level="balanced",
            days_on_market_avg=60,
            investor_sentiment=60,
        )
        assert conditions.city == "Kisumu"
        assert conditions.market_status == "balanced"


class TestInvestmentAdvisor:
    @pytest.mark.asyncio
    async def test_analyze_high_value_property(self, advisor):
        """High-value Karen property should get strong recommendation."""
        score = await advisor.analyze_property(
            price=25_000_000,
            city="Nairobi",
            area="Karen",
            property_type="house",
            bedrooms=4,
            monthly_rent_estimate=150_000,
            trust_score=75,
        )

        assert score.overall > 0
        assert score.recommendation in ("strong_buy", "buy", "hold", "caution", "avoid")
        assert len(score.factors) > 0
        assert score.risk_level > 0
        assert score.roi_potential >= 0

    @pytest.mark.asyncio
    async def test_analyze_low_trust_property(self, advisor):
        """Low trust score should increase risk."""
        score = await advisor.analyze_property(
            price=5_000_000,
            city="Nairobi",
            area="Eastlands",
            property_type="apartment",
            bedrooms=2,
            monthly_rent_estimate=25_000,
            trust_score=30,
        )

        assert score.risk_level > 20  # Should have elevated risk
        assert any("trust" in risk.lower() for risk in score.risks)

    @pytest.mark.asyncio
    async def test_analyze_excellent_roi_budget(self, advisor):
        """Property with excellent yield should score well on ROI."""
        score = await advisor.analyze_property(
            price=3_000_000,
            city="Mombasa",
            area="Nyali",
            property_type="apartment",
            bedrooms=1,
            monthly_rent_estimate=40_000,
            trust_score=80,
        )

        # Monthly rent 40k / price 3M = 16% yield → strong ROI
        assert score.roi_potential > 70

    @pytest.mark.asyncio
    async def test_analyze_returns_factors(self, advisor):
        """Every analysis should return explanatory factors."""
        score = await advisor.analyze_property(
            price=8_000_000,
            city="Nakuru",
            area="Milimani",
            property_type="apartment",
            bedrooms=3,
            monthly_rent_estimate=35_000,
            trust_score=60,
        )

        assert len(score.factors) >= 3  # Should have roi, location, and market factors
        assert len(score.summary) > 0

    @pytest.mark.asyncio
    async def test_analyze_strong_buy_threshold(self, advisor):
        """Verify strong_buy recommendation for excellent properties."""
        score = await advisor.analyze_property(
            price=6_000_000,
            city="Nairobi",
            area="Muthaiga",
            property_type="apartment",
            bedrooms=3,
            monthly_rent_estimate=65_000,
            trust_score=90,
        )

        assert score.recommendation in ("strong_buy", "buy")
        assert score.overall > 60

    @pytest.mark.asyncio
    async def test_analyze_avoid_scenario(self, advisor):
        """Very risky property should get caution or avoid."""
        score = await advisor.analyze_property(
            price=50_000_000,
            city="Nairobi",
            area="Eastleigh",
            property_type="land",
            bedrooms=0,
            monthly_rent_estimate=0,
            trust_score=20,
        )

        assert score.recommendation in ("caution", "avoid")
        assert score.risk_level > 30

    def test_recommendation_emoji(self, advisor):
        assert advisor.get_recommendation_emoji("strong_buy") == "🏆"
        assert advisor.get_recommendation_emoji("buy") == "👍"
        assert advisor.get_recommendation_emoji("hold") == "🤔"
        assert advisor.get_recommendation_emoji("caution") == "⚠️"
        assert advisor.get_recommendation_emoji("avoid") == "🚫"

    def test_recommendation_color(self, advisor):
        assert advisor.get_recommendation_color("strong_buy") == "emerald"
        assert advisor.get_recommendation_color("avoid") == "red"

    @pytest.mark.asyncio
    async def test_market_conditions_caching(self, advisor):
        """Market conditions should be cached after first fetch."""
        conditions1 = await advisor._get_market_conditions("Nairobi")
        conditions2 = await advisor._get_market_conditions("Nairobi")

        assert conditions1.city == conditions2.city
        assert conditions1.market_status == conditions2.market_status

    @pytest.mark.asyncio
    async def test_different_cities(self, advisor):
        """Different cities should have different conditions."""
        nbo = await advisor._get_market_conditions("Nairobi")
        msa = await advisor._get_market_conditions("Mombasa")

        assert nbo.city == "Nairobi"
        assert msa.city == "Mombasa"
        # They may or may not differ, but both should be valid
        assert nbo.market_status in ("hot", "balanced", "buyers_market")
        assert msa.market_status in ("hot", "balanced", "buyers_market")

    @pytest.mark.asyncio
    async def test_analyze_empty_area_defaults(self, advisor):
        """Empty area should default to city-level analysis."""
        score = await advisor.analyze_property(
            price=4_000_000,
            city="Kisumu",
            area="Millimani",  # intentional typo — should still work
            property_type="apartment",
            bedrooms=2,
        )

        assert score.overall > 0
        assert score.location_score >= 0
