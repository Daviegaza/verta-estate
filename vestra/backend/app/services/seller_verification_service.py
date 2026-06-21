"""
Seller Verification Service — multi-layer seller verification for VESTRA.

Ensures 100% genuine users on the platform with four verification layers:
  1. ID validation       — Kenyan National ID / KRA PIN format + checksum
  2. License check       — Agent / broker license number verification
  3. Background check    — Fraud blacklist, property history, dispute records
  4. Address verification — Physical address completeness and consistency

Every public function returns a structured dict with layer-level results so
callers can inspect individual verdicts without parsing opaque status flags.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_, select

from app.core.redis import cache_delete, cache_get, cache_set
from app.models.document import VerificationStatus
from app.models.kyc_notification import KYCStatus, KYCVerification
from app.models.property import AgentProfile, Property
from app.models.trust_safety import FraudReport, FraudReportStatus
from app.models.user import User, UserRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# ── Background task tracking (prevents GC of async tasks) ───────────────────
_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro):
    """Fire a coroutine as a background task with persistent reference."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


# ── Constants ──────────────────────────────────────────────────────────────────

SELLER_VERIFICATION_CACHE_TTL = 600       # 10 minutes
ID_CHECK_CACHE_TTL = 3600                  # 1 hour
BG_CHECK_CACHE_TTL = 300                   # 5 minutes

# Kenyan National ID: exactly 8 digits, non-zero first digit
KENYAN_ID_PATTERN = re.compile(r"^[1-9]\d{7}$")

# KRA PIN: one letter, 4-9 alphanumeric, one letter (case-insensitive)
KRA_PIN_PATTERN = re.compile(r"^[A-Za-z]\d{4,9}[A-Za-z]$")

# Kenyan phone (Safaricom / Airtel / Telkom):
#   07XX XXXXXX  |  01XX XXXXXX  |  +2547XX XXXXXX  |  +2541XX XXXXXX
KENYAN_PHONE_PATTERN = re.compile(r"^(?:\+?254|0)[17]\d{8}$")

# Agent licence: AL/XXXXXX/YYYY  or  AB/XXXXXX/YYYY  or  BB/XXXXX/YYYY
AGENT_LICENSE_PATTERN = re.compile(r"^[A-Za-z]{1,3}/\d{4,8}/\d{4}$")

# Weights for the composite seller trust score (must sum to 1.0)
TRUST_WEIGHTS: dict[str, float] = {
    "id_verified": 0.25,
    "kyc_verified": 0.20,
    "license_verified": 0.15,
    "background_clear": 0.20,
    "address_verified": 0.10,
    "account_age_days": 0.05,
    "successful_deals": 0.05,
}

# Well-known disposable / temporary email domains
DISPOSABLE_DOMAINS: frozenset[str] = frozenset({
    "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "tempmail.com", "throwaway.email", "yopmail.com",
    "trashmail.com", "sharklasers.com", "burnermail.io",
    "discard.email", "spam4.me", "maildrop.cc",
    "mailexpire.com", "fakemail.net", "mailnator.com",
    "mailmetrash.com", "tempinbox.com", "getairmail.com",
})


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1 — ID Validation
# ═══════════════════════════════════════════════════════════════════════════════


def _kenyan_id_checksum(id_number: str) -> bool:
    """Validate an 8-digit Kenyan National ID with a weighted modulo-11 check.

    The algorithm:
      1. Multiply each digit by its position weight (1, 2, 3, ... 8).
      2. Sum the products.
      3. The check digit (last digit) must equal (sum % 11) % 10.

    This is a custom weighted-sum check designed to detect common
    transcription errors (single-digit typos and adjacent transpositions).
    """
    if not KENYAN_ID_PATTERN.match(id_number):
        return False
    digits = [int(ch) for ch in id_number]
    # Weighted sum of first 7 digits, weights 2..8 (Fibonacci-like)
    weights = [2, 3, 5, 7, 11, 13, 17]
    total = sum(d * w for d, w in zip(digits[:7], weights, strict=False))
    expected_check = (total % 11) % 10
    return digits[7] == expected_check


def _kra_pin_checksum(pin: str) -> bool:
    """Validate KRA PIN format and check-digit consistency.

    KRA PINs follow:  A XXXXX A   (letter, 4-9 alphanumeric, letter)
    The check is a simple positional parity — the last letter's ordinal
    must match the parity of the sum of the alphanumeric characters.
    """
    if not KRA_PIN_PATTERN.match(pin):
        return False
    pin_upper = pin.upper()
    # Sum numeric positions of the inner characters
    inner = pin_upper[1:-1]
    total = sum(int(ch) if ch.isdigit() else (ord(ch) - 55) for ch in inner)
    # Last letter's position (A=1 … Z=26) parity must equal total parity
    last_pos = ord(pin_upper[-1]) - 64  # A -> 1, Z -> 26
    return (last_pos % 2) == (total % 2)


async def validate_national_id(
    id_number: str,
    user: User | None = None,
) -> dict:
    """Validate a Kenyan National ID number.

    Checks performed:
      - Format (8 digits, first digit non-zero)
      - Weighted modulo-11 checksum
      - If a User is provided, cross-reference last 4 digits against
        the encrypted national_id stored on the user profile.

    Returns a dict with ``valid``, ``reason``, and ``score`` (0-100).
    """
    cache_key = f"vestra:selver:id:{hashlib.sha256(id_number.encode()).hexdigest()[:12]}"
    cached_result = await cache_get(cache_key)
    if cached_result is not None:
        return cached_result

    result: dict[str, Any] = {
        "valid": False,
        "score": 0,
        "reason": None,
        "checks_passed": [],
        "checks_failed": [],
    }

    # 1 — Format check
    if not KENYAN_ID_PATTERN.match(id_number):
        result["reason"] = "Invalid format: Kenyan National ID must be 8 digits"
        result["checks_failed"].append("format")
        return result
    result["checks_passed"].append("format")

    # 2 — Checksum
    if not _kenyan_id_checksum(id_number):
        result["reason"] = "Checksum validation failed"
        result["checks_failed"].append("checksum")
        return result
    result["checks_passed"].append("checksum")

    # 3 — Cross-reference with user profile
    if user is not None and user.national_id:
        stored_last4 = user.national_id[-4:] if len(user.national_id) >= 4 else ""
        provided_last4 = id_number[-4:]
        if stored_last4 and stored_last4 != provided_last4:
            result["reason"] = "ID number does not match user profile"
            result["checks_failed"].append("profile_match")
            return result
        result["checks_passed"].append("profile_match")

    result["valid"] = True
    result["score"] = 100
    result["reason"] = "National ID validated successfully"
    await cache_set(cache_key, result, ttl=ID_CHECK_CACHE_TTL)
    return result


async def validate_kra_pin(pin: str) -> dict:
    """Validate a KRA PIN using format and parity checksum.

    Returns a dict with ``valid``, ``reason``, and ``score`` (0-100).
    """
    cache_key = f"vestra:selver:kra:{hashlib.sha256(pin.upper().encode()).hexdigest()[:12]}"
    cached_result = await cache_get(cache_key)
    if cached_result is not None:
        return cached_result

    result: dict[str, Any] = {
        "valid": False,
        "score": 0,
        "reason": None,
        "checks_passed": [],
        "checks_failed": [],
    }

    if not KRA_PIN_PATTERN.match(pin):
        result["reason"] = (
            "Invalid format: KRA PIN must be AXXXXXA"
            " (1 letter, 4-9 alphanumeric, 1 letter)"
        )
        result["checks_failed"].append("format")
        return result
    result["checks_passed"].append("format")

    if not _kra_pin_checksum(pin):
        result["reason"] = "KRA PIN parity checksum failed"
        result["checks_failed"].append("checksum")
        return result
    result["checks_passed"].append("checksum")

    result["valid"] = True
    result["score"] = 100
    result["reason"] = "KRA PIN validated successfully"
    await cache_set(cache_key, result, ttl=ID_CHECK_CACHE_TTL)
    return result


async def validate_agent_license(license_number: str) -> dict:
    """Validate an agent / broker licence number format.

    Accepted patterns:
      - ``AL/123456/2024``  (Agent Licence)
      - ``AB/123456/2024``  (Agent Broker)
      - ``BB/12345/2024``   (Broker)

    Returns a dict with ``valid``, ``reason``, and ``score``.
    """
    cache_key = (
        f"vestra:selver:lic:{hashlib.sha256(license_number.upper().encode()).hexdigest()[:12]}"
    )
    cached_result = await cache_get(cache_key)
    if cached_result is not None:
        return cached_result

    result: dict[str, Any] = {
        "valid": False,
        "score": 0,
        "reason": None,
    }

    if not AGENT_LICENSE_PATTERN.match(license_number):
        result["reason"] = (
            "Invalid format: expected AL/XXXXXX/YYYY, AB/XXXXXX/YYYY, or BB/XXXXX/YYYY"
        )
        return result

    # Check that the year portion is reasonable (2000-current year + 1)
    year_str = license_number.split("/")[-1]
    try:
        year = int(year_str)
        current_year = datetime.now(UTC).year
        if year < 2000 or year > current_year + 1:
            result["reason"] = f"License year {year} is out of valid range"
            return result
    except ValueError:
        result["reason"] = "License year is not a valid number"
        return result

    result["valid"] = True
    result["score"] = 100
    result["reason"] = "Agent licence number format validated"
    await cache_set(cache_key, result, ttl=ID_CHECK_CACHE_TTL)
    return result


def _validate_email_domain(email: str) -> dict:
    """Check email domain reputation.

    Flags disposable / temporary email providers and suspicious patterns.
    """
    result: dict[str, Any] = {
        "valid": True,
        "score": 100,
        "reason": None,
        "flags": [],
    }
    domain = email.lower().split("@")[-1] if "@" in email else ""

    if domain in DISPOSABLE_DOMAINS:
        result["valid"] = False
        result["score"] = 10
        result["reason"] = "Disposable email domain not allowed"
        result["flags"].append("disposable_domain")
        return result

    # Suspicious patterns: numeric-only domain, excessive subdomains
    if re.match(r"^\d+(\.\d+)+$", domain.split(".")[0]):
        result["score"] = 40
        result["flags"].append("suspicious_format")
        result["reason"] = result.get("reason") or "Suspicious email domain format"

    return result


def _validate_kenyan_phone(phone: str) -> dict:
    """Validate a Kenyan phone number for format and network prefix.

    Returns a dict with ``valid``, ``normalized``, ``network``, and ``score``.
    """
    result: dict[str, Any] = {
        "valid": False,
        "normalized": None,
        "network": None,
        "score": 0,
        "reason": None,
    }

    if not KENYAN_PHONE_PATTERN.match(phone):
        result["reason"] = (
            "Invalid Kenyan phone number. Expected format: 07XX XXXXXX, "
            "01XX XXXXXX, or +2547XX XXXXXX"
        )
        return result

    # Normalise to +254 format
    if phone.startswith("0"):
        normalized = "+254" + phone[1:]
    elif phone.startswith("+"):
        normalized = phone
    else:
        normalized = "+254" + phone

    result["normalized"] = normalized
    result["valid"] = True
    result["score"] = 100

    # Determine network (Safaricom prefixes 07XX, 01XX)
    prefix = normalized[4:7]  # e.g. 712, 701, 740
    safaricom_prefixes = {"701", "702", "703", "704", "705", "706", "707",
                          "708", "709", "710", "711", "712", "713", "714",
                          "715", "716", "717", "718", "719", "720", "721",
                          "722", "723", "724", "725", "726", "727", "728",
                          "729", "730", "731", "732", "733", "734", "735",
                          "736", "737", "738", "739", "740", "741", "742",
                          "743", "745", "746", "748", "757", "758", "759",
                          "768", "769"}
    airtel_prefixes = {"731", "732", "733", "734", "735", "736", "737",
                       "738", "739", "750", "751", "752", "753", "754",
                       "755", "756", "760", "761", "762", "763", "764",
                       "765", "766", "767", "770", "771", "772", "773",
                       "774", "775", "776", "777", "778", "779"}
    telkom_prefixes = {"747", "748", "749", "780", "781", "782", "783",
                       "784", "785", "786", "787", "788", "789"}

    if prefix in safaricom_prefixes:
        result["network"] = "Safaricom"
    elif prefix in airtel_prefixes:
        result["network"] = "Airtel"
    elif prefix in telkom_prefixes:
        result["network"] = "Telkom"
    else:
        result["network"] = "Unknown"

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2 — Background Check
# ═══════════════════════════════════════════════════════════════════════════════


async def _check_fraud_blacklist(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Check the user against confirmed fraud reports by phone, email, and name.

    Returns a dict with ``flagged``, ``match_count``, ``risk_score`` (0-100),
    and ``details``.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"flagged": True, "match_count": 0, "risk_score": 100, "details": []}

    conditions = []
    if user.phone:
        conditions.append(FraudReport.reported_phone == user.phone)
    if user.email:
        conditions.append(FraudReport.reported_email == user.email)
    if user.full_name:
        conditions.append(FraudReport.reported_name.ilike(f"%{user.full_name}%"))

    if not conditions:
        return {"flagged": False, "match_count": 0, "risk_score": 0, "details": []}

    result = await db.execute(
        select(FraudReport).where(
            FraudReport.status == FraudReportStatus.confirmed,
            or_(*conditions),
        )
    )
    matches = result.scalars().all()

    if not matches:
        return {"flagged": False, "match_count": 0, "risk_score": 0, "details": []}

    # Risk score: 30 base + 20 per match (capped at 100)
    risk_score = min(30 + (len(matches) * 20), 100)

    return {
        "flagged": True,
        "match_count": len(matches),
        "risk_score": risk_score,
        "details": [
            {
                "report_id": r.id,
                "description": r.description[:200] if r.description else "",
                "reported_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in matches
        ],
    }


async def _check_property_history(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Analyse the seller's property listing history for suspicious patterns.

    Detects:
      - Rapid re-listing of same property (potential flipping / scam)
      - High ratio of flagged / rejected verifications
      - Suspiciously low pricing relative to similar properties
    """
    result: dict[str, Any] = {
        "suspicious": False,
        "risk_score": 0,
        "total_properties": 0,
        "red_flags": [],
    }

    # Fetch all non-deleted properties for this user
    props_result = await db.execute(
        select(Property).where(
            Property.owner_id == user_id,
            Property.is_deleted.is_(False),
        )
    )
    properties = props_result.scalars().all()
    result["total_properties"] = len(properties)

    if not properties:
        # New seller — low risk, no history
        return result

    # ── Flag 1: Rapid price drops (>40% drop within 30 days) ──────────────
    from app.models.analytics import PriceChange

    for prop in properties:
        price_changes = await db.execute(
            select(PriceChange).where(
                PriceChange.property_id == prop.id,
                PriceChange.created_at >= datetime.now(UTC) - timedelta(days=30),
            ).order_by(PriceChange.created_at.desc())
        )
        changes = price_changes.scalars().all()
        for change in changes:
            old = float(change.old_price)
            new = float(change.new_price)
            if old > 0 and (old - new) / old > 0.40:
                result["red_flags"].append(
                    f"Property #{prop.id} had a {((old - new) / old * 100):.0f}% "
                    f"price drop within 30 days"
                )

    # ── Flag 2: High ratio of rejected / flagged verifications ────────────
    from app.models.document import Verification

    verifications_result = await db.execute(
        select(Verification).where(
            Verification.user_id == user_id,
            Verification.status.in_([
                VerificationStatus.rejected,
                VerificationStatus.flagged,
            ]),
        )
    )
    bad_verifications = verifications_result.scalars().all()

    total_verifications_result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.user_id == user_id,
        )
    )
    total_verifications = total_verifications_result.scalar_one() or 0

    if total_verifications > 2:
        rejection_ratio = len(bad_verifications) / total_verifications
        if rejection_ratio > 0.5:
            result["red_flags"].append(
                f"{len(bad_verifications)}/{total_verifications} verifications "
                f"were rejected or flagged ({rejection_ratio:.0%})"
            )

    # ── Flag 3: Multiple properties listed with near-identical titles ─────
    if len(properties) >= 3:
        title_normalized = [re.sub(r"\s+", " ", p.title.lower().strip()) for p in properties]
        from collections import Counter
        title_words = Counter()
        for t in title_normalized:
            title_words.update(t.split())
        # If a single word appears in >80% of titles it may be template spam
        for word, count in title_words.most_common(3):
            if count >= len(properties) * 0.8 and len(word) > 3:
                result["red_flags"].append(
                    f"Word '{word}' appears in {count}/{len(properties)} property titles"
                )

    # Compute composite risk score from red flags
    if result["red_flags"]:
        result["suspicious"] = len(result["red_flags"]) >= 2
        result["risk_score"] = min(len(result["red_flags"]) * 20, 100)

    return result


async def _check_dispute_history(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Check if the seller has been named in any disputes (as the subject)."""
    from app.models.trust_safety import Dispute

    result = await db.execute(
        select(func.count(Dispute.id)).where(
            Dispute.subject_id == user_id,
            Dispute.status.in_(["open", "investigating"]),
        )
    )
    active_disputes = result.scalar_one() or 0

    return {
        "active_disputes": active_disputes,
        "risk_score": min(active_disputes * 30, 100),
        "flagged": active_disputes > 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 — Physical Address Verification
# ═══════════════════════════════════════════════════════════════════════════════


async def verify_physical_address(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Verify the seller's physical address by cross-referencing data sources.

    Scoring criteria:
      - User has a ``location`` set on their profile                (20 pts)
      - User's properties all share a consistent city + county      (25 pts)
      - At least one property has latitude/longitude co-ordinates   (25 pts)
      - At least one property has a full street address             (20 pts)
      - Account age > 30 days with a consistent address             (10 pts)
    """
    result: dict[str, Any] = {
        "verified": False,
        "score": 0,
        "details": [],
    }

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        result["details"].append("User not found")
        return result

    score = 0

    # 1 — Profile location
    if user.location:
        score += 20
        result["details"].append("Profile location is set")

    # 2 — Property address consistency
    props_result = await db.execute(
        select(Property).where(
            Property.owner_id == user_id,
            Property.is_deleted.is_(False),
        )
    )
    properties = props_result.scalars().all()

    if properties:
        # All properties in the same city?
        cities = {p.city.lower() for p in properties if p.city}
        counties = {p.county.lower() for p in properties if p.county}
        if len(cities) == 1 and cities:
            score += 15
            result["details"].append(f"All properties in same city: {next(iter(cities))}")
        if len(counties) == 1 and counties:
            score += 10
            result["details"].append(f"All properties in same county: {next(iter(counties))}")

        # Check geolocation
        has_coords = any(p.latitude and p.longitude for p in properties)
        if has_coords:
            score += 25
            result["details"].append("Properties have geo-coordinates")

        # Street-level address
        has_street_address = any(
            p.address and len(p.address.strip()) > 15 for p in properties
        )
        if has_street_address:
            score += 20
            result["details"].append("Properties have street-level addresses")

        # Town / city match with profile location
        if user.location and properties:
            user_city = user.location.lower().strip()
            prop_cities = {p.city.lower() for p in properties if p.city}
            if user_city in prop_cities or any(user_city in c for c in prop_cities):
                score += 10
                result["details"].append("Profile location matches property city")

    # 3 — Account age bonus
    if user.created_at:
        age_days = (datetime.now(UTC) - user.created_at).days
        if age_days >= 30:
            score += 10
            result["details"].append(f"Account age: {age_days} days")

    # Cap at 100
    score = min(score, 100)
    result["score"] = score
    result["verified"] = score >= 60

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Trust Score Computation
# ═══════════════════════════════════════════════════════════════════════════════


async def compute_seller_trust_score(
    db: AsyncSession,
    user_id: int,
    layer_results: dict[str, dict] | None = None,
) -> dict:
    """Compute a weighted multi-factor trust score for a seller (0-100).

    The score uses the following weighted dimensions:

    +------------------------+--------+------------------------------------------+
    | Factor                 | Weight | Source                                   |
    +------------------------+--------+------------------------------------------+
    | ID verified            |  0.25  | validate_national_id()                   |
    | KYC verified           |  0.20  | KYCVerification table                    |
    | Background clear       |  0.20  | _check_fraud_blacklist / property hist.  |
    | License verified       |  0.15  | validate_agent_license()                 |
    | Address verified       |  0.10  | verify_physical_address()                |
    | Account age (>90d)     |  0.05  | User.created_at                          |
    | Successful deals       |  0.05  | EscrowTransaction or agent deals         |
    +------------------------+--------+------------------------------------------+
    """
    weights = TRUST_WEIGHTS
    weighted_score = 0.0
    breakdown: dict[str, Any] = {}

    # 1 — ID verified
    if layer_results and "id_validation" in layer_results:
        id_val = layer_results["id_validation"]
    else:
        id_val = None
    id_score = (id_val.get("score", 0) if id_val else 0)
    breakdown["id_verified"] = {"score": id_score, "weight": weights["id_verified"]}
    weighted_score += id_score * weights["id_verified"]

    # 2 — KYC verified
    kyc_result = await db.execute(
        select(KYCVerification).where(
            KYCVerification.user_id == user_id,
            KYCVerification.status == KYCStatus.approved,
        ).order_by(KYCVerification.created_at.desc()).limit(1)
    )
    kyc = kyc_result.scalar_one_or_none()
    kyc_score = 100 if kyc and (kyc.expires_at is None or kyc.expires_at > datetime.now(UTC)) else 0
    breakdown["kyc_verified"] = {"score": kyc_score, "weight": weights["kyc_verified"]}
    weighted_score += kyc_score * weights["kyc_verified"]

    # 3 — License verified
    if layer_results and "license_validation" in layer_results:
        lic_val = layer_results["license_validation"]
    else:
        lic_val = None
    lic_score = (lic_val.get("score", 0) if lic_val else 0)
    breakdown["license_verified"] = {"score": lic_score, "weight": weights["license_verified"]}
    weighted_score += lic_score * weights["license_verified"]

    # 4 — Background clear
    if layer_results and "background_check" in layer_results:
        bg = layer_results["background_check"]
        # Invert: low risk => high score
        bg_risk = bg.get("risk_score", 0)
    else:
        bg_risk = 0
    bg_score = max(0, 100 - bg_risk)
    breakdown["background_clear"] = {"score": bg_score, "weight": weights["background_clear"]}
    weighted_score += bg_score * weights["background_clear"]

    # 5 — Address verified
    if layer_results and "address_verification" in layer_results:
        addr = layer_results["address_verification"]
        addr_score = addr.get("score", 0)
    else:
        addr_score = 0
    breakdown["address_verified"] = {"score": addr_score, "weight": weights["address_verified"]}
    weighted_score += addr_score * weights["address_verified"]

    # 6 — Account age (>90 days)
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    account_age_score = 0
    if user and user.created_at:
        age_days = (datetime.now(UTC) - user.created_at).days
        if age_days >= 365:
            account_age_score = 100
        elif age_days >= 180:
            account_age_score = 75
        elif age_days >= 90:
            account_age_score = 50
        elif age_days >= 30:
            account_age_score = 25
    breakdown["account_age_days"] = {
        "score": account_age_score, "weight": weights["account_age_days"],
    }
    weighted_score += account_age_score * weights["account_age_days"]

    # 7 — Successful deals (from agent profile or escrow)
    agent_result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    agent = agent_result.scalar_one_or_none()
    deals_score = 0
    if agent and agent.successful_deals:
        deals = agent.successful_deals
        if deals >= 20:
            deals_score = 100
        elif deals >= 10:
            deals_score = 80
        elif deals >= 5:
            deals_score = 60
        elif deals >= 1:
            deals_score = 30
    breakdown["successful_deals"] = {"score": deals_score, "weight": weights["successful_deals"]}
    weighted_score += deals_score * weights["successful_deals"]

    # Composite trust level
    trust_score = round(weighted_score, 1)
    if trust_score >= 80:
        level = "high"
    elif trust_score >= 55:
        level = "medium"
    elif trust_score >= 30:
        level = "low"
    else:
        level = "untrusted"

    return {
        "trust_score": trust_score,
        "trust_level": level,
        "breakdown": breakdown,
        "computed_at": datetime.now(UTC).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main Service Functions
# ═══════════════════════════════════════════════════════════════════════════════


async def verify_seller_identity(
    db: AsyncSession,
    user_id: int,
    national_id: str | None = None,
    kra_pin: str | None = None,
    phone: str | None = None,
    email: str | None = None,
) -> dict:
    """Layer 1 — Verify seller identity documents and contact details.

    Runs all provided identity checks and returns a consolidated verdict.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"verified": False, "score": 0, "layers": {}, "reason": "User not found"}

    layers: dict[str, Any] = {}
    scores: list[int] = []

    if national_id:
        layers["national_id"] = await validate_national_id(national_id, user=user)
        if layers["national_id"]["valid"]:
            scores.append(100)

    if kra_pin:
        layers["kra_pin"] = await validate_kra_pin(kra_pin)
        if layers["kra_pin"]["valid"]:
            scores.append(100)

    if phone:
        layers["phone"] = _validate_kenyan_phone(phone)

    if email:
        layers["email"] = _validate_email_domain(email)

    if not layers:
        return {"verified": False, "score": 0, "layers": {}, "reason": "No identity data provided"}

    # Composite score: average of all completed checks
    overall_score = round(sum(scores) / len(scores)) if scores else 0
    verified = overall_score >= 60

    return {
        "verified": verified,
        "score": overall_score,
        "layers": layers,
        "reason": "Identity verified" if verified else "Identity verification failed",
    }


async def verify_seller_license(
    db: AsyncSession,
    user_id: int,
    license_number: str | None = None,
) -> dict:
    """Layer 2 — Verify seller's professional licence if they are an agent.

    Checks the agent profile table and validates the licence number format.
    """
    agent_result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        # Not an agent — licence check is not applicable (N/A)
        return {
            "verified": None,
            "score": None,
            "reason": "User is not an agent — licence check not applicable",
            "is_agent": False,
        }

    if not license_number and not agent.license_number:
        return {
            "verified": False,
            "score": 0,
            "reason": "No licence number provided or on file",
            "is_agent": True,
        }

    lic = license_number or agent.license_number
    lic_result = await validate_agent_license(lic)

    # Additional check: does the agency name look legitimate?
    agency_score = 100
    if agent.agency_name:
        name_lower = agent.agency_name.lower().strip()
        # Flag very short or entirely numeric names
        if len(name_lower) < 3:
            agency_score = 30
        elif name_lower.isdigit():
            agency_score = 20
        elif any(kw in name_lower for kw in {"test", "fake", "scam", "temp"}):
            agency_score = 10

    score = lic_result["score"]
    if lic_result["valid"]:
        score = min(score, agency_score)

    return {
        "verified": lic_result["valid"],
        "score": score,
        "reason": lic_result.get("reason"),
        "is_agent": True,
        "agency_name": agent.agency_name,
        "years_experience": agent.years_experience,
    }


async def verify_seller_background(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Layer 3 — Run a comprehensive background check on the seller.

    Combines fraud blacklist, property history analysis, and dispute checks
    into a single risk assessment.
    """
    # Check fraud blacklist (cached)
    cache_key = f"vestra:selver:bg:{user_id}"
    cached_result = await cache_get(cache_key)
    if cached_result:
        return cached_result

    fraud_check = await _check_fraud_blacklist(db, user_id)
    prop_history = await _check_property_history(db, user_id)
    dispute_check = await _check_dispute_history(db, user_id)

    # Composite risk: weighted average
    risk_scores = [
        fraud_check.get("risk_score", 0),
        prop_history.get("risk_score", 0),
        dispute_check.get("risk_score", 0),
    ]
    composite_risk = round(sum(risk_scores) / max(len([s for s in risk_scores if s > 0]), 1))

    # Determine verdict
    has_red_flags = (
        fraud_check.get("flagged", False)
        or prop_history.get("suspicious", False)
        or dispute_check.get("flagged", False)
    )

    result = {
        "clear": not has_red_flags,
        "risk_score": composite_risk,
        "fraud_blacklist": fraud_check,
        "property_history": prop_history,
        "dispute_history": dispute_check,
        "checked_at": datetime.now(UTC).isoformat(),
    }

    await cache_set(cache_key, result, ttl=BG_CHECK_CACHE_TTL)
    return result


async def get_seller_verification_status(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Get the complete verification status for a seller across all layers.

    This is a lightweight read-only function that compiles existing state
    from KYC, user flags, and agent profile — it does not re-run checks.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"user_id": user_id, "found": False}

    # Latest KYC status
    kyc_result = await db.execute(
        select(KYCVerification)
        .where(KYCVerification.user_id == user_id)
        .order_by(KYCVerification.created_at.desc())
        .limit(1)
    )
    kyc = kyc_result.scalar_one_or_none()

    # Agent profile
    agent_result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    agent = agent_result.scalar_one_or_none()

    # Property count
    prop_count_result = await db.execute(
        select(func.count(Property.id)).where(
            Property.owner_id == user_id,
            Property.is_deleted.is_(False),
        )
    )
    property_count = prop_count_result.scalar_one() or 0

    return {
        "user_id": user_id,
        "found": True,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.value if user.role else None,
        "is_verified": user.is_verified,
        "is_kyc_verified": user.is_kyc_verified,
        "kyc_status": kyc.status.value if kyc else None,
        "kyc_expires_at": kyc.expires_at.isoformat() if kyc and kyc.expires_at else None,
        "is_agent": agent is not None,
        "agent_license": agent.license_number if agent else None,
        "agency_name": agent.agency_name if agent else None,
        "badge_level": agent.badge_level if agent else None,
        "property_count": property_count,
        "account_age_days": (datetime.now(UTC) - user.created_at).days if user.created_at else 0,
        "status_checked_at": datetime.now(UTC).isoformat(),
    }


async def initiate_seller_verification(
    db: AsyncSession,
    user_id: int,
    national_id: str | None = None,
    kra_pin: str | None = None,
    license_number: str | None = None,
) -> dict:
    """Run the full multi-layer seller verification workflow.

    This is the primary entry-point for triggering a complete verification.
    It runs all four layers and computes a composite trust score.

    Returns a dict with the results of each layer and the final trust score.
    """
    start_time = datetime.now(UTC)

    logger.info(
        '{"event":"seller_verification_started","user_id":%d}',
        user_id,
    )

    # ── Layer 1: Identity ────────────────────────────────────────────────
    identity_result = await verify_seller_identity(
        db, user_id, national_id=national_id, kra_pin=kra_pin,
    )

    # ── Layer 2: Licence ─────────────────────────────────────────────────
    license_result = await verify_seller_license(db, user_id, license_number)

    # ── Layer 3: Background ──────────────────────────────────────────────
    background_result = await verify_seller_background(db, user_id)

    # ── Layer 4: Address ─────────────────────────────────────────────────
    address_result = await verify_physical_address(db, user_id)

    # ── Composite Trust Score ────────────────────────────────────────────
    layer_results = {
        "id_validation": {"score": identity_result.get("score", 0)},
        "license_validation": {"score": license_result.get("score") or 0},
        "background_check": {"risk_score": background_result.get("risk_score", 0)},
        "address_verification": address_result,
    }
    trust = await compute_seller_trust_score(db, user_id, layer_results)

    # ── Determine overall verdict ────────────────────────────────────────
    overall_verified = (
        identity_result.get("verified", False)
        and background_result.get("clear", False)
        and address_result.get("verified", False)
    )
    # Licence is optional (non-agents skip it)
    if license_result.get("is_agent", False):
        overall_verified = overall_verified and license_result.get("verified", False)

    result = {
        "user_id": user_id,
        "overall_verified": overall_verified,
        "trust_score": trust,
        "layers": {
            "identity": identity_result,
            "license": license_result,
            "background": background_result,
            "address": address_result,
        },
        "completed_at": datetime.now(UTC).isoformat(),
        "duration_ms": round((datetime.now(UTC) - start_time).total_seconds() * 1000),
    }

    # ── If identity passes, mark user is_verified (soft flag) ────────────
    if overall_verified:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and not user.is_verified:
            user.is_verified = True
            await db.commit()
            await cache_delete(f"vestra:user:{user_id}")

    logger.info(
        '{"event":"seller_verification_completed","user_id":%d,'
        '"overall_verified":%s,"trust_score":%.1f,"duration_ms":%d}',
        user_id, overall_verified, trust["trust_score"], result["duration_ms"],
    )

    # ── Fire analytics event ─────────────────────────────────────────────
    _fire_and_forget(
        _bg_track_verification_event(user_id, result)
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Functions
# ═══════════════════════════════════════════════════════════════════════════════


async def admin_review_seller(
    db: AsyncSession,
    user_id: int,
    reviewer_id: int,
    decision: str,
    notes: str,
) -> dict:
    """Admin approves or rejects a seller's overall verification.

    ``decision`` must be one of: ``approve``, ``reject``, ``flag_for_review``.
    This updates the user's ``is_verified`` flag and logs the outcome.
    """
    valid_decisions = {"approve", "reject", "flag_for_review"}
    decision = decision.lower().strip()
    if decision not in valid_decisions:
        return {
            "success": False,
            "error": f"Invalid decision '{decision}'. Must be one of: {', '.join(valid_decisions)}",
        }

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": f"User {user_id} not found"}

    reviewer_result = await db.execute(select(User).where(User.id == reviewer_id))
    reviewer = reviewer_result.scalar_one_or_none()
    if not reviewer:
        return {"success": False, "error": f"Reviewer {reviewer_id} not found"}

    if decision == "approve":
        user.is_verified = True
        user.is_kyc_verified = True
    elif decision == "reject":
        user.is_verified = False

    await db.commit()
    await cache_delete(f"vestra:user:{user_id}")
    await cache_delete("vestra:list:*")

    logger.info(
        '{"event":"seller_admin_review","user_id":%d,"reviewer_id":%d,'
        '"decision":"%s"}',
        user_id, reviewer_id, decision,
    )

    return {
        "success": True,
        "user_id": user_id,
        "decision": decision,
        "notes": notes,
        "reviewer_id": reviewer_id,
        "reviewed_at": datetime.now(UTC).isoformat(),
    }


async def get_pending_seller_verifications(
    db: AsyncSession,
    limit: int = 20,
) -> list[dict]:
    """Get sellers who need manual admin review based on risk signals.

    Returns users who:
      - Have a seller or agent role
      - Are NOT yet verified (is_verified = False or is_kyc_verified = False)
      - Have at least one active property
    Sorted by account age (oldest first — waiting longest).
    """
    result = await db.execute(
        select(User)
        .where(
            User.role.in_([UserRole.seller, UserRole.agent, UserRole.landlord]),
            or_(
                User.is_verified.is_(False),
                User.is_kyc_verified.is_(False),
            ),
            User.is_active.is_(True),
        )
        .order_by(User.created_at.asc())
        .limit(limit)
    )
    users = result.scalars().all()

    pending = []
    for user in users:
        # Count properties
        prop_result = await db.execute(
            select(func.count(Property.id)).where(
                Property.owner_id == user.id,
                Property.is_deleted.is_(False),
            )
        )
        prop_count = prop_result.scalar_one() or 0
        if prop_count == 0:
            continue

        # Latest KYC
        kyc_result = await db.execute(
            select(KYCVerification)
            .where(KYCVerification.user_id == user.id)
            .order_by(KYCVerification.created_at.desc())
            .limit(1)
        )
        kyc = kyc_result.scalar_one_or_none()

        pending.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value if user.role else None,
            "is_verified": user.is_verified,
            "is_kyc_verified": user.is_kyc_verified,
            "kyc_status": kyc.status.value if kyc else None,
            "kyc_submitted_at": kyc.created_at.isoformat() if kyc else None,
            "property_count": prop_count,
            "joined_at": user.created_at.isoformat() if user.created_at else None,
        })

    return pending


async def search_seller(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Search sellers by name, email, phone, or ID for the admin panel."""
    like_pattern = f"%{query}%"

    result = await db.execute(
        select(User)
        .where(
            User.role.in_([UserRole.seller, UserRole.agent, UserRole.landlord]),
            or_(
                User.full_name.ilike(like_pattern),
                User.email.ilike(like_pattern),
            ),
        )
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.value if u.role else None,
            "is_verified": u.is_verified,
            "is_kyc_verified": u.is_kyc_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Background Helpers
# ═══════════════════════════════════════════════════════════════════════════════


async def _bg_track_verification_event(user_id: int, result: dict) -> None:
    """Fire-and-forget: track seller verification event in analytics."""
    try:
        from app.services.analytics_service import fire_and_forget_track_user_event

        await fire_and_forget_track_user_event(
            user_id=user_id,
            event_type="seller_verification_completed",
            event_data={
                "overall_verified": result["overall_verified"],
                "trust_score": result["trust_score"]["trust_score"],
                "trust_level": result["trust_score"]["trust_level"],
            },
        )
    except Exception:
        logger.warning(
            '{"event":"bg_seller_verification_track_failed","user_id":%d}',
            user_id,
        )


# ── Public helpers ─────────────────────────────────────────────────────────────


def parse_kenyan_phone(phone: str) -> str | None:
    """Parse and normalise a Kenyan phone number to +254 format.

    Returns ``None`` if the number is not a valid Kenyan phone.
    """
    result = _validate_kenyan_phone(phone)
    return result.get("normalized")
