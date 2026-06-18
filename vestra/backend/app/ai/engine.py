"""
VESTRA AI ENGINE
================
Vestra's own built-in AI. No external APIs. No Anthropic. No OpenAI.
Runs entirely inside this system.

Modules:
  - FraudDetector      : scores fraud risk 0-100
  - TrustEngine        : computes property trust score
  - PriceAnalyser      : checks if price is under/fair/over
  - SearchParser       : parses natural language queries
  - DocumentAnalyser   : flags document issues
  - RecommendEngine    : recommends properties per user
  - MarketIntelligence : estimates market trends per city
"""

from __future__ import annotations
import re
import math
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# KENYA MARKET KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────────────────────

KENYA_PRICE_BANDS = {
    # city/area → (min_rent_kes, max_rent_kes, min_sale_kes, max_sale_kes, avg_sqft_price)
    "karen":          (80_000, 350_000, 15_000_000, 150_000_000, 95_000),
    "runda":          (90_000, 400_000, 20_000_000, 200_000_000, 110_000),
    "muthaiga":       (100_000, 500_000, 25_000_000, 300_000_000, 130_000),
    "westlands":      (40_000, 150_000, 5_000_000, 60_000_000, 55_000),
    "kilimani":       (35_000, 130_000, 4_500_000, 55_000_000, 48_000),
    "lavington":      (50_000, 200_000, 6_000_000, 80_000_000, 60_000),
    "kileleshwa":     (35_000, 120_000, 5_000_000, 50_000_000, 45_000),
    "parklands":      (30_000, 100_000, 4_000_000, 40_000_000, 40_000),
    "upper hill":     (50_000, 200_000, 8_000_000, 80_000_000, 65_000),
    "nairobi":        (15_000, 120_000, 2_000_000, 50_000_000, 30_000),
    "ruaka":          (15_000, 50_000, 1_800_000, 12_000_000, 14_000),
    "rongai":         (10_000, 35_000, 1_200_000, 8_000_000, 10_000),
    "kitengela":      (8_000,  30_000, 800_000,   6_000_000, 8_000),
    "athi river":     (8_000,  25_000, 700_000,   5_000_000, 7_000),
    "ngong":          (10_000, 35_000, 900_000,   6_000_000, 9_000),
    "thika":          (8_000,  30_000, 600_000,   5_000_000, 7_000),
    "kiambu":         (10_000, 40_000, 1_000_000, 8_000_000, 10_000),
    "limuru":         (8_000,  30_000, 800_000,   5_000_000, 7_500),
    "mombasa":        (15_000, 100_000, 2_000_000, 40_000_000, 20_000),
    "kisumu":         (8_000,  40_000, 500_000,   8_000_000, 8_000),
    "nakuru":         (7_000,  35_000, 400_000,   6_000_000, 7_000),
    "eldoret":        (6_000,  30_000, 350_000,   5_000_000, 6_000),
    "default":        (8_000,  80_000, 500_000,   20_000_000, 12_000),
}

FRAUD_KEYWORD_WEIGHTS = {
    # High risk keywords
    "urgent": 15, "act fast": 20, "limited time": 18, "only one left": 20,
    "direct from owner": 10, "no agent": 8, "cash only": 25, "wire transfer": 30,
    "overseas owner": 35, "travelling abroad": 40, "send money": 40,
    "western union": 45, "mpesa now": 12, "pay deposit first": 20,
    "no viewing": 30, "trust me": 20, "guaranteed": 10,
    # Slightly suspicious
    "below market": 8, "motivated seller": 5, "must sell": 5,
}

REQUIRED_DOCUMENTS = {
    "sale": ["title_deed", "sale_agreement", "kra_pin", "national_id", "land_search", "rates_clearance"],
    "rent": ["lease_agreement", "national_id"],
    "lease": ["lease_agreement", "kra_pin", "national_id"],
}

KENYA_CITIES_LIST = [
    "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
    "kitengela", "rongai", "karen", "westlands", "kiambu", "machakos",
    "meru", "nyeri", "ruiru", "ngong", "athi river", "limuru", "kikuyu",
    "kahawa", "ruaka", "kileleshwa", "kilimani", "lavington", "runda",
    "muthaiga", "parklands", "upper hill",
]

PROPERTY_TYPE_KEYWORDS = {
    "residential": ["bedroom", "apartment", "flat", "house", "bungalow", "maisonette", "studio", "br", "bed"],
    "commercial": ["office", "shop", "retail", "warehouse", "commercial", "business", "plaza"],
    "land": ["land", "plot", "acre", "hectare", "parcel"],
    "agricultural": ["farm", "agricultural", "ranch", "crop"],
    "student_housing": ["student", "hostel", "bedsitter", "bedsit"],
    "short_stay": ["airbnb", "short stay", "holiday", "vacation", "nightly"],
}

LISTING_TYPE_KEYWORDS = {
    "rent": ["rent", "rental", "let", "lease", "monthly", "per month", "/month", "kes/mo"],
    "sale": ["sale", "sell", "buy", "purchase", "for sale", "own", "buying"],
    "lease": ["lease", "long lease", "commercial lease"],
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    fraud_risk_score: float
    trust_score: float
    price_reasonableness: str            # under | fair | over
    ownership_confidence: str            # low | medium | high
    ai_recommendation: str               # approve | review | reject
    document_flags: list[str]
    positive_signals: list[str]
    market_insights: str
    ai_summary: str
    price_analysis: dict
    action_items: list[str]


@dataclass
class SearchResult:
    city: Optional[str]
    county: Optional[str]
    property_type: Optional[str]
    listing_type: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    keywords: str
    interpretation: str


@dataclass
class ValuationResult:
    estimated_value_kes: int
    value_range_low: int
    value_range_high: int
    rental_estimate_monthly: Optional[int]
    rental_yield_percent: Optional[float]
    price_per_sqft: Optional[float]
    market_sentiment: str
    confidence_level: str
    investment_score: int
    appreciation_forecast: dict
    key_value_drivers: list[str]
    risk_factors: list[str]
    valuation_summary: str


# ─────────────────────────────────────────────────────────────────────────────
# FRAUD DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

class FraudDetector:
    """
    Rule-based + heuristic fraud detection for Kenyan real estate.
    Scores 0-100. Higher = more fraudulent.
    """

    def score(
        self,
        title: str,
        description: str,
        price: float,
        city: str,
        listing_type: str,
        documents: list[dict],
        agent_verified: bool,
        agent_license: Optional[str],
    ) -> tuple[float, list[str], list[str]]:
        text = f"{title} {description}".lower()
        flags: list[str] = []
        positives: list[str] = []
        score = 0.0

        # 1. Keyword fraud signals
        for kw, weight in FRAUD_KEYWORD_WEIGHTS.items():
            if kw in text:
                score += weight
                flags.append(f"Suspicious language detected: '{kw}'")

        # 2. Price sanity check
        city_key = self._normalize_city(city)
        band = KENYA_PRICE_BANDS.get(city_key, KENYA_PRICE_BANDS["default"])
        if listing_type == "rent":
            min_p, max_p = band[0], band[1]
        else:
            min_p, max_p = band[2], band[3]

        if price < min_p * 0.3:
            score += 35
            flags.append(f"Price (KES {price:,.0f}) is suspiciously low for {city} — possible bait listing")
        elif price < min_p * 0.6:
            score += 15
            flags.append(f"Price below typical market range for {city}")
        elif price > max_p * 2.5:
            score += 5
            flags.append("Price significantly above typical market — verify value")

        # 3. Document checks
        required = REQUIRED_DOCUMENTS.get(listing_type, [])
        submitted_types = [d.get("type", "") for d in documents]
        missing = [doc for doc in required if doc not in submitted_types]

        if not documents:
            score += 30
            flags.append("No documents uploaded — HIGH RISK: verify ownership independently")
        elif len(missing) > 2:
            score += 20
            flags.append(f"Missing critical documents: {', '.join(missing[:3])}")
        elif len(missing) > 0:
            score += 10
            flags.append(f"Incomplete documents — missing: {', '.join(missing)}")
        else:
            positives.append("All required documents submitted")

        # 4. Agent verification
        if not agent_verified:
            score += 10
            flags.append("Seller/agent account not verified — request verification")
        else:
            positives.append("Verified seller/agent account")

        if not agent_license:
            score += 8
            flags.append("No EARB agent license number provided")
        else:
            positives.append(f"Agent license number provided: {agent_license}")

        # 5. Title length / quality
        if len(title) < 10:
            score += 8
            flags.append("Listing title too vague — professional listings are more descriptive")
        if not description or len(description) < 50:
            score += 10
            flags.append("Very short or missing description — legitimate listings include full details")
        elif len(description) > 200:
            positives.append("Detailed property description provided")

        # 6. Cap at 100
        score = min(100.0, score)

        return round(score, 1), flags, positives

    def _normalize_city(self, city: str) -> str:
        c = city.lower().strip()
        for key in KENYA_PRICE_BANDS:
            if key in c or c in key:
                return key
        return "default"


# ─────────────────────────────────────────────────────────────────────────────
# TRUST ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class TrustEngine:
    """
    Computes a Trust Score 0-100 from multiple signals.
    Inverse of fraud, plus positive signals.
    """

    def compute(
        self,
        fraud_score: float,
        doc_count: int,
        has_required_docs: bool,
        agent_verified: bool,
        agent_licensed: bool,
        price_reasonable: bool,
        description_quality: float,   # 0-1
        listing_age_days: int = 0,
    ) -> tuple[float, str, str]:
        """Returns (trust_score, ownership_confidence, recommendation)"""

        # Base: invert fraud score
        base = 100 - fraud_score

        # Bonuses
        bonus = 0.0
        if has_required_docs:
            bonus += 10
        if doc_count >= 3:
            bonus += 5
        if agent_verified:
            bonus += 8
        if agent_licensed:
            bonus += 7
        if price_reasonable:
            bonus += 5
        if description_quality > 0.6:
            bonus += 5
        if listing_age_days > 30:
            bonus += 3  # established listing

        trust = min(100.0, base + bonus)

        # Ownership confidence
        if trust >= 80 and has_required_docs and agent_verified:
            ownership_confidence = "high"
        elif trust >= 55:
            ownership_confidence = "medium"
        else:
            ownership_confidence = "low"

        # Recommendation
        if trust >= 75 and fraud_score < 25:
            recommendation = "approve"
        elif trust >= 50 and fraud_score < 50:
            recommendation = "review"
        else:
            recommendation = "reject"

        return round(trust, 1), ownership_confidence, recommendation


# ─────────────────────────────────────────────────────────────────────────────
# PRICE ANALYSER
# ─────────────────────────────────────────────────────────────────────────────

class PriceAnalyser:
    """Checks if a price is under/fair/over for the city and type."""

    def analyse(
        self,
        price: float,
        city: str,
        listing_type: str,
        bedrooms: Optional[int],
        size_sqft: Optional[float],
    ) -> tuple[str, dict]:
        city_key = self._normalize_city(city)
        band = KENYA_PRICE_BANDS.get(city_key, KENYA_PRICE_BANDS["default"])

        if listing_type == "rent":
            low, high = band[0], band[1]
            # Bedroom adjustments
            if bedrooms:
                multiplier = 1 + (bedrooms - 2) * 0.25
                low = int(low * max(0.5, multiplier))
                high = int(high * max(0.5, multiplier))
        else:
            low, high = band[2], band[3]
            if bedrooms:
                multiplier = 1 + (bedrooms - 3) * 0.15
                low = int(low * max(0.4, multiplier))
                high = int(high * max(0.4, multiplier))

        mid = (low + high) / 2
        tolerance = 0.2  # 20% tolerance

        if price < low * (1 - tolerance):
            reasonableness = "under"
        elif price > high * (1 + tolerance):
            reasonableness = "over"
        else:
            reasonableness = "fair"

        return reasonableness, {
            "submitted_price": price,
            "estimated_market_low": low,
            "estimated_market_high": high,
            "currency": "KES",
        }

    def _normalize_city(self, city: str) -> str:
        c = city.lower().strip()
        for key in KENYA_PRICE_BANDS:
            if key in c or c in key:
                return key
        return "default"


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH PARSER
# ─────────────────────────────────────────────────────────────────────────────

class SearchParser:
    """
    Parses natural language property search queries into structured filters.
    No ML needed — pure pattern matching on Kenyan real estate language.
    """

    def parse(self, query: str) -> SearchResult:
        q = query.lower().strip()

        city = self._extract_city(q)
        listing_type = self._extract_listing_type(q)
        property_type = self._extract_property_type(q)
        bedrooms = self._extract_bedrooms(q)
        bathrooms = self._extract_bathrooms(q)
        min_price, max_price = self._extract_price(q, listing_type)
        keywords = self._clean_keywords(q)
        interpretation = self._build_interpretation(
            city, listing_type, property_type, bedrooms, min_price, max_price
        )

        return SearchResult(
            city=city,
            county=self._city_to_county(city) if city else None,
            property_type=property_type,
            listing_type=listing_type,
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            keywords=keywords,
            interpretation=interpretation,
        )

    def _extract_city(self, q: str) -> Optional[str]:
        for city in sorted(KENYA_CITIES_LIST, key=len, reverse=True):
            if city in q:
                return city.title()
        return None

    def _extract_listing_type(self, q: str) -> Optional[str]:
        for lt, keywords in LISTING_TYPE_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                return lt
        return None

    def _extract_property_type(self, q: str) -> Optional[str]:
        for pt, keywords in PROPERTY_TYPE_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                return pt
        return None

    def _extract_bedrooms(self, q: str) -> Optional[int]:
        patterns = [
            r'(\d+)\s*(?:bed|bedroom|br|bdr)',
            r'(\d+)\s*(?:bhk)',
            r'(?:studio|bedsitter|bedsit)',
        ]
        for pattern in patterns:
            m = re.search(pattern, q)
            if m:
                if "studio" in pattern or "bedsit" in pattern:
                    return 1
                return int(m.group(1))
        return None

    def _extract_bathrooms(self, q: str) -> Optional[int]:
        m = re.search(r'(\d+)\s*(?:bath|bathroom)', q)
        return int(m.group(1)) if m else None

    def _extract_price(self, q: str, listing_type: Optional[str]) -> tuple[Optional[float], Optional[float]]:
        min_p: Optional[float] = None
        max_p: Optional[float] = None

        # Normalize shorthand: 40k → 40000, 1m → 1000000, 1.5m → 1500000
        q_norm = re.sub(r'(\d+(?:\.\d+)?)\s*k', lambda m: str(int(float(m.group(1)) * 1_000)), q)
        q_norm = re.sub(r'(\d+(?:\.\d+)?)\s*m(?:illion)?', lambda m: str(int(float(m.group(1)) * 1_000_000)), q_norm)

        # "under X" / "below X" / "max X"
        m = re.search(r'(?:under|below|max|maximum|up to|less than|at most)\s*(?:kes\s*)?(\d[\d,]*)', q_norm)
        if m:
            max_p = float(m.group(1).replace(',', ''))

        # "above X" / "over X" / "from X" / "min X"
        m = re.search(r'(?:above|over|from|min|minimum|at least|more than)\s*(?:kes\s*)?(\d[\d,]*)', q_norm)
        if m:
            min_p = float(m.group(1).replace(',', ''))

        # "X to Y" range
        m = re.search(r'(?:kes\s*)?(\d[\d,]*)\s*(?:to|-)\s*(?:kes\s*)?(\d[\d,]*)', q_norm)
        if m:
            a, b = float(m.group(1).replace(',', '')), float(m.group(2).replace(',', ''))
            min_p, max_p = min(a, b), max(a, b)

        return min_p, max_p

    def _clean_keywords(self, q: str) -> str:
        stop = set(KENYA_CITIES_LIST + [
            "for", "rent", "sale", "buy", "looking", "find", "want",
            "need", "a", "an", "the", "in", "at", "with", "under", "above",
            "kes", "bedroom", "bed", "bath", "to", "i", "me", "and", "or",
        ])
        words = [w for w in q.split() if w not in stop and len(w) > 2]
        return " ".join(words[:10])

    def _city_to_county(self, city: Optional[str]) -> Optional[str]:
        mapping = {
            "Nairobi": "Nairobi", "Karen": "Nairobi", "Westlands": "Nairobi",
            "Kilimani": "Nairobi", "Lavington": "Nairobi", "Runda": "Nairobi",
            "Muthaiga": "Nairobi", "Kileleshwa": "Nairobi", "Ruaka": "Kiambu",
            "Rongai": "Kajiado", "Kitengela": "Kajiado", "Ngong": "Kajiado",
            "Thika": "Kiambu", "Kiambu": "Kiambu", "Limuru": "Kiambu",
            "Ruiru": "Kiambu", "Kikuyu": "Kiambu", "Athi River": "Machakos",
            "Mombasa": "Mombasa", "Kisumu": "Kisumu", "Nakuru": "Nakuru",
            "Eldoret": "Uasin Gishu",
        }
        return mapping.get(city or "", None)

    def _build_interpretation(self, city, listing_type, property_type, bedrooms, min_p, max_p) -> str:
        parts = ["Searching for"]
        if bedrooms:
            parts.append(f"{bedrooms}-bedroom")
        if property_type:
            parts.append(property_type.replace("_", " "))
        else:
            parts.append("property")
        if listing_type:
            parts.append(f"for {listing_type}")
        if city:
            parts.append(f"in {city}")
        if min_p and max_p:
            parts.append(f"priced KES {min_p:,.0f} – {max_p:,.0f}")
        elif max_p:
            parts.append(f"under KES {max_p:,.0f}")
        elif min_p:
            parts.append(f"above KES {min_p:,.0f}")
        return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT ANALYSER
# ─────────────────────────────────────────────────────────────────────────────

class DocumentAnalyser:
    """Flags issues with submitted documents based on type and listing type."""

    DOCUMENT_DESCRIPTIONS = {
        "title_deed": "Title Deed",
        "sale_agreement": "Sale Agreement",
        "lease_agreement": "Lease Agreement",
        "national_id": "National ID / Passport",
        "kra_pin": "KRA PIN Certificate",
        "land_search": "Land Search Certificate",
        "rates_clearance": "Rates Clearance Certificate",
        "other": "Supporting Document",
    }

    def analyse(self, documents: list[dict], listing_type: str) -> tuple[list[str], list[str]]:
        flags: list[str] = []
        positives: list[str] = []
        submitted = {d.get("type", "") for d in documents}
        required = set(REQUIRED_DOCUMENTS.get(listing_type, []))

        missing = required - submitted
        present = required & submitted

        for doc_type in missing:
            label = self.DOCUMENT_DESCRIPTIONS.get(doc_type, doc_type)
            if doc_type == "title_deed":
                flags.append(f"CRITICAL: No Title Deed uploaded — cannot confirm ownership without it")
            elif doc_type == "land_search":
                flags.append(f"Missing Land Search Certificate — required to confirm no encumbrances")
            elif doc_type == "rates_clearance":
                flags.append(f"Missing Rates Clearance Certificate — seller must prove no outstanding land rates")
            else:
                flags.append(f"Missing: {label}")

        for doc_type in present:
            label = self.DOCUMENT_DESCRIPTIONS.get(doc_type, doc_type)
            positives.append(f"{label} submitted")

        if not documents:
            flags.append("No documents submitted — property cannot be verified without documentation")

        return flags, positives


# ─────────────────────────────────────────────────────────────────────────────
# VALUATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ValuationEngine:
    """Estimates property value based on city, size, type, and market data."""

    def valuate(
        self,
        city: str,
        listing_type: str,
        property_type: str,
        bedrooms: Optional[int],
        size_sqft: Optional[float],
        year_built: Optional[int],
        amenities: list[str],
        submitted_price: float,
    ) -> ValuationResult:

        city_key = self._normalize_city(city)
        band = KENYA_PRICE_BANDS.get(city_key, KENYA_PRICE_BANDS["default"])
        avg_sqft_price = band[4]

        # Base value from sqft
        if size_sqft and size_sqft > 0:
            base_value = size_sqft * avg_sqft_price
        elif bedrooms:
            # Estimate sqft from bedrooms
            est_sqft = 400 + (bedrooms * 350)
            base_value = est_sqft * avg_sqft_price
        else:
            base_value = (band[2] + band[3]) / 2 if listing_type == "sale" else (band[0] + band[1]) / 2

        # Age depreciation
        if year_built:
            age = max(0, datetime.now().year - year_built)
            depreciation = min(0.35, age * 0.008)
            base_value *= (1 - depreciation)

        # Amenity bonuses
        amenity_bonus = 0.0
        premium_amenities = {"Swimming Pool", "Gym", "Lift/Elevator", "Backup Generator", "Solar Power"}
        matched = set(amenities) & premium_amenities
        amenity_bonus = len(matched) * 0.04
        base_value *= (1 + amenity_bonus)

        # Bedroom premium
        if bedrooms and bedrooms >= 4:
            base_value *= 1.15

        low = int(base_value * 0.88)
        high = int(base_value * 1.15)
        estimated = int(base_value)

        # Rental estimate
        rental_monthly = None
        rental_yield = None
        if listing_type == "sale":
            # Estimate monthly rental at 6% annual yield
            rental_monthly = int(estimated * 0.06 / 12)
            rental_yield = round((rental_monthly * 12 / estimated) * 100, 1)
        elif listing_type == "rent":
            rental_monthly = int(submitted_price)

        # Investment score
        inv_score = self._investment_score(city_key, property_type, rental_yield, estimated)

        # Price per sqft
        price_per_sqft = round(estimated / size_sqft, 0) if size_sqft else avg_sqft_price

        # Market sentiment
        sentiment = self._market_sentiment(city_key)

        # Confidence
        confidence = "high" if size_sqft and bedrooms else "medium" if bedrooms else "low"

        # Drivers and risks
        drivers = self._value_drivers(city, property_type, amenities, bedrooms)
        risks = self._risk_factors(city_key, year_built, property_type)

        # Summary
        summary = self._build_summary(city, estimated, low, high, rental_yield, inv_score)

        return ValuationResult(
            estimated_value_kes=estimated,
            value_range_low=low,
            value_range_high=high,
            rental_estimate_monthly=rental_monthly,
            rental_yield_percent=rental_yield,
            price_per_sqft=float(price_per_sqft),
            market_sentiment=sentiment,
            confidence_level=confidence,
            investment_score=inv_score,
            appreciation_forecast={
                "1_year": "7-10%",
                "3_year": "20-32%",
                "5_year": "38-55%",
            },
            key_value_drivers=drivers,
            risk_factors=risks,
            valuation_summary=summary,
        )

    def _normalize_city(self, city: str) -> str:
        c = city.lower().strip()
        for key in KENYA_PRICE_BANDS:
            if key in c or c in key:
                return key
        return "default"

    def _investment_score(self, city_key: str, prop_type: str, rental_yield: Optional[float], value: int) -> int:
        score = 50
        # Prime areas score higher
        prime = {"karen", "runda", "muthaiga", "westlands", "kilimani", "lavington"}
        growth = {"ruaka", "kitengela", "rongai", "ngong", "thika", "kiambu"}
        if city_key in prime:
            score += 20
        elif city_key in growth:
            score += 15
        # Good rental yield
        if rental_yield and rental_yield >= 7:
            score += 15
        elif rental_yield and rental_yield >= 5:
            score += 8
        # Land is high value
        if prop_type == "land":
            score += 10
        return min(100, score)

    def _market_sentiment(self, city_key: str) -> str:
        hot = {"ruaka", "kitengela", "rongai", "westlands", "kilimani"}
        warm = {"nairobi", "kiambu", "ngong", "thika", "mombasa"}
        if city_key in hot:
            return "bullish"
        elif city_key in warm:
            return "neutral"
        return "neutral"

    def _value_drivers(self, city: str, prop_type: str, amenities: list, bedrooms: Optional[int]) -> list[str]:
        drivers = [f"Prime {city} location"]
        if bedrooms and bedrooms >= 3:
            drivers.append("Family-sized unit in high demand")
        if "Security" in amenities or "CCTV" in amenities:
            drivers.append("Enhanced security features")
        if "Fibre Internet" in amenities:
            drivers.append("Fibre internet — valued by professionals and expats")
        if prop_type == "land":
            drivers.append("Land appreciates faster than built property in Kenya")
        if len(drivers) < 3:
            drivers.append("Growing Kenyan middle class demand")
        return drivers[:4]

    def _risk_factors(self, city_key: str, year_built: Optional[int], prop_type: str) -> list[str]:
        risks = []
        if year_built and (datetime.now().year - year_built) > 20:
            risks.append("Older property — factor in renovation costs")
        if prop_type == "land":
            risks.append("Verify land is not riparian, road reserve, or public utility zone")
        if city_key in {"kitengela", "rongai", "athi river"}:
            risks.append("Satellite town — verify access road quality and utility connections")
        if not risks:
            risks.append("Standard market risk — diversify across property types")
        return risks[:3]

    def _build_summary(self, city, est, low, high, yield_pct, inv_score) -> str:
        return (
            f"Based on current {city} market data, this property is estimated at "
            f"KES {est:,.0f} (range KES {low:,.0f} – {high:,.0f}). "
            + (f"The estimated annual rental yield is {yield_pct}%, " if yield_pct else "")
            + f"giving it an investment score of {inv_score}/100. "
            f"Kenya's real estate market continues to show strong fundamentals driven by "
            f"urbanisation and growing middle-class demand."
        )


# ─────────────────────────────────────────────────────────────────────────────
# MARKET INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

class MarketIntelligence:
    """Returns market summary stats per city."""

    def get_insights(self, city: str, listing_type: str) -> dict:
        city_key = city.lower().strip()
        for key in KENYA_PRICE_BANDS:
            if key in city_key or city_key in key:
                city_key = key
                break
        else:
            city_key = "default"

        band = KENYA_PRICE_BANDS[city_key]
        hot_cities = {"ruaka", "kitengela", "rongai", "westlands", "kilimani"}
        status = "hot" if city_key in hot_cities else "warm"

        if listing_type == "rent":
            avg = (band[0] + band[1]) // 2
        else:
            avg = (band[2] + band[3]) // 2

        return {
            "market_status": status,
            "avg_price_kes": avg,
            "avg_price_per_sqft": band[4],
            "supply_demand": "high demand/low supply" if city_key in hot_cities else "balanced",
            "trend_summary": f"{city} continues to see strong demand driven by urbanisation and infrastructure investment.",
            "best_time_to_buy": "now" if city_key in hot_cities else "now",
            "investor_tip": f"Focus on areas near upcoming infrastructure in {city} for best capital gains.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# VESTRA AI — MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

class VestraAI:
    """
    The single AI object the rest of the application imports.
    Internally coordinates all engines.
    """

    def __init__(self):
        self._fraud = FraudDetector()
        self._trust = TrustEngine()
        self._price = PriceAnalyser()
        self._search = SearchParser()
        self._docs = DocumentAnalyser()
        self._valuation = ValuationEngine()
        self._market = MarketIntelligence()

    # ── Verification ──────────────────────────────────────────────────────────

    def verify_property(
        self,
        property_data: dict,
        documents: list[dict],
        agent_info: Optional[dict] = None,
    ) -> dict:
        """
        Full AI property verification.
        Returns a dict matching the VerificationResult schema.
        """
        title = property_data.get("title", "")
        description = property_data.get("description", "") or ""
        price = float(property_data.get("price", 0))
        city = property_data.get("city", "Nairobi")
        listing_type = property_data.get("listing_type", "sale")
        bedrooms = property_data.get("bedrooms")
        size_sqft = property_data.get("size_sqft")

        agent_verified = agent_info.get("is_verified", False) if agent_info else False
        agent_license = agent_info.get("license_number") if agent_info else None

        # Run fraud detection
        fraud_score, fraud_flags, positives = self._fraud.score(
            title=title,
            description=description,
            price=price,
            city=city,
            listing_type=listing_type,
            documents=documents,
            agent_verified=agent_verified,
            agent_license=agent_license,
        )

        # Run document analysis
        doc_flags, doc_positives = self._docs.analyse(documents, listing_type)
        all_flags = fraud_flags + [f for f in doc_flags if f not in fraud_flags]
        all_positives = positives + doc_positives

        # Required docs check
        required = set(REQUIRED_DOCUMENTS.get(listing_type, []))
        submitted_types = {d.get("type", "") for d in documents}
        has_required = required.issubset(submitted_types) if required else False

        # Price analysis
        price_reasonableness, price_analysis = self._price.analyse(
            price, city, listing_type, bedrooms, size_sqft
        )

        # Description quality score
        desc_quality = min(1.0, len(description) / 300)

        # Trust score
        trust_score, ownership_confidence, recommendation = self._trust.compute(
            fraud_score=fraud_score,
            doc_count=len(documents),
            has_required_docs=has_required,
            agent_verified=agent_verified,
            agent_licensed=bool(agent_license),
            price_reasonable=(price_reasonableness == "fair"),
            description_quality=desc_quality,
        )

        # Market insights
        market_insights = (
            f"{city} {listing_type} market is currently active. "
            f"Properties in this area typically list for "
            f"KES {price_analysis['estimated_market_low']:,.0f} – "
            f"KES {price_analysis['estimated_market_high']:,.0f}."
        )

        # Action items
        action_items = self._build_action_items(
            all_flags, recommendation, agent_verified, has_required
        )

        # Human-readable summary
        summary = self._build_summary(
            trust_score, fraud_score, recommendation, city,
            price_reasonableness, all_flags, ownership_confidence
        )

        return {
            "fraud_risk_score": fraud_score,
            "trust_score": trust_score,
            "price_reasonableness": price_reasonableness,
            "ownership_confidence": ownership_confidence,
            "ai_recommendation": recommendation,
            "document_flags": all_flags,
            "positive_signals": all_positives,
            "market_insights": market_insights,
            "ai_summary": summary,
            "price_analysis": price_analysis,
            "action_items": action_items,
        }

    # ── Search ────────────────────────────────────────────────────────────────

    def parse_search(self, query: str) -> dict:
        result = self._search.parse(query)
        return {
            "city": result.city,
            "county": result.county,
            "property_type": result.property_type,
            "listing_type": result.listing_type,
            "min_price": result.min_price,
            "max_price": result.max_price,
            "bedrooms": result.bedrooms,
            "bathrooms": result.bathrooms,
            "keywords": result.keywords,
            "interpretation": result.interpretation,
        }

    # ── Valuation ─────────────────────────────────────────────────────────────

    def valuate(self, property_data: dict) -> dict:
        result = self._valuation.valuate(
            city=property_data.get("city", "Nairobi"),
            listing_type=property_data.get("listing_type", "sale"),
            property_type=property_data.get("property_type", "residential"),
            bedrooms=property_data.get("bedrooms"),
            size_sqft=property_data.get("size_sqft"),
            year_built=property_data.get("year_built"),
            amenities=property_data.get("amenities", []),
            submitted_price=float(property_data.get("price", 0)),
        )
        return {
            "estimated_value_kes": result.estimated_value_kes,
            "value_range_low": result.value_range_low,
            "value_range_high": result.value_range_high,
            "rental_estimate_monthly": result.rental_estimate_monthly,
            "rental_yield_percent": result.rental_yield_percent,
            "price_per_sqft": result.price_per_sqft,
            "market_sentiment": result.market_sentiment,
            "confidence_level": result.confidence_level,
            "investment_score": result.investment_score,
            "appreciation_forecast": result.appreciation_forecast,
            "key_value_drivers": result.key_value_drivers,
            "risk_factors": result.risk_factors,
            "valuation_summary": result.valuation_summary,
        }

    # ── Market ────────────────────────────────────────────────────────────────

    def market_insights(self, city: str, listing_type: str = "sale") -> dict:
        return self._market.get_insights(city, listing_type)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_action_items(
        self,
        flags: list[str],
        recommendation: str,
        agent_verified: bool,
        has_required_docs: bool,
    ) -> list[str]:
        items = []
        if not has_required_docs:
            items.append("Request all missing documents from the seller before proceeding")
        if not agent_verified:
            items.append("Ask the agent or seller to complete Vestra identity verification")
        if recommendation == "reject":
            items.append("Do NOT proceed with this property — multiple high-risk signals detected")
        elif recommendation == "review":
            items.append("Proceed with caution — conduct independent due diligence")
            items.append("Visit the property in person and verify ownership at the Land Registry")
        else:
            items.append("Property cleared — proceed with normal conveyancing process")
        if any("title deed" in f.lower() for f in flags):
            items.append("Obtain an official Land Registry search to confirm ownership chain")
        return items[:5]

    def _build_summary(
        self,
        trust_score: float,
        fraud_score: float,
        recommendation: str,
        city: str,
        price_reasonableness: str,
        flags: list[str],
        ownership_confidence: str,
    ) -> str:
        risk_level = "LOW" if fraud_score < 25 else "MEDIUM" if fraud_score < 55 else "HIGH"
        rec_text = {
            "approve": "cleared for further consideration",
            "review": "flagged for manual review before proceeding",
            "reject": "flagged as HIGH RISK — do not transact without independent verification",
        }.get(recommendation, "under review")

        price_text = {
            "under": "priced below typical market range for this area (possible bait listing)",
            "fair": "priced within normal market range for this area",
            "over": "priced above typical market range — negotiate or verify premium features",
        }.get(price_reasonableness, "")

        flag_count = len([f for f in flags if "CRITICAL" in f or "Missing" in f])
        doc_text = (
            f" {flag_count} document issue(s) require attention."
            if flag_count > 0 else " Documentation appears adequate."
        )

        return (
            f"Vestra AI has assigned this property a Trust Score of {trust_score:.0f}/100 "
            f"with {risk_level} fraud risk ({fraud_score:.0f}/100). "
            f"The listing has been {rec_text}. "
            f"The price is {price_text}.{doc_text} "
            f"Ownership confidence is {ownership_confidence}."
        )


# ─── Singleton instance — import this everywhere ──────────────────────────────
vestra_ai = VestraAI()
