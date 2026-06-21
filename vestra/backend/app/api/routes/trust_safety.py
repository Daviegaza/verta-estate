"""
Trust & Safety API routes — comprehensive verification, fraud detection,
trust scoring, and safety infrastructure for the VESTRA platform.

All endpoints live under /api/v1/trust/ (and /api/trust/ for backward compat).
Implements the 100% Genuine Users guarantee with multi-layer verification.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user, get_current_user_optional
from app.models.user import UserRole
from app.services.agent_verification_service import (
    get_agent_audit_trail,
    get_agent_verification_stats,
    get_agent_verification_status,
    invalidate_agent_cache,
    list_verified_agents,
    verify_agent,
)
from app.services.enhanced_fraud_detection import (
    bulk_screen_properties,
    detect_scam_patterns,
    get_comprehensive_fraud_score,
    get_fraud_dashboard_stats,
)
from app.services.fraud_service import (
    report_fraud,
)
from app.services.property_authentication_service import (
    run_full_property_authentication,
)
from app.services.property_service import get_property_by_id
from app.services.rate_limit_advanced import EndpointLimit, get_advanced_limiter
from app.services.seller_verification_service import (
    admin_review_seller,
    get_pending_seller_verifications,
    get_seller_verification_status,
    initiate_seller_verification,
    search_seller,
)
from app.services.title_chain import title_chain
from app.services.trust_scoring_engine import (
    compute_user_trust_score,
    get_trust_dashboard_stats,
    invalidate_user_trust_cache,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra.trust_safety")

router = APIRouter(prefix="/trust", tags=["Trust & Safety"])

# ── Rate limit configuration ────────────────────────────────────────────────────
# Register tight limits for verification-heavy endpoints to prevent abuse.
_TRUST_LIMITS = [
    EndpointLimit(
        name="trust:verify-seller", max_requests=10, window_seconds=300,
        burst=3, block_duration=1800,
    ),
    EndpointLimit(
        name="trust:verify-agent", max_requests=10, window_seconds=300,
        burst=3, block_duration=1800,
    ),
    EndpointLimit(
        name="trust:verify-property", max_requests=20, window_seconds=300,
        burst=5, block_duration=1800,
    ),
    EndpointLimit(
        name="trust:fraud-check", max_requests=30, window_seconds=60,
        burst=5,
    ),
    EndpointLimit(
        name="trust:report-scam", max_requests=5, window_seconds=300,
        burst=2, block_duration=3600,
    ),
    EndpointLimit(
        name="trust:site-verification", max_requests=10, window_seconds=600,
        burst=3, block_duration=3600,
    ),
]

try:
    limiter = get_advanced_limiter()
    for _limit in _TRUST_LIMITS:
        limiter.register(_limit)
except Exception:
    logger.warning('{"event":"trust_ratelimit_init_skipped"}')


# ─────────────────────────────────────────────────────────────────────────────────
# 1. POST /verify-seller — Multi-layer seller verification
# ─────────────────────────────────────────────────────────────────────────────────


@router.post(
    "/verify-seller",
    status_code=status.HTTP_200_OK,
    summary="Multi-layer seller verification",
    description=(
        "Runs all four verification layers against a seller: identity document"
        " validation (National ID / KRA PIN), licence check, background check"
        " (fraud blacklist, property history, disputes), and physical address"
        " verification. Returns a composite trust score and per-layer breakdown."
    ),
)
async def verify_seller(
    national_id: str | None = Form(None, description="Kenyan National ID (8 digits)"),
    kra_pin: str | None = Form(None, description="KRA PIN (e.g. P051234567Z)"),
    license_number: str | None = Form(None, description="Agent licence number"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate a full multi-layer seller verification for the current user."""

    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:verify-seller", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification requests. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Fail open if rate limiter unavailable

    result = await initiate_seller_verification(
        db=db,
        user_id=current_user.id,
        national_id=national_id,
        kra_pin=kra_pin,
        license_number=license_number,
    )

    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 2. POST /verify-agent — Agent license and certification verification
# ─────────────────────────────────────────────────────────────────────────────────


@router.post(
    "/verify-agent",
    status_code=status.HTTP_200_OK,
    summary="Agent license and certification verification",
    description=(
        "Runs the full agent verification pipeline: licence validation, professional"
        " history check, brokerage affiliation verification, and past transaction"
        " audit. Returns a composite verification score (0-100), badge level, and"
        " per-check breakdown."
    ),
)
async def verify_agent_endpoint(
    user_id: int | None = Query(None, description="Target user ID (admin only). Defaults to current user."),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify an agent's license, certifications, and professional history."""
    target_id = user_id if user_id is not None else current_user.id

    # Only admins can verify other users
    if user_id is not None and user_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can initiate verification for other users.",
        )

    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:verify-agent", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification requests. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass

    result = await verify_agent(db=db, user_id=target_id)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 3. POST /verify-property — Property authentication with title deed check
# ─────────────────────────────────────────────────────────────────────────────────


@router.post(
    "/verify-property",
    status_code=status.HTTP_200_OK,
    summary="Property authentication with title deed check",
    description=(
        "Runs the full property authentication pipeline: title deed OCR analysis,"
        " land registry format validation, ownership verification, boundary/geolocation"
        " confirmation, and tax record verification. Optionally accepts optional OCR"
        " text from an already-scanned title deed. On full authentication, creates a"
        " TitleChain genesis block for the property."
    ),
)
async def verify_property(
    property_id: int = Form(...),
    title_deed_document_id: int | None = Form(None, description="Document ID of the uploaded title deed"),
    ocr_text: str | None = Form(None, description="Optional OCR text from title deed scan"),
    kra_pin: str | None = Form(None, description="Owner's KRA PIN for tax verification"),
    rates_paid_upto: str | None = Form(None, description="Land rates paid up to (year or YYYY-MM-DD)"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticate a property with title deed, ownership, and tax checks."""

    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:verify-property", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many property verification requests. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass

    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Only the owner or admin can initiate verification
    owner_id = prop.owner_id if hasattr(prop, "owner_id") else None
    if owner_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the property owner or an admin can initiate verification.",
        )

    result = await run_full_property_authentication(
        db=db,
        property_id=property_id,
        owner_user_id=owner_id,
        title_deed_document_id=title_deed_document_id,
        ocr_text=ocr_text,
        kra_pin=kra_pin,
        rates_paid_upto=rates_paid_upto,
    )

    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 4. GET /score/{user_id} — Get comprehensive trust score with breakdown
# ─────────────────────────────────────────────────────────────────────────────────


@router.get(
    "/score/{user_id}",
    summary="Get comprehensive trust score with breakdown",
    description=(
        "Returns the 6-dimension trust score for a user: identity, transaction history,"
        " community reputation, property verification, response time, and dispute history."
        " Includes overall score (0-100), badge level, per-dimension breakdown, and any"
        " active risk flags. Results are cached for 15 minutes."
    ),
)
async def get_trust_score(
    user_id: int,
    force_refresh: bool = Query(False, description="Bypass cache and force re-computation"),
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the comprehensive 6-dimension trust score for a user."""
    # Auth: only the user themselves or admins can view detailed trust scores
    if current_user is None or (current_user.id != user_id and current_user.role not in (UserRole.admin, UserRole.super_admin)):
        # Public view — return limited data
        result = await compute_user_trust_score(db, user_id, use_cache=not force_refresh)
        if result.get("error"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        return {
            "user_id": user_id,
            "overall_score": result.get("overall_score", 0),
            "badge": result.get("badge", "untrusted"),
            "computed_at": result.get("computed_at"),
        }

    result = await compute_user_trust_score(db, user_id, use_cache=not force_refresh)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 5. GET /fraud-check/{property_id} — Run AI fraud detection on a property
# ─────────────────────────────────────────────────────────────────────────────────


@router.get(
    "/fraud-check/{property_id}",
    summary="Run AI fraud detection on a property",
    description=(
        "Runs all five fraud detection engines against a property: image forgery analysis,"
        " price anomaly detection (z-score / IQR), duplicate listing detection (TF-IDF text"
        " similarity), scam pattern recognition (keyword + urgency scoring), and user"
        " behaviour analysis (listing velocity, account age). Returns a unified risk"
        " score (0-100), per-engine breakdown, and a recommendation (approve / flag / reject)."
    ),
)
async def fraud_check(
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run the full AI fraud detection pipeline against a property listing."""
    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:fraud-check", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many fraud check requests. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass

    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    result = await get_comprehensive_fraud_score(db, property_id)
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )

    logger.info(
        '{"event":"fraud_check_completed","property_id":%d,"risk_score":%.1f,"recommendation":"%s"}',
        property_id, result.get("overall_risk_score", 0), result.get("recommendation", "unknown"),
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 6. POST /report-scam — Report a scam/fake listing
# ─────────────────────────────────────────────────────────────────────────────────


@router.post(
    "/report-scam",
    status_code=status.HTTP_201_CREATED,
    summary="Report a scam or fake listing",
    description=(
        "Submit a fraud report against a listing, user, or agent. Optionally scans the"
        " reported listing's content through the scam pattern detection engine for"
        " additional AI-powered analysis. Reports are queued for admin review."
    ),
)
async def report_scam(
    property_id: int | None = Form(None, description="ID of the property being reported"),
    description: str = Form(..., min_length=10, max_length=2000, description="Detailed description of the scam"),
    reported_phone: str | None = Form(None, description="Phone number of the reported party"),
    reported_email: str | None = Form(None, description="Email of the reported party"),
    reported_name: str | None = Form(None, description="Name of the reported party"),
    evidence_urls: str | None = Form(None, description="Comma-separated evidence URLs"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Report a scam or fake listing for admin investigation."""

    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:report-scam", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many reports submitted. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass

    # ── AI-powered scam pattern analysis on the reported property ──────────
    scam_analysis: dict[str, Any] = {}
    if property_id:
        prop = await get_property_by_id(db, property_id)
        if prop:
            scam_analysis = await detect_scam_patterns(
                db=db,
                title=prop.title or "",
                description=prop.description or "",
                owner_id=prop.owner_id,
            )
            logger.info(
                '{"event":"report_scam_ai_analysis","property_id":%d,"risk_score":%.1f}',
                property_id, scam_analysis.get("risk_score", 0),
            )

    urls = [u.strip() for u in (evidence_urls or "").split(",") if u.strip()]
    report = await report_fraud(
        db=db,
        reporter_id=current_user.id,
        description=description,
        reported_phone=reported_phone,
        reported_email=reported_email,
        reported_name=reported_name,
        evidence_urls=urls,
    )

    response: dict[str, Any] = {
        "report_id": report.id,
        "status": report.status.value if hasattr(report.status, "value") else report.status,
        "message": "Thank you for your report. Our Trust & Safety team will investigate.",
    }

    if scam_analysis and scam_analysis.get("risk_score", 0) >= 40:
        response["scam_risk_score"] = scam_analysis["risk_score"]
        response["scam_risk_level"] = scam_analysis.get("risk_level", "unknown")
        response["scam_indicators"] = scam_analysis.get("flags", [])

    return response


# ─────────────────────────────────────────────────────────────────────────────────
# 7. GET /verified-badge/{user_id} — Get verification badge level and details
# ─────────────────────────────────────────────────────────────────────────────────


@router.get(
    "/verified-badge/{user_id}",
    summary="Get verification badge level and details",
    description=(
        "Returns the current verification badge level (platinum / gold / silver / bronze /"
        " untrusted), the underlying trust score, and a summary of which verification"
        " dimensions contributed. Lightweight — uses cached data where possible."
    ),
)
async def verified_badge(
    user_id: int,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the verification badge level and details for a user."""
    # Public: returns badge only. Authenticated: returns full breakdown.
    score_data = await compute_user_trust_score(db, user_id, use_cache=True)
    if score_data.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    badge = score_data.get("badge", "untrusted")
    overall_score = score_data.get("overall_score", 0)
    risk_flags = score_data.get("risk_flags", [])

    # Build badge metadata
    badge_meta = {
        "platinum": {"color": "#7c3aed", "label": "Platinum Trusted", "min_score": 90},
        "gold": {"color": "#f59e0b", "label": "Gold Trusted", "min_score": 75},
        "silver": {"color": "#9ca3af", "label": "Silver Trusted", "min_score": 60},
        "bronze": {"color": "#f97316", "label": "Bronze Trusted", "min_score": 40},
        "untrusted": {"color": "#6b7280", "label": "Unverified", "min_score": 0},
    }
    meta = badge_meta.get(badge, badge_meta["untrusted"])

    # Also check seller verification status for additional context
    seller_status = await get_seller_verification_status(db, user_id)
    agent_status = await get_agent_verification_status(db, user_id)

    response: dict[str, Any] = {
        "user_id": user_id,
        "badge": badge,
        "badge_label": meta["label"],
        "badge_color": meta["color"],
        "trust_score": overall_score,
        "seller_verified": seller_status.get("is_verified", False),
        "kyc_verified": seller_status.get("is_kyc_verified", False),
        "agent_badge": agent_status.get("badge_level", "unverified") if not agent_status.get("error") else None,
        "computed_at": score_data.get("computed_at"),
    }

    # Only return full breakdown to the user themselves or admins
    if current_user is not None and (current_user.id == user_id or current_user.role in (UserRole.admin, UserRole.super_admin)):
        response["dimensions"] = score_data.get("dimensions", {})
        response["risk_flags"] = risk_flags

    return response


# ─────────────────────────────────────────────────────────────────────────────────
# 8. GET /safety-tips — Get contextual safety tips for buyers/sellers
# ─────────────────────────────────────────────────────────────────────────────────


@router.get(
    "/safety-tips",
    summary="Get contextual safety tips for buyers and sellers",
    description=(
        "Returns curated safety tips categorised by audience (buyers, sellers, agents, all)."
        " Tips are dynamically prioritised based on whether the requesting user has a"
        " verified profile, recent disputes, or other risk signals. Unauthenticated"
        " requests receive the general set of tips."
    ),
)
async def safety_tips(
    audience: str = Query("all", regex="^(buyer|seller|agent|all)$", description="Target audience for the tips"),
    locale: str = Query("en", description="Language locale (en/sw)"),
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get contextual safety tips for buyers, sellers, or agents."""

    # ── Base tip database (categorised and severity-ranked) ─────────────────
    tips_by_category: dict[str, list[dict]] = {
        "buyer": [
            {
                "id": "buy-001",
                "severity": "critical",
                "title": "Always use VESTRA Escrow",
                "body": "Never send money directly to a seller via M-Pesa, bank transfer, or wire. All payments must go through VESTRA Escrow for full protection.",
                "icon": "shield_check",
            },
            {
                "id": "buy-002",
                "severity": "critical",
                "title": "Verify the property in person",
                "body": "Visit the property physically before making any payment. If the seller refuses a site visit, this is a major red flag.",
                "icon": "map_pin",
            },
            {
                "id": "buy-003",
                "severity": "high",
                "title": "Check the seller's trust score",
                "body": "Always review the seller's trust score and verification badge before engaging. A score below 40 is a warning sign.",
                "icon": "score",
            },
            {
                "id": "buy-004",
                "severity": "high",
                "title": "Request title deed documents",
                "body": "Ask the seller to upload their title deed and other ownership documents. Run a property verification to authenticate them.",
                "icon": "document",
            },
            {
                "id": "buy-005",
                "severity": "high",
                "title": "Be wary of urgent sales",
                "body": '"Owner leaving country" and "urgent sale" are common scam phrases. Cross-check the listing with our AI fraud detection.',
                "icon": "warning",
            },
            {
                "id": "buy-006",
                "severity": "medium",
                "title": "Compare prices in the area",
                "body": "Use VESTRA's price analysis to check if the listing price is within normal range for the area. Suspiciously low prices are often scams.",
                "icon": "trending_down",
            },
            {
                "id": "buy-007",
                "severity": "medium",
                "title": "Confirm agent credentials",
                "body": "If dealing with an agent, verify their license number and check their agent verification badge on the platform.",
                "icon": "badge",
            },
            {
                "id": "buy-008",
                "severity": "low",
                "title": "Keep communication on-platform",
                "body": "Keep all communication within VESTRA's messaging system. Off-platform conversations cannot be monitored or used as evidence in disputes.",
                "icon": "chat",
            },
        ],
        "seller": [
            {
                "id": "sel-001",
                "severity": "high",
                "title": "Complete KYC verification",
                "body": "Fully verified sellers attract more buyers and higher offers. Complete your KYC and seller verification to earn the 'Verified' badge.",
                "icon": "verified",
            },
            {
                "id": "sel-002",
                "severity": "high",
                "title": "Upload genuine property photos",
                "body": "Use real, unedited photos of your property. AI forgery detection flags heavily edited or stock images, which can harm your trust score.",
                "icon": "camera",
            },
            {
                "id": "sel-003",
                "severity": "medium",
                "title": "Be transparent about pricing",
                "body": "Set a realistic market price. Suspiciously low prices (to attract quick buyers) or inflated prices trigger our price anomaly detection.",
                "icon": "attach_money",
            },
            {
                "id": "sel-004",
                "severity": "medium",
                "title": "Respond to buyer inquiries promptly",
                "body": "Quick response times improve your trust score and community reputation. Aim to respond within 4 hours.",
                "icon": "schedule",
            },
            {
                "id": "sel-005",
                "severity": "low",
                "title": "Provide complete documentation",
                "body": "Upload title deeds, KRA PIN, rates clearance certificates, and any other relevant documents to build buyer confidence.",
                "icon": "folder",
            },
        ],
        "agent": [
            {
                "id": "agt-001",
                "severity": "high",
                "title": "Maintain a valid license",
                "body": "Ensure your agent license is current and renewed before expiry. An expired license negatively impacts your agent verification score.",
                "icon": "license",
            },
            {
                "id": "agt-002",
                "severity": "high",
                "title": "Verify your brokerage",
                "body": "List your correct agency/brokerage name. Impersonating a known agency is grounds for permanent platform ban.",
                "icon": "business",
            },
            {
                "id": "agt-003",
                "severity": "medium",
                "title": "Build your review profile",
                "body": "Encourage genuine buyers and sellers to leave reviews after completed transactions. Verified transaction reviews carry more weight.",
                "icon": "star",
            },
        ],
    }

    # ── Personalised tips based on user state ───────────────────────────────
    personalised_tips: list[dict] = []
    if current_user is not None and current_user.id:
        seller_status = await get_seller_verification_status(db, current_user.id)
        score_data = await compute_user_trust_score(db, current_user.id, use_cache=True)

        # If the user hasn't done KYC, always recommend it
        if not seller_status.get("is_kyc_verified"):
            personalised_tips.append({
                "id": "pers-kyc",
                "severity": "high",
                "title": "Complete your KYC verification",
                "body": "KYC (Know Your Customer) verification is required to unlock full platform features and build trust with buyers.",
                "icon": "fingerprint",
            })

        # Low trust score
        trust_score = score_data.get("overall_score", 0)
        if 0 < trust_score < 40:
            personalised_tips.append({
                "id": "pers-lowscore",
                "severity": "high",
                "title": "Your trust score needs attention",
                "body": f"Your current trust score is {trust_score:.0f}/100. Complete verifications and resolve any open disputes to improve it.",
                "icon": "trending_up",
            })

        # Active disputes
        risk_flags = score_data.get("risk_flags", [])
        if "has_open_disputes" in risk_flags:
            personalised_tips.append({
                "id": "pers-dispute",
                "severity": "critical",
                "title": "You have active disputes",
                "body": "Open disputes significantly impact your trust score. Engage with our dispute resolution team to resolve them promptly.",
                "icon": "gavel",
            })

        # Recent fraud reports
        if "confirmed_fraud_reports" in risk_flags:
            personalised_tips.append({
                "id": "pers-fraud",
                "severity": "critical",
                "title": "Potential fraud reports on your account",
                "body": "Your account identifiers appear in confirmed fraud reports. Contact Trust & Safety immediately if you believe this is an error.",
                "icon": "report",
            })

    # ── Select tips by audience ─────────────────────────────────────────────
    if audience == "all":
        selected = (
            tips_by_category["buyer"][:4]
            + tips_by_category["seller"][:3]
            + tips_by_category["agent"][:2]
        )
    else:
        selected = tips_by_category.get(audience, tips_by_category["all"])

    # Merge personalised tips at the top
    all_tips = personalised_tips + selected

    return {
        "audience": audience,
        "total_tips": len(all_tips),
        "personalised_count": len(personalised_tips),
        "tips": all_tips,
        "locale": locale,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────────
# 9. POST /site-verification — Submit physical site verification (GPS + photos)
# ─────────────────────────────────────────────────────────────────────────────────


@router.post(
    "/site-verification",
    status_code=status.HTTP_201_CREATED,
    summary="Submit physical site verification (GPS + photos)",
    description=(
        "Allows a buyer, agent, or admin to submit a physical site verification report"
        " for a property. Requires GPS coordinates and at least one photo. The report"
        " is cross-referenced against the property's listed location for consistency."
        " Results are visible on the property's trust record."
    ),
)
async def site_verification(
    property_id: int = Form(...),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    photo: UploadFile = File(..., description="Site photo as evidence"),
    notes: str | None = Form(None, max_length=1000, description="Verification notes"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a physical site verification with GPS coordinates and photo evidence."""

    # ── Rate limit check ────────────────────────────────────────────────────
    try:
        rl = await limiter.check("trust:site-verification", current_user.email, user_id=current_user.id)
        if not rl.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many site verification submissions. Please wait before retrying.",
                headers=rl.headers,
            )
    except HTTPException:
        raise
    except Exception:
        pass

    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Validate file type
    allowed_mime = {"image/jpeg", "image/png", "image/jpg", "image/heic", "image/heif"}
    if photo.content_type and photo.content_type not in allowed_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{photo.content_type}'. Accepted: JPEG, PNG, HEIC.",
        )

    # Save the photo
    import os

    from app.core.config import settings

    upload_dir = os.path.join(
        settings.UPLOAD_DIR, "site_verifications", str(property_id),
    )
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = f"site_{current_user.id}_{int(datetime.now(UTC).timestamp())}_{photo.filename}".replace(" ", "_")
    photo_path = os.path.join(upload_dir, safe_name)
    content = await photo.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024*1024)}MB.",
        )
    with open(photo_path, "wb") as f:
        f.write(content)

    # ── Cross-reference with property location (geolocation consistency) ────
    geo_check = {}
    if hasattr(prop, "latitude") and prop.latitude and hasattr(prop, "longitude") and prop.longitude:
        from math import asin, cos, radians, sin, sqrt

        def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Great-circle distance between two GPS points in kilometres."""
            earth_radius_km = 6371  # Earth radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            return earth_radius_km * 2 * asin(sqrt(a))

        distance_km = _haversine(
            float(prop.latitude), float(prop.longitude),
            latitude, longitude,
        )
        if distance_km < 0.1:
            geo_check = {"match": True, "distance_km": round(distance_km, 3), "message": "Coordinates match the property location."}
        elif distance_km < 1.0:
            geo_check = {"match": True, "distance_km": round(distance_km, 3), "message": "Coordinates are within 1 km of the property location."}
        elif distance_km < 5.0:
            geo_check = {"match": False, "distance_km": round(distance_km, 3), "message": f"Coordinates are {distance_km:.1f} km from the property location — possible mismatch."}
        else:
            geo_check = {"match": False, "distance_km": round(distance_km, 3), "message": f"Coordinates are {distance_km:.1f} km from the property location — significant mismatch!"}
    else:
        geo_check = {"match": None, "distance_km": None, "message": "Property has no stored GPS coordinates for comparison."}

    logger.info(
        '{"event":"site_verification","property_id":%d,"verifier_id":%d,'
        '"geo_match":%s,"photo":"%s","notes":"%s"}',
        property_id, current_user.id, geo_check.get("match"),
        photo_path, (notes or "")[:200],
    )

    return {
        "property_id": property_id,
        "geo_consistency": geo_check,
        "photo_url": photo_path,
        "status": "submitted",
        "message": "Site verification submitted successfully. Our team will review the evidence.",
        "submitted_at": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────────
# 10. GET /title-chain/{property_id} — Get blockchain-style title ownership chain
# ─────────────────────────────────────────────────────────────────────────────────


@router.get(
    "/title-chain/{property_id}",
    summary="Get blockchain-style title ownership chain",
    description=(
        "Returns the full TitleChain for a property — an immutable, cryptographically"
        " linked chain of ownership events (registration, transfers, verifications,"
        " encumbrances). Each block includes a SHA-256 hash chained to the previous"
        " block, making the entire history tamper-proof. Publicly verifiable."
    ),
)
async def get_title_chain(
    property_id: int,
    verify_integrity: bool = Query(False, description="Run chain integrity verification (hash check)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the blockchain-style title ownership chain for a property."""
    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    history = await title_chain.get_chain_history(db, property_id)
    if not history:
        return {
            "property_id": property_id,
            "title_chain_exists": False,
            "blocks": [],
            "total_blocks": 0,
            "message": "This property does not yet have a TitleChain. Run property verification to create the genesis block.",
        }

    response: dict[str, Any] = {
        "property_id": property_id,
        "title_chain_exists": True,
        "blocks": history,
        "total_blocks": len(history),
        "chain_id": history[0].get("data", {}).get("chain_id") if history else None,
        "established": history[0].get("timestamp") if history else None,
        "last_updated": history[-1].get("timestamp") if history else None,
    }

    # Optional chain integrity verification
    if verify_integrity and history:
        integrity = await title_chain.verify_chain(db, property_id)
        response["integrity"] = {
            "valid": integrity.get("valid", False),
            "reason": integrity.get("reason", ""),
            "blocks_checked": integrity.get("blocks", 0),
        }

    logger.info(
        '{"event":"title_chain_viewed","property_id":%d,"blocks":%d}',
        property_id, len(history),
    )

    return response


# ═════════════════════════════════════════════════════════════════════════════════
# Admin Endpoints
# ═════════════════════════════════════════════════════════════════════════════════


@router.get(
    "/admin/stats",
    summary="Trust & Safety dashboard statistics (admin)",
    description=(
        "Returns aggregated trust and fraud statistics for the admin dashboard:"
        " total verified agents, fraud report trends, trust score distribution,"
        " badge distribution, and pending review counts."
    ),
)
async def trust_admin_stats(
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get aggregated Trust & Safety dashboard statistics."""
    trust_stats = await get_trust_dashboard_stats(db)
    fraud_stats = await get_fraud_dashboard_stats(db)
    agent_stats = await get_agent_verification_stats(db)

    return {
        "trust": trust_stats,
        "fraud": fraud_stats,
        "agents": agent_stats,
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/admin/pending-sellers",
    summary="List sellers pending admin review",
    description="Returns sellers who need manual admin review based on incomplete verification or risk signals.",
)
async def admin_pending_sellers(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List sellers awaiting manual verification review."""
    pending = await get_pending_seller_verifications(db, limit=limit)
    return {
        "total": len(pending),
        "items": pending,
    }


@router.post(
    "/admin/review-seller/{user_id}",
    summary="Admin review seller verification",
    description="Admin approves, rejects, or flags a seller's verification for manual review.",
)
async def admin_review_seller_endpoint(
    user_id: int,
    decision: str = Form(..., regex="^(approve|reject|flag_for_review)$"),
    notes: str = Form("", max_length=2000),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin review of a seller's verification status."""
    result = await admin_review_seller(
        db=db,
        user_id=user_id,
        reviewer_id=current_user.id,
        decision=decision,
        notes=notes,
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.get(
    "/admin/search-sellers",
    summary="Search sellers for admin panel",
    description="Search sellers by name, email, or phone for the admin management panel.",
)
async def admin_search_sellers(
    query: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search sellers for the admin management panel."""
    results = await search_seller(db, query=query, limit=limit)
    return {
        "query": query,
        "total": len(results),
        "items": results,
    }


@router.get(
    "/admin/agent-audit/{user_id}",
    summary="Detailed agent audit trail (admin)",
    description=(
        "Produces a comprehensive audit trail for an agent including profile data,"
        " all reviews, fraud reports, and the full verification result."
    ),
)
async def admin_agent_audit(
    user_id: int,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a detailed audit trail for an agent."""
    result = await get_agent_audit_trail(db, user_id)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/admin/verified-agents",
    summary="List verified agents (admin)",
    description="List all agents that meet a minimum verification score threshold.",
)
async def admin_verified_agents(
    min_score: float = Query(60.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List agents whose profiles meet a minimum verification threshold."""
    agents = await list_verified_agents(db, min_score=min_score, limit=limit, offset=offset)
    return {
        "min_score": min_score,
        "total": len(agents),
        "items": agents,
    }


@router.post(
    "/admin/invalidate-cache/{user_id}",
    summary="Invalidate cached trust score for a user (admin)",
    description="Force-invalidates Redis caches for a user's trust score, agent verification, and seller status.",
)
async def admin_invalidate_cache(
    user_id: int,
    current_user=Depends(get_current_admin),
) -> dict:
    """Invalidate all cached trust & safety data for a user."""
    await invalidate_user_trust_cache(user_id)
    await invalidate_agent_cache(user_id)
    logger.info('{"event":"admin_invalidate_trust_cache","user_id":%d}', user_id)
    return {
        "success": True,
        "user_id": user_id,
        "message": "Trust score and verification caches invalidated.",
    }


@router.post(
    "/admin/bulk-fraud-screen",
    summary="Bulk fraud screen properties (admin)",
    description=(
        "Screen multiple properties for fraud in parallel. Accepts a list of property"
        " IDs and returns risk assessments sorted by risk score (riskiest first)."
        " Maximum 50 properties per request."
    ),
)
async def admin_bulk_fraud_screen(
    property_ids: list[int],
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Screen multiple properties for fraud in parallel."""
    if not property_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No property IDs provided")
    if len(property_ids) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 50 properties per bulk screen request")

    results = await bulk_screen_properties(db, property_ids, max_concurrency=10)
    return {
        "total_screened": len(results),
        "high_risk": sum(1 for r in results if r.get("overall_risk_level") == "high"),
        "medium_risk": sum(1 for r in results if r.get("overall_risk_level") == "medium"),
        "low_risk": sum(1 for r in results if r.get("overall_risk_level") in ("low", "very_low")),
        "results": results,
    }
