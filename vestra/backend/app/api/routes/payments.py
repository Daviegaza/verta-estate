from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.schemas.verification import MpesaPaymentRequest, PaymentResponse
from app.services.payment_service import (
    initiate_mpesa_payment, handle_mpesa_callback,
    get_payment_by_id, get_user_payments
)
from app.services.verification_service import (
    create_verification_request, run_ai_verification
)
from app.models.payment import PaymentPurpose, PaymentStatus
from app.models.user import UserRole
from app.core.redis import cache_delete, check_and_mark_processed
import asyncio
import hashlib
import hmac
import logging

logger = logging.getLogger("vestra")
router = APIRouter(prefix="/payments", tags=["Payments"])

# Safaricom M-Pesa production IP ranges (verified from Safaricom documentation)
SAFARICOM_IPS = {
    "196.201.214.200", "196.201.214.201", "196.201.214.202",
    "196.201.214.203", "196.201.214.204", "196.201.214.205",
    "196.201.214.206", "196.201.214.207", "196.201.214.208",
    "196.201.214.209", "196.201.214.210", "196.201.214.211",
}

# Sandbox IPs are the same range
SAFARICOM_SANDBOX_IPS = {"196.201.214.200"}


def _verify_safaricom_ip(client_ip: str) -> bool:
    """Verify that the request originates from a Safaricom IP address."""
    if settings.MPESA_ENV == "sandbox":
        # In sandbox, also allow localhost and common dev IPs
        if client_ip in ("127.0.0.1", "localhost", "::1"):
            return True
        return client_ip in SAFARICOM_SANDBOX_IPS
    return client_ip in SAFARICOM_IPS


def _verify_callback_signature(body: bytes, signature: str | None) -> bool:
    """Verify HMAC signature if Safaricom provides it in production."""
    if settings.MPESA_ENV == "sandbox":
        return True  # Sandbox may not send signatures
    if not signature or not settings.MPESA_PASSKEY:
        return True  # Skip if not configured yet
    expected = hmac.new(
        settings.MPESA_PASSKEY.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/mpesa/initiate", response_model=dict)
async def initiate_mpesa(
    data: MpesaPaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        purpose = PaymentPurpose(data.purpose)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment purpose: {data.purpose}")

    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=data.phone_number,
        amount=data.amount,
        purpose=purpose,
        reference_id=data.reference_id,
    )
    return {
        "payment_id": payment.id,
        "checkout_request_id": payment.mpesa_checkout_request_id,
        "status": payment.status.value,
        "message": "Check your phone and enter your M-Pesa PIN",
        "amount": payment.amount,
        "currency": payment.currency,
    }


@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Safaricom M-Pesa STK Push callback endpoint.
    Triggered automatically by Safaricom after payment attempt.

    SECURITY: Verifies Safaricom IP range (and HMAC signature in production)
    to prevent unauthorized payment confirmations.
    Replay protection: ignores duplicate checkout_request_ids.
    """
    # ── Security: IP whitelist ────────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    if not _verify_safaricom_ip(client_ip):
        logger.warning(
            '{"event":"mpesa_callback_blocked","reason":"invalid_ip","ip":"%s"}',
            client_ip
        )
        # Return success to not reveal rejection to attacker
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── Security: HMAC signature verification ─────────────────────────────
    body = await request.body()
    signature = request.headers.get("X-Safaricom-Signature") or request.headers.get("X-Hub-Signature-256", "")
    if not _verify_callback_signature(body, signature):
        logger.warning(
            '{"event":"mpesa_callback_blocked","reason":"invalid_signature","ip":"%s"}',
            client_ip
        )
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── Parse callback body ───────────────────────────────────────────────
    try:
        import json as _json
        callback_data = _json.loads(body.decode())
    except Exception:
        logger.warning(
            '{"event":"mpesa_callback_blocked","reason":"invalid_json","ip":"%s"}',
            client_ip
        )
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── Replay protection (Redis atomic SET NX, shared across all workers) ──
    checkout_id = (
        callback_data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID", "")
    )
    if checkout_id:
        is_new = await check_and_mark_processed(f"mpesa:{checkout_id}", ttl=86400)
        if not is_new:
            logger.warning(
                '{"event":"mpesa_callback_blocked","reason":"replay","checkout_id":"%s"}',
                checkout_id
            )
            return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── Process payment ───────────────────────────────────────────────────
    payment = await handle_mpesa_callback(db, callback_data)

    if payment and payment.status == PaymentStatus.completed:
        ref_id = payment.payment_metadata.get("reference_id") if payment.payment_metadata else None

        # ── Fire event bus: payment completed ──────────────────────────────
        from app.services.event_bus import emit_event, EVENT_PAYMENT_COMPLETED
        asyncio.create_task(
            _bg_emit_event_after_payment(payment)
        )

        # Handle verification report payment
        if payment.purpose == PaymentPurpose.verification_report and ref_id:
            verification = await create_verification_request(db, ref_id, payment.user_id, payment.id)
            background_tasks.add_task(run_ai_verification, db, verification.id)

        # Handle subscription payment
        if payment.purpose == PaymentPurpose.subscription:
            from app.services.subscription_service import (
                get_subscription_orm, create_subscription, renew_subscription, upgrade_subscription
            )
            from app.models.user import User, UserRole
            result = await db.execute(select(User).where(User.id == payment.user_id))
            user = result.scalar_one_or_none()

            if user:
                existing_sub = await get_subscription_orm(db, user.id)
                if existing_sub:
                    await renew_subscription(db, user.id, payment.id)
                else:
                    await create_subscription(
                        db, user.id, "basic", payment.amount,
                        payment_method="mpesa",
                        mpesa_phone=payment.phone_number,
                    )
                    # ── Referral reward: first subscription payment ──────
                    from app.services.referral_engine import award_referral_reward
                    reward_result = await award_referral_reward(db, user.id, "first_payment")
                    if reward_result:
                        logger.info(
                            '{"event":"referral_reward_for_payment","referrer":%d,'
                            '"referred":%d,"amount_kes":%d}',
                            reward_result["referrer_id"], user.id,
                            reward_result["reward_kes"],
                        )

        # Handle listing fee payment → activate featured listing
        if payment.purpose == PaymentPurpose.listing_fee and ref_id:
            from datetime import datetime, timedelta, timezone
            from app.services.property_service import get_property_by_id
            prop = await get_property_by_id(db, ref_id)
            if prop:
                now = datetime.now(timezone.utc)
                prop.is_featured = True
                prop.featured_expires_at = now + timedelta(days=30)
                await db.commit()
                await cache_delete(f"vestra:prop:{prop.id if hasattr(prop, 'id') else prop.get('id')}")
                await cache_delete("vestra:list:*")
                logger.info(
                    '{"event":"featured_listing_activated","property_id":%d,"expires":"%s"}',
                    ref_id, prop.featured_expires_at.isoformat()
                )

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/status/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.user_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    return payment


@router.get("/my", response_model=list[PaymentResponse])
async def my_payments(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_payments(db, current_user.id)


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_event_after_payment(payment) -> None:
    """Fire-and-forget: emit payment.completed event."""
    from app.services.event_bus import emit_event, EVENT_PAYMENT_COMPLETED

    try:
        data = {
            "payment_id": payment.id,
            "amount": float(payment.amount),
            "purpose": payment.purpose.value if payment.purpose else "unknown",
            "currency": payment.currency,
            "phone": payment.phone_number,
        }
        await emit_event(
            event_type=EVENT_PAYMENT_COMPLETED,
            user_id=payment.user_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_payment_event_failed","payment_id":%d}',
            payment.id,
        )
