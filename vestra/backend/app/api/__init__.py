from fastapi import APIRouter
from app.api.routes import auth, properties, verification, payments, admin
from app.api.routes.ai_routes import router as ai_router
from app.api.routes.whatsapp import router as whatsapp_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.rentals import router as rentals_router
from app.api.routes.kyc import router as kyc_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.messages import router as messages_router
from app.api.routes.fraud import router as fraud_router
from app.api.routes.favorites import router as favorites_router
from app.api.routes.otp_auth import router as otp_auth_router
from app.api.routes.reports import router as reports_router
from app.api.routes.enterprise import router as enterprise_router
from app.api.routes.monitoring import router as monitoring_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)  # Keep legacy email auth
api_router.include_router(otp_auth_router)  # Phone OTP auth (primary)
api_router.include_router(properties.router)
api_router.include_router(verification.router)
api_router.include_router(payments.router)
api_router.include_router(admin.router)
api_router.include_router(ai_router)
api_router.include_router(whatsapp_router)
api_router.include_router(subscriptions_router)
api_router.include_router(rentals_router)
api_router.include_router(kyc_router)
api_router.include_router(notifications_router)
api_router.include_router(messages_router)
api_router.include_router(fraud_router)
api_router.include_router(favorites_router)
api_router.include_router(reports_router)
api_router.include_router(enterprise_router)
api_router.include_router(monitoring_router)
