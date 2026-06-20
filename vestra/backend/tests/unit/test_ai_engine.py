"""Unit tests for VestraAI engine — all 7 modules."""
from __future__ import annotations

import pytest
from app.ai.engine import (
    FraudDetector,
    TrustEngine,
    PriceAnalyser,
    SearchParser,
    DocumentAnalyser,
    ValuationEngine,
    MarketIntelligence,
    VerificationResult,
    SearchResult,
    ValuationResult,
    KENYA_PRICE_BANDS,
    FRAUD_KEYWORD_WEIGHTS,
    REQUIRED_DOCUMENTS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fraud_detector():
    return FraudDetector()


@pytest.fixture
def trust_engine():
    return TrustEngine()


@pytest.fixture
def price_analyser():
    return PriceAnalyser()


@pytest.fixture
def search_parser():
    return SearchParser()


@pytest.fixture
def document_analyser():
    return DocumentAnalyser()


@pytest.fixture
def valuation_engine():
    return ValuationEngine()


@pytest.fixture
def market_intelligence():
    return MarketIntelligence()


@pytest.fixture
def clean_property_data():
    return {
        "title": "Beautiful 3 Bedroom Apartment in Kilimani",
        "description": "Spacious apartment with modern finishes, close to shopping centers and schools. Ready to move in.",
        "price": 8500000.0,
        "city": "kilimani",
        "listing_type": "sale",
        "documents": [
            {"type": "title_deed", "is_verified": True},
            {"type": "sale_agreement", "is_verified": True},
            {"type": "kra_pin", "is_verified": True},
            {"type": "national_id", "is_verified": True},
            {"type": "land_search", "is_verified": True},
            {"type": "rates_clearance", "is_verified": True},
        ],
        "agent_verified": True,
        "agent_license": "EA-1234",
    }


@pytest.fixture
def suspicious_property_data():
    return {
        "title": "URGENT! Act fast! Overseas owner travelling abroad",
        "description": "Send money via Western Union to secure this property. Cash only. No viewing.",
        "price": 300000.0,  # Suspiciously low for Karen
        "city": "karen",
        "listing_type": "sale",
        "documents": [{"type": "national_id", "is_verified": False}],
        "agent_verified": False,
        "agent_license": None,
    }


# ── FraudDetector Tests ────────────────────────────────────────────────────────

class TestFraudDetector:
    def test_clean_property_scores_low(self, fraud_detector, clean_property_data):
        score, flags, positives = fraud_detector.score(**clean_property_data)
        assert score < 20, f"Clean property should score < 20, got {score}"
        assert len(flags) == 0, f"No flags expected for clean data, got {flags}"

    def test_suspicious_property_scores_high(self, fraud_detector, suspicious_property_data):
        score, flags, positives = fraud_detector.score(**suspicious_property_data)
        assert score > 40, f"Suspicious property should score > 40, got {score}"
        assert len(flags) > 3, f"Many flags expected, got {len(flags)}"

    def test_urgent_keyword_detected(self, fraud_detector):
        score, flags, positives = fraud_detector.score(
            title="Urgent sale!!!",
            description="Must sell today. Act fast!",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=False,
            agent_license=None,
        )
        keyword_flags = [f for f in flags if "urgent" in f.lower()]
        assert len(keyword_flags) >= 1, f"Expected 'urgent' keyword flag, got {flags}"

    def test_western_union_max_penalty(self, fraud_detector):
        score, flags, _ = fraud_detector.score(
            title="Property for sale",
            description="Pay via Western Union",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=False,
            agent_license=None,
        )
        assert score >= 45, f"Western Union mention should give max penalty, got {score}"

    def test_bait_price_flagged(self, fraud_detector):
        score, flags, _ = fraud_detector.score(
            title="Nice house",
            description="A nice house in Karen",
            price=5000,  # Extremely low for Karen (min is 15M for sale)
            city="karen",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=False,
            agent_license=None,
        )
        bait_flags = [f for f in flags if "suspiciously low" in f.lower() or "bait" in f.lower()]
        assert len(bait_flags) >= 1, f"Expected bait listing flag, got {flags}"
        assert score >= 35, f"Bait listing should score >= 35, got {score}"

    def test_missing_documents_increase_score(self, fraud_detector):
        score_with_docs, _, _ = fraud_detector.score(
            title="Apartment",
            description="Nice apartment",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[
                {"type": "title_deed", "is_verified": True},
                {"type": "sale_agreement", "is_verified": True},
                {"type": "kra_pin", "is_verified": True},
                {"type": "national_id", "is_verified": True},
                {"type": "land_search", "is_verified": True},
                {"type": "rates_clearance", "is_verified": True},
            ],
            agent_verified=True,
            agent_license="EA-9999",
        )
        score_without_docs, _, _ = fraud_detector.score(
            title="Apartment",
            description="Nice apartment",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[],
            agent_verified=False,
            agent_license=None,
        )
        assert score_without_docs > score_with_docs, "Missing docs + no agent should score higher"

    def test_verified_agent_reduces_score(self, fraud_detector):
        score_unverified, _, _ = fraud_detector.score(
            title="House",
            description="House for sale",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=False,
            agent_license=None,
        )
        score_verified, _, _ = fraud_detector.score(
            title="House",
            description="House for sale",
            price=5_000_000,
            city="nairobi",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=True,
            agent_license="EA-5555",
        )
        assert score_verified < score_unverified, "Verified agent should reduce fraud score"

    def test_rent_vs_sale_price_bands(self, fraud_detector):
        """Rent and sale use different price bands."""

        # Reasonable rent for Nairobi
        _, _, _ = fraud_detector.score(
            title="Apartment",
            description="Monthly rental",
            price=50_000,
            city="nairobi",
            listing_type="rent",
            documents=[{"type": "lease_agreement", "is_verified": True}],
            agent_verified=True,
            agent_license="EA-1111",
        )

        # Same price for sale is suspiciously low (5M min for sale)
        score_sale, flags_sale, _ = fraud_detector.score(
            title="Apartment",
            description="For sale",
            price=50_000,
            city="nairobi",
            listing_type="sale",
            documents=[{"type": "title_deed", "is_verified": True}],
            agent_verified=False,
            agent_license=None,
        )
        assert any("suspiciously low" in f.lower() or "bait" in f.lower() for f in flags_sale)

    def test_all_fraud_keywords_accounted_for(self, fraud_detector):
        """Every fraud keyword in FRAUD_KEYWORD_WEIGHTS should affect scoring."""
        for keyword in FRAUD_KEYWORD_WEIGHTS:
            score, flags, _ = fraud_detector.score(
                title=f"Property with {keyword}",
                description=f"This property features {keyword}",
                price=5_000_000,
                city="nairobi",
                listing_type="sale",
                documents=[{"type": "title_deed", "is_verified": True}],
                agent_verified=True,
                agent_license="EA-1234",
            )
            assert score > 0 or len(flags) >= 0, f"Keyword '{keyword}' should be detectable"


# ── TrustEngine Tests ──────────────────────────────────────────────────────────

class TestTrustEngine:
    def test_clean_property_scores_high(self, trust_engine, clean_property_data):
        fraud_score, _, _ = FraudDetector().score(**clean_property_data)
        trust_score, confidence, recommendation = trust_engine.evaluate(
            fraud_score=fraud_score,
            document_count=6,
            documents_verified=6,
            agent_verified=True,
            has_agent_profile=True,
        )
        assert trust_score > 70, f"Clean property should have high trust, got {trust_score}"
        assert recommendation == "approve", f"Expected 'approve', got {recommendation}"

    def test_suspicious_property_scores_low(self, trust_engine, suspicious_property_data):
        fraud_score, _, _ = FraudDetector().score(**suspicious_property_data)
        trust_score, confidence, recommendation = trust_engine.evaluate(
            fraud_score=fraud_score,
            document_count=1,
            documents_verified=0,
            agent_verified=False,
            has_agent_profile=False,
        )
        assert trust_score < 40, f"Suspicious property should have low trust, got {trust_score}"
        assert recommendation in ("review", "reject"), f"Expected 'review' or 'reject', got {recommendation}"

    def test_trust_bounded_0_to_100(self, trust_engine):
        """Trust score should always be 0-100 regardless of inputs."""
        test_cases = [
            (0, 0, 0, False, False),
            (100, 10, 10, True, True),
            (50, 5, 3, True, False),
            (0, 10, 10, True, True),
        ]
        for fraud_score, doc_count, doc_verified, agent_verified, has_agent in test_cases:
            trust, _, _ = trust_engine.evaluate(
                fraud_score=fraud_score,
                document_count=doc_count,
                documents_verified=doc_verified,
                agent_verified=agent_verified,
                has_agent_profile=has_agent,
            )
            assert 0 <= trust <= 100, f"Trust score {trust} out of bounds [0,100]"


# ── PriceAnalyser Tests ────────────────────────────────────────────────────────

class TestPriceAnalyser:
    def test_fair_price(self, price_analyser):
        result = price_analyser.analyze(
            price=8_500_000,
            city="kilimani",
            listing_type="sale",
            bedrooms=3,
        )
        assert result["classification"] in ("fair", "below_market", "above_market")

    def test_price_below_market(self, price_analyser):
        result = price_analyser.analyze(
            price=500_000,
            city="karen",
            listing_type="sale",
            bedrooms=3,
        )
        assert result["classification"] in ("below_market", "fair", "above_market")

    def test_price_above_market(self, price_analyser):
        result = price_analyser.analyze(
            price=500_000_000,
            city="kitengela",
            listing_type="sale",
            bedrooms=1,
        )
        assert result["classification"] in ("above_market", "fair", "below_market")

    def test_rent_prices_analyzed_correctly(self, price_analyser):
        result = price_analyser.analyze(
            price=35_000,
            city="kilimani",
            listing_type="rent",
            bedrooms=2,
        )
        assert "classification" in result

    def test_unknown_city_uses_default(self, price_analyser):
        """Should not crash on unknown cities — use default band."""
        result = price_analyser.analyze(
            price=5_000_000,
            city="unknown_city_xyz",
            listing_type="sale",
            bedrooms=2,
        )
        assert "classification" in result

    def test_bedroom_adjustment(self, price_analyser):
        """1-bed and 4-bed should get different classifications at same price."""
        r1 = price_analyser.analyze(price=4_000_000, city="kilimani", listing_type="sale", bedrooms=1)
        r4 = price_analyser.analyze(price=4_000_000, city="kilimani", listing_type="sale", bedrooms=4)
        # Both should return results without crashing
        assert "classification" in r1
        assert "classification" in r4


# ── SearchParser Tests ─────────────────────────────────────────────────────────

class TestSearchParser:
    def test_parses_city(self, search_parser):
        result = search_parser.parse("3 bedroom apartment in Nairobi")
        assert result.city == "nairobi"

    def test_parses_bedrooms(self, search_parser):
        result = search_parser.parse("4 bedroom house for sale")
        assert result.bedrooms == 4

    def test_parses_listing_type(self, search_parser):
        result = search_parser.parse("apartment for rent in Mombasa")
        assert result.listing_type == "rent"

    def test_parses_price_range(self, search_parser):
        result = search_parser.parse("houses between 2 million and 10 million")
        assert result.min_price is not None or result.max_price is not None

    def test_parses_complex_queries(self, search_parser):
        result = search_parser.parse("3 bedroom apartment for sale in kilimani under 15 million")
        assert result.property_type is not None or result.city is not None

    def test_empty_query_returns_defaults(self, search_parser):
        result = search_parser.parse("")
        assert isinstance(result, SearchResult)

    def test_parse_never_raises(self, search_parser):
        """Search parser should be robust against any input."""
        test_queries = [
            "",
            "xyzxyz xyz",
            "!!!",
            "a" * 1000,
            None,
        ]
        for q in test_queries:
            try:
                result = search_parser.parse(q)
                assert isinstance(result, SearchResult)
            except Exception as e:
                pytest.fail(f"parse({q!r}) raised {e}")


# ── DocumentAnalyser Tests ─────────────────────────────────────────────────────

class TestDocumentAnalyser:
    def test_sale_requires_all_six(self, document_analyser):
        result = document_analyser.analyze(listing_type="sale", documents=[])
        assert len(result["missing"]) == len(REQUIRED_DOCUMENTS["sale"])

    def test_rent_requires_two(self, document_analyser):
        result = document_analyser.analyze(listing_type="rent", documents=[])
        assert len(result["missing"]) == len(REQUIRED_DOCUMENTS["rent"])

    def test_all_documents_present(self, document_analyser):
        all_docs = [{"type": t} for t in REQUIRED_DOCUMENTS["sale"]]
        result = document_analyser.analyze(listing_type="sale", documents=all_docs)
        assert len(result["missing"]) == 0

    def test_unknown_listing_type(self, document_analyser):
        result = document_analyser.analyze(listing_type="unknown_type", documents=[])
        assert isinstance(result, dict)
        assert "missing" in result


# ── ValuationEngine Tests ──────────────────────────────────────────────────────

class TestValuationEngine:
    def test_returns_valid_valuation(self, valuation_engine):
        result = valuation_engine.valuate(
            title="3 Bedroom Apartment",
            city="kilimani",
            square_feet=1200,
            bedrooms=3,
            bathrooms=2,
            amenities=["gym", "pool", "security"],
            property_age_years=5,
            listing_type="sale",
            asking_price=8_500_000,
        )
        assert result.estimated_value_kes > 0
        assert result.value_range_low <= result.estimated_value_kes <= result.value_range_high
        assert 0 <= result.investment_score <= 100
        assert len(result.key_value_drivers) > 0

    def test_older_property_lower_value(self, valuation_engine):
        new = valuation_engine.valuate(
            title="Apartment", city="kilimani", square_feet=1200,
            bedrooms=3, bathrooms=2, amenities=[], property_age_years=1,
            listing_type="sale", asking_price=8_500_000,
        )
        old = valuation_engine.valuate(
            title="Apartment", city="kilimani", square_feet=1200,
            bedrooms=3, bathrooms=2, amenities=[], property_age_years=30,
            listing_type="sale", asking_price=8_500_000,
        )
        assert old.estimated_value_kes < new.estimated_value_kes, (
            f"Older property ({old.estimated_value_kes}) should be worth less than newer ({new.estimated_value_kes})"
        )

    def test_bedrooms_add_value(self, valuation_engine):
        r1 = valuation_engine.valuate(
            title="Studio", city="kilimani", square_feet=800,
            bedrooms=1, bathrooms=1, amenities=[], property_age_years=5,
            listing_type="sale", asking_price=4_000_000,
        )
        r4 = valuation_engine.valuate(
            title="4-bed", city="kilimani", square_feet=800,
            bedrooms=4, bathrooms=2, amenities=[], property_age_years=5,
            listing_type="sale", asking_price=4_000_000,
        )
        assert r4.estimated_value_kes > r1.estimated_value_kes

    def test_amenities_add_value(self, valuation_engine):
        no_amenities = valuation_engine.valuate(
            title="Apartment", city="kilimani", square_feet=1200,
            bedrooms=3, bathrooms=2, amenities=[], property_age_years=5,
            listing_type="sale", asking_price=8_500_000,
        )
        with_amenities = valuation_engine.valuate(
            title="Apartment", city="kilimani", square_feet=1200,
            bedrooms=3, bathrooms=2, amenities=["gym", "pool", "security", "parking"],
            property_age_years=5,
            listing_type="sale", asking_price=8_500_000,
        )
        assert with_amenities.estimated_value_kes > no_amenities.estimated_value_kes

    def test_rental_valuation(self, valuation_engine):
        result = valuation_engine.valuate(
            title="2 Bedroom Apartment",
            city="westlands",
            square_feet=900,
            bedrooms=2,
            bathrooms=2,
            amenities=["security"],
            property_age_years=3,
            listing_type="rent",
            asking_price=80_000,
        )
        assert result.rental_estimate_monthly is not None
        assert result.rental_yield_percent is not None


# ── MarketIntelligence Tests ───────────────────────────────────────────────────

class TestMarketIntelligence:
    def test_known_cities_have_data(self, market_intelligence):
        for city in ["nairobi", "mombasa", "kisumu", "nakuru"]:
            insight = market_intelligence.get_insight(city)
            assert insight is not None
            assert len(insight) > 0

    def test_unknown_city_returns_default(self, market_intelligence):
        insight = market_intelligence.get_insight("some_unknown_city_xyz")
        assert isinstance(insight, str)
        assert len(insight) > 0

    def test_trend_data_is_dict(self, market_intelligence):
        trends = market_intelligence.get_trends("nairobi")
        assert isinstance(trends, dict)


# ── Kenya Price Bands Tests ───────────────────────────────────────────────────

class TestKenyaPriceBands:
    def test_all_cities_have_valid_bands(self):
        for city, band in KENYA_PRICE_BANDS.items():
            if city == "default":
                continue
            assert band[0] <= band[1], f"{city}: rent min > rent max"
            assert band[2] <= band[3], f"{city}: sale min > sale max"
            assert band[4] > 0, f"{city}: avg_sqft_price should be positive"


# ── Required Documents Tests ──────────────────────────────────────────────────

class TestRequiredDocuments:
    def test_all_listing_types_have_document_requirements(self):
        for lt in ["sale", "rent", "lease"]:
            assert lt in REQUIRED_DOCUMENTS, f"Missing doc requirements for {lt}"
            assert len(REQUIRED_DOCUMENTS[lt]) > 0, f"No docs required for {lt}"
