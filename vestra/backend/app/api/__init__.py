"""
API Router Registration
=======================
Canonical API at /api/v1/ with legacy backward-compatible mounting at /api/.
"""
from fastapi import APIRouter

from app.api.routes import admin, auth, payments, properties, verification
from app.api.routes.ai_routes import router as ai_router
from app.api.routes.coupons import router as coupons_router
from app.api.routes.currencies import router as currencies_router
from app.api.routes.disputes import router as disputes_router
from app.api.routes.enterprise import router as enterprise_router
from app.api.routes.escrow import router as escrow_router
from app.api.routes.favorites import router as favorites_router
from app.api.routes.fraud import router as fraud_router
from app.api.routes.investment import router as investment_router
from app.api.routes.kyc import router as kyc_router
from app.api.routes.messages import router as messages_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.otp_auth import router as otp_auth_router
from app.api.routes.payouts import router as payouts_router
from app.api.routes.referrals import router as referrals_router
from app.api.routes.rentals import router as rentals_router
from app.api.routes.reports import router as reports_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.title_chain import router as title_chain_router
from app.api.routes.trust_safety import router as trust_safety_router
from app.api.routes.whatsapp import router as whatsapp_router

# ── Helper: include all sub-routers into a given parent router ──────────────────

def _include_all_routers(router: APIRouter) -> None:
    """Attach every route module to the given router."""
    router.include_router(auth.router)  # Keep legacy email auth
    router.include_router(otp_auth_router)  # Phone OTP auth (primary)
    router.include_router(properties.router)
    router.include_router(verification.router)
    router.include_router(payments.router)
    router.include_router(admin.router)
    router.include_router(ai_router)
    router.include_router(whatsapp_router)
    router.include_router(subscriptions_router)
    router.include_router(rentals_router)
    router.include_router(kyc_router)
    router.include_router(notifications_router)
    router.include_router(messages_router)
    router.include_router(fraud_router)
    router.include_router(favorites_router)
    router.include_router(reports_router)
    router.include_router(enterprise_router)
    router.include_router(monitoring_router)
    router.include_router(escrow_router)
    router.include_router(disputes_router)
    router.include_router(reviews_router)
    router.include_router(payouts_router)
    router.include_router(coupons_router)
    router.include_router(currencies_router)
    router.include_router(investment_router)
    router.include_router(title_chain_router)
    router.include_router(trust_safety_router)
    router.include_router(referrals_router)


# ── Canonical v1 Router ─────────────────────────────────────────────────────────

api_router = APIRouter(prefix="/api/v1")
_include_all_routers(api_router)


@api_router.get("/version", tags=["meta"], summary="API version info")
async def api_version_v1():
    return {
        "version": "4.3.0",
        "api_version": "v1",
        "deprecated_versions": [],
    }


# ── Legacy / Backward-Compatible Router ─────────────────────────────────────────
# Serves the same routes at /api/* for old clients. Responses include deprecation
# headers so clients can migrate to /api/v1/*.

legacy_router = APIRouter(prefix="/api")
_include_all_routers(legacy_router)


@legacy_router.get("/version", tags=["meta"], summary="API version info")
async def api_version_legacy():
    return {
        "version": "4.3.0",
        "api_version": "v1",
        "deprecated_versions": [],
    }
