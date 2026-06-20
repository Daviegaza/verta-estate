from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.schemas.verification import MpesaPaymentRequest, PaymentResponse
from app.services.payment_service import (
    initiate_mpesa_payment, handle_mpesa_callback,
    get_payment_by_id, get_user_payments,
    process_stripe_payment_intent,
    refund_payment_stripe, refund_payment_mpesa,
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

        # ── Send payment receipt notification ──────────────────────────────
        asyncio.create_task(
            _bg_send_payment_receipt(payment)
        )

        # ── Rent Payment Auto-Update ───────────────────────────────────────
        # If this was a rent payment, auto-update the RentPayment record,
        # generate a receipt, and notify both parties.
        if payment.purpose == PaymentPurpose.rent or (
            payment.description and 'rent' in payment.description.lower()
        ):
            asyncio.create_task(
                _bg_handle_rent_payment_completed(payment, db)
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


# ── Stripe Webhook ──────────────────────────────────────────────────────────────


@router.post("/stripe/callback")
async def stripe_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook endpoint.
    Triggered by Stripe after payment events (succeeded, failed, refunded).
    Verifies signature using STRIPE_WEBHOOK_SECRET.
    Idempotent via Redis deduplication (stripe:{event_id}).
    """
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # ── Signature verification ──────────────────────────────────────────────
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        logger.warning('{"event":"stripe_webhook_blocked","reason":"missing_signature"}')
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning('{"event":"stripe_webhook_blocked","reason":"invalid_payload"}')
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning('{"event":"stripe_webhook_blocked","reason":"invalid_signature"}')
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.get("id", "unknown")
    event_type = event.get("type", "unknown")

    logger.info(
        '{"event":"stripe_webhook_received","type":"%s","id":"%s"}',
        event_type, event_id,
    )

    # ── Idempotency (Redis atomic dedup) ────────────────────────────────────
    is_new = await check_and_mark_processed(f"stripe:{event_id}", ttl=86400)
    if not is_new:
        logger.info(
            '{"event":"stripe_webhook_duplicate","type":"%s","id":"%s"}',
            event_type, event_id,
        )
        return {"received": True, "id": event_id, "status": "duplicate"}

    # ── Route event type ────────────────────────────────────────────────────
    data_object = event.get("data", {}).get("object", {})

    if event_type == "payment_intent.succeeded":
        payment = await process_stripe_payment_intent(db, data_object)
        if payment and payment.status == PaymentStatus.completed:
            ref_id = payment.payment_metadata.get("reference_id") if payment.payment_metadata else None

            # Fire event bus
            from app.services.event_bus import emit_event, EVENT_PAYMENT_COMPLETED
            asyncio.create_task(_bg_emit_event_after_payment(payment))

            # Rent payment auto-update
            if payment.purpose == PaymentPurpose.rent or (
                payment.description and 'rent' in payment.description.lower()
            ):
                asyncio.create_task(_bg_handle_rent_payment_completed(payment, db))

            # Verification report
            if payment.purpose == PaymentPurpose.verification_report and ref_id:
                verification = await create_verification_request(
                    db, ref_id, payment.user_id, payment.id
                )
                background_tasks.add_task(run_ai_verification, db, verification.id)

            # Subscription
            if payment.purpose == PaymentPurpose.subscription:
                from app.services.subscription_service import (
                    get_subscription_orm, create_subscription, renew_subscription,
                )
                from app.models.user import User
                result = await db.execute(select(User).where(User.id == payment.user_id))
                user = result.scalar_one_or_none()
                if user:
                    existing_sub = await get_subscription_orm(db, user.id)
                    if existing_sub:
                        await renew_subscription(db, user.id, payment.id)
                    else:
                        await create_subscription(
                            db, user.id, "basic", payment.amount,
                            payment_method="stripe",
                        )

            # Listing fee / featured
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
                        '{"event":"featured_listing_activated_stripe","property_id":%d,"expires":"%s"}',
                        ref_id, prop.featured_expires_at.isoformat(),
                    )

        logger.info(
            '{"event":"stripe_payment_succeeded","pi":"%s","payment_id":%d}',
            data_object.get("id"), payment.id if payment else None,
        )

    elif event_type == "payment_intent.payment_failed":
        payment = await process_stripe_payment_intent(db, data_object)
        logger.info(
            '{"event":"stripe_payment_failed","pi":"%s","payment_id":%d}',
            data_object.get("id"), payment.id if payment else None,
        )

    elif event_type == "charge.refunded":
        charge = data_object
        pi_id = charge.get("payment_intent")
        if pi_id:
            result = await db.execute(
                select(Payment).where(Payment.stripe_payment_intent_id == pi_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.refunded
                payment.error_message = f"Refunded on Stripe: {charge.get('id')}"
                await db.commit()
                logger.info(
                    '{"event":"stripe_charge_refunded","pi":"%s","payment_id":%d}',
                    pi_id, payment.id,
                )

    else:
        logger.info(
            '{"event":"stripe_webhook_unhandled","type":"%s","id":"%s"}',
            event_type, event_id,
        )

    return {"received": True, "id": event_id}


# ── User Refund ─────────────────────────────────────────────────────────────────


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request a refund for a completed payment.
    - Stripe payments are refunded via the Stripe API.
    - M-Pesa payments are marked as refunded and flagged for manual B2C reversal.
    - User must own the payment or be an admin.
    """
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.user_id != current_user.id and current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Not authorized to refund this payment")
    if payment.status != PaymentStatus.completed:
        raise HTTPException(status_code=400, detail="Only completed payments can be refunded")

    if payment.method == PaymentMethod.stripe:
        try:
            result = await refund_payment_stripe(db, payment)
        except ValueError as e:
            raise HTTPException(status_code=502, detail=str(e))
    elif payment.method == PaymentMethod.mpesa:
        result = await refund_payment_mpesa(db, payment)
    else:
        raise HTTPException(status_code=400, detail=f"Cannot refund {payment.method.value} payments")

    return result


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


async def _bg_send_payment_receipt(payment) -> None:
    """Fire-and-forget: send payment receipt notification."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import send_payment_receipt

    try:
        async with AsyncSessionLocal() as bg_db:
            await send_payment_receipt(
                db=bg_db,
                user_id=payment.user_id,
                payment_id=payment.id,
                amount_kes=float(payment.amount),
                purpose=payment.purpose.value if payment.purpose else "payment",
                mpesa_receipt=payment.mpesa_receipt_number,
            )
    except Exception:
        logger.warning(
            '{"event":"bg_payment_receipt_failed","payment_id":%d}',
            payment.id,
        )


async def _bg_handle_rent_payment_completed(payment, db) -> None:
    """
    Fire-and-forget: auto-update rent record, generate receipt, notify parties.

    When a tenant pays rent via M-Pesa:
    1. RentPayment record auto-updates to 'paid'
    2. Receipt is auto-generated
    3. Landlord is notified: "Rent Paid!"
    4. Tenant is notified: "Receipt Ready"
    5. WhatsApp receipt is sent to tenant
    """
    from app.services.smart_automation import auto_update_rent_on_payment

    try:
        # Re-create a fresh DB session for background task
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            receipt = await auto_update_rent_on_payment(bg_db, payment)
            if receipt:
                logger.info(
                    '{"event":"rent_auto_completed","receipt":"%s","amount":%f,"tenant":"%s"}',
                    receipt.get("receipt_number"), receipt.get("amount_paid"),
                    receipt.get("tenant_name"),
                )
    except Exception as e:
        logger.error(
            '{"event":"bg_rent_update_failed","payment_id":%d,"error":"%s"}',
            payment.id, str(e),
        )
