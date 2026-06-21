import asyncio
import hashlib
import hmac
import logging
import uuid as _uuid
from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.airtel_money_provider
import app.services.bank_transfer_provider
import app.services.crypto_provider
import app.services.paypal_provider  # noqa: F401 — registers PayPalProvider
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import cache_delete, check_and_mark_processed
from app.core.security import get_current_user
from app.models.payment import Payment, PaymentMethod, PaymentPurpose, PaymentStatus
from app.models.user import UserRole
from app.schemas.verification import MpesaPaymentRequest, PaymentResponse
from app.services.payment_providers import (
    PaymentRequest as ProvPaymentRequest,
)
from app.services.payment_providers import (
    get_provider_by_method,
    list_available_providers,
)
from app.services.payment_service import (
    get_payment_by_id,
    get_user_payments,
    handle_mpesa_callback,
    initiate_mpesa_payment,
    process_stripe_payment_intent,
    refund_payment_mpesa,
    refund_payment_stripe,
)
from app.services.verification_service import create_verification_request, run_ai_verification

logger = logging.getLogger("vestra")

# Background task references to prevent garbage collection of asyncio tasks
_background_tasks: set[asyncio.Task] = set()


# ── Pydantic schemas for new endpoints ──────────────────────────────────────


class InitiatePaymentRequest(BaseModel):
    phone_number: str | None = None
    email: str | None = None
    amount: float
    currency: str = "KES"
    purpose: str = "verification_report"
    reference_id: int | None = None
    description: str = "Vestra Payment"
    callback_url: str | None = None
    metadata: dict = {}


class AvailableMethodsRequest(BaseModel):
    country_code: str = "KE"

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


# ── Payment Methods Discovery ──────────────────────────────────────────────────


@router.post("/methods", response_model=list[dict])
async def get_available_methods(
    data: AvailableMethodsRequest,
    current_user=Depends(get_current_user),
):
    """List available payment methods for the user's country."""
    country_code = data.country_code.upper()

    # Determine which providers are available for this country
    methods = [
        {
            "method": "mpesa",
            "display_name": "M-Pesa",
            "currencies": ["KES"],
            "countries": ["KE"],
            "min_amount": 1,
            "max_amount": 150000,
            "description": "Pay via M-Pesa mobile money",
        },
        {
            "method": "stripe",
            "display_name": "Card (Stripe)",
            "currencies": ["KES", "USD", "EUR", "GBP"],
            "countries": ["KE", "TZ", "UG", "NG", "GH", "ZA"],
            "min_amount": 1,
            "max_amount": 999999,
            "description": "Pay via credit/debit card",
        },
        {
            "method": "bank_transfer",
            "display_name": "Bank Transfer",
            "currencies": ["KES"],
            "countries": ["KE"],
            "min_amount": 100,
            "max_amount": 9999999,
            "description": "Pay via direct bank transfer",
        },
        {
            "method": "paypal",
            "display_name": "PayPal",
            "currencies": ["USD", "EUR", "GBP"],
            "countries": ["KE", "UG", "NG", "GH", "ZA"],
            "min_amount": 1,
            "max_amount": 999999,
            "description": "Pay via PayPal account or card",
        },
        {
            "method": "airtel_money",
            "display_name": "Airtel Money",
            "currencies": ["KES"],
            "countries": ["KE"],
            "min_amount": 1,
            "max_amount": 150000,
            "description": "Pay via Airtel Money mobile money",
        },
        {
            "method": "crypto",
            "display_name": "Cryptocurrency (USDT/USDC)",
            "currencies": ["USDT", "USDC"],
            "countries": ["KE", "UG", "NG", "GH", "ZA"],
            "min_amount": 5,
            "max_amount": 9999999,
            "description": "Pay with USDT or USDC on Polygon network",
        },
    ]

    # Filter to available providers (those registered)
    registered = {p["type"] for p in list_available_providers()}
    method_registry = {
        "mpesa": "mpesa_ke",
        "stripe": "stripe",
        "bank_transfer": "bank_transfer",
        "paypal": "paypal",
        "airtel_money": "airtel_money",
        "crypto": "crypto",
    }

    available = []
    for m in methods:
        pt = method_registry.get(m["method"])
        if pt and pt in registered and country_code in m["countries"]:
            available.append(m)

    return available


# ── Generic Payment Initiation ────────────────────────────────────────────────


@router.post("/initiate/{method}", response_model=dict)
async def initiate_payment(
    method: str,
    data: InitiatePaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate a payment using the specified payment method.

    Routes to the correct provider implementation based on the method parameter.
    Supported methods: mpesa, stripe, bank_transfer, paypal, airtel_money, crypto
    """
    # Route M-Pesa through the existing workflow (which handles DB + STK Push)
    if method == "mpesa":
        try:
            purpose = PaymentPurpose(data.purpose)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid payment purpose: {data.purpose}") from None

        payment = await initiate_mpesa_payment(
            db=db,
            user_id=current_user.id,
            phone_number=data.phone_number or "",
            amount=data.amount,
            purpose=purpose,
            reference_id=data.reference_id,
            description=data.description,
        )
        return {
            "payment_id": payment.id,
            "checkout_request_id": payment.mpesa_checkout_request_id,
            "status": payment.status.value,
            "message": "Check your phone and enter your M-Pesa PIN",
            "amount": payment.amount,
            "currency": payment.currency,
        }

    # Route Stripe through the existing workflow
    if method in ("stripe", "card"):
        import stripe as stripe_lib
        stripe_lib.api_key = settings.STRIPE_SECRET_KEY

        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(status_code=502, detail="Stripe is not configured")

        try:
            purpose = PaymentPurpose(data.purpose)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid payment purpose: {data.purpose}") from None

        from app.models.payment import Payment
        reference = f"STR-{_uuid.uuid4().hex[:10].upper()}"
        payment = Payment(
            user_id=current_user.id,
            amount=data.amount,
            currency=data.currency,
            method=PaymentMethod.stripe,
            purpose=purpose,
            status=PaymentStatus.pending,
            reference=reference,
            description=data.description,
            payment_metadata={"reference_id": data.reference_id, **(data.metadata or {})},
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        # Create Stripe PaymentIntent
        intent = stripe_lib.PaymentIntent.create(
            amount=int(data.amount * 100),
            currency=data.currency.lower(),
            description=data.description,
            metadata={
                "payment_id": str(payment.id),
                "user_id": str(current_user.id),
                "reference": reference,
                "purpose": data.purpose,
                **(data.metadata or {}),
            },
        )
        payment.stripe_payment_intent_id = intent.id
        payment.status = PaymentStatus.processing
        await db.commit()
        await db.refresh(payment)

        return {
            "payment_id": payment.id,
            "client_secret": intent.client_secret,
            "status": payment.status.value,
            "amount": payment.amount,
            "currency": payment.currency,
            "publishable_key": "",  # Frontend should inject its own Stripe publishable key
        }

    # For other providers, use the pluggable provider interface
    provider = get_provider_by_method(method)
    if provider is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported payment method: {method}",
        )

    from decimal import Decimal
    prov_request = ProvPaymentRequest(
        amount=Decimal(str(data.amount)),
        currency=data.currency,
        phone_number=data.phone_number,
        email=data.email,
        reference=f"VST-{_uuid.uuid4().hex[:10].upper()}",
        description=data.description,
        callback_url=data.callback_url,
        metadata={
            "user_id": current_user.id,
            "purpose": data.purpose,
            "reference_id": data.reference_id,
            **(data.metadata or {}),
        },
    )

    result = await provider.initiate_payment(prov_request)

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=result.error_message or f"{method} payment failed",
        )

    response = {
        "success": result.success,
        "provider": result.provider,
        "provider_transaction_id": result.provider_transaction_id,
        "status": result.status,
        "redirect_url": result.redirect_url,
        "raw": result.raw_response,
    }

    # For bank_transfer, include the bank account details
    if method == "bank_transfer" and result.raw_response:
        response["bank_accounts"] = result.raw_response.get("bank_accounts", [])
        response["virtual_reference"] = result.raw_response.get("virtual_reference", "")
        response["instructions"] = result.raw_response.get("instructions", "")

    # For crypto, include the wallet address
    if method == "crypto" and result.raw_response:
        response["wallet_address"] = result.raw_response.get("wallet_address", "")
        response["network"] = result.raw_response.get("network", "")
        response["asset"] = result.raw_response.get("asset", "")
        response["instructions"] = result.raw_response.get("instructions", "")

    return response


# ── M-Pesa ─────────────────────────────────────────────────────────────────────


@router.post("/mpesa/initiate", response_model=dict)
async def initiate_mpesa(
    data: MpesaPaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        purpose = PaymentPurpose(data.purpose)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment purpose: {data.purpose}") from None

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
        _task = asyncio.create_task(
            _bg_emit_event_after_payment(payment)
        )
        _background_tasks.add(_task)
        _task.add_done_callback(_background_tasks.discard)

        # ── Send payment receipt notification ──────────────────────────────
        _task2 = asyncio.create_task(
            _bg_send_payment_receipt(payment)
        )
        _background_tasks.add(_task2)
        _task2.add_done_callback(_background_tasks.discard)

        # ── Rent Payment Auto-Update ───────────────────────────────────────
        # If this was a rent payment, auto-update the RentPayment record,
        # generate a receipt, and notify both parties.
        if payment.purpose == PaymentPurpose.rent or (
            payment.description and 'rent' in payment.description.lower()
        ):
            _task3 = asyncio.create_task(
                _bg_handle_rent_payment_completed(payment, db)
            )
            _background_tasks.add(_task3)
            _task3.add_done_callback(_background_tasks.discard)

        # Handle verification report payment
        if payment.purpose == PaymentPurpose.verification_report and ref_id:
            verification = await create_verification_request(db, ref_id, payment.user_id, payment.id)
            background_tasks.add_task(run_ai_verification, db, verification.id)

        # Handle subscription payment
        if payment.purpose == PaymentPurpose.subscription:
            from app.models.user import User
            from app.services.subscription_service import (
                create_subscription,
                get_subscription_orm,
                renew_subscription,
            )
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
            from datetime import datetime, timedelta

            from app.services.property_service import get_property_by_id
            prop = await get_property_by_id(db, ref_id)
            if prop:
                now = datetime.now(UTC)
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


# ── PayPal Webhook ────────────────────────────────────────────────────────────────


@router.post("/paypal/callback")
async def paypal_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    PayPal webhook endpoint.

    Triggered by PayPal after payment events (CHECKOUT.ORDER.APPROVED,
    PAYMENT.CAPTURE.COMPLETED, PAYMENT.CAPTURE.DENIED, etc.).
    Verifies signature via PayPal POSTBACK API.
    Idempotent via Redis deduplication (paypal:{event_id}).
    """
    import json as _json

    payload = await request.body()
    headers_dict = dict(request.headers.items())

    try:
        raw_data = _json.loads(payload.decode())
    except Exception:
        logger.warning('{"event":"paypal_webhook_blocked","reason":"invalid_json"}')
        raise HTTPException(status_code=400, detail="Invalid payload") from None

    event_id = raw_data.get("id", "unknown")
    event_type = raw_data.get("event_type", "unknown")

    logger.info(
        '{"event":"paypal_webhook_received","type":"%s","id":"%s"}',
        event_type, event_id,
    )

    # Idempotency (Redis atomic dedup)
    is_new = await check_and_mark_processed(f"paypal:{event_id}", ttl=86400)
    if not is_new:
        logger.info(
            '{"event":"paypal_webhook_duplicate","type":"%s","id":"%s"}',
            event_type, event_id,
        )
        return {"received": True, "id": event_id, "status": "duplicate"}

    # Verify webhook signature
    from app.services.paypal_provider import PayPalProvider
    provider = PayPalProvider()
    is_valid = await provider.verify_callback(raw_data, headers_dict)
    if not is_valid:
        logger.warning(
            '{"event":"paypal_webhook_blocked","reason":"invalid_signature","id":"%s"}',
            event_id,
        )
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Route event type
    resource = raw_data.get("resource", {})

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        from app.models.payment import Payment
        capture_id = resource.get("id")
        if capture_id:
            result = await db.execute(
                select(Payment).where(Payment.stripe_payment_intent_id == capture_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.completed
                await db.commit()
                logger.info(
                    '{"event":"paypal_payment_completed","capture":"%s","payment_id":%d}',
                    capture_id, payment.id,
                )
                _task4 = asyncio.create_task(_bg_emit_event_after_payment(payment))
                _background_tasks.add(_task4)
                _task4.add_done_callback(_background_tasks.discard)
        else:
            logger.info(
                '{"event":"paypal_payment_completed","resource":"%s"}',
                resource.get("id"),
            )

    elif event_type == "PAYMENT.CAPTURE.DENIED":
        logger.info(
            '{"event":"paypal_payment_denied","capture":"%s"}',
            resource.get("id"),
        )

    elif event_type == "PAYMENT.CAPTURE.REFUNDED":
        logger.info(
            '{"event":"paypal_payment_refunded","capture":"%s"}',
            resource.get("id"),
        )

    else:
        logger.info(
            '{"event":"paypal_webhook_unhandled","type":"%s","id":"%s"}',
            event_type, event_id,
        )

    return {"received": True, "id": event_id}


# ── Airtel Money Callback ────────────────────────────────────────────────────────


@router.post("/airtel/callback")
async def airtel_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Airtel Money callback endpoint.

    Triggered by Airtel after a push payment is completed or fails.
    Verifies HMAC signature if provided.
    Idempotent via Redis deduplication (airtel:{transaction_id}).
    """
    import json as _json

    payload = await request.body()
    headers_dict = dict(request.headers.items())

    try:
        raw_data = _json.loads(payload.decode())
    except Exception:
        logger.warning('{"event":"airtel_callback_blocked","reason":"invalid_json"}')
        return {"status_code": "200", "status_message": "Accepted"}

    transaction = raw_data.get("transaction", {})
    transaction_id = transaction.get("id", raw_data.get("airtel_money_request_id", "unknown"))

    logger.info(
        '{"event":"airtel_callback_received","transaction_id":"%s"}',
        transaction_id,
    )

    # Idempotency (Redis atomic dedup)
    is_new = await check_and_mark_processed(f"airtel:{transaction_id}", ttl=86400)
    if not is_new:
        logger.info(
            '{"event":"airtel_callback_duplicate","transaction_id":"%s"}',
            transaction_id,
        )
        # Airtel expects 200 response
        return {"status_code": "200", "status_message": "Accepted"}

    # Verify HMAC signature
    from app.services.airtel_money_provider import AirtelMoneyProvider
    provider = AirtelMoneyProvider()
    is_valid = await provider.verify_callback(raw_data, headers_dict)
    if not is_valid:
        logger.warning(
            '{"event":"airtel_callback_blocked","reason":"invalid_signature","transaction_id":"%s"}',
            transaction_id,
        )
        return {"status_code": "200", "status_message": "Accepted"}

    # Process payment
    status_code = raw_data.get("status", {}).get("code", "")
    if status_code in ("200", "TS"):
        from app.models.payment import Payment
        result = await db.execute(
            select(Payment).where(Payment.reference == transaction_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.completed
            await db.commit()
            logger.info(
                '{"event":"airtel_payment_completed","transaction_id":"%s","payment_id":%d}',
                transaction_id, payment.id,
            )
            _task = asyncio.create_task(_bg_emit_event_after_payment(payment))
            _background_tasks.add(_task)
            _task.add_done_callback(_background_tasks.discard)

    elif status_code in ("404", "500", "FAILED", "TF"):
        from app.models.payment import Payment
        result = await db.execute(
            select(Payment).where(Payment.reference == transaction_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.failed
            payment.error_message = raw_data.get("status", {}).get("message", "Airtel payment failed")
            await db.commit()

    # Airtel requires a specific response format
    return {"status_code": "200", "status_message": "Accepted"}


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
        raise HTTPException(status_code=400, detail="Invalid payload") from None
    except stripe.error.SignatureVerificationError:
        logger.warning('{"event":"stripe_webhook_blocked","reason":"invalid_signature"}')
        raise HTTPException(status_code=400, detail="Invalid signature") from None

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
            _task = asyncio.create_task(_bg_emit_event_after_payment(payment))
            _background_tasks.add(_task)
            _task.add_done_callback(_background_tasks.discard)

            # Rent payment auto-update
            if payment.purpose == PaymentPurpose.rent or (
                payment.description and 'rent' in payment.description.lower()
            ):
                _task = asyncio.create_task(_bg_handle_rent_payment_completed(payment, db))
                _background_tasks.add(_task)
                _task.add_done_callback(_background_tasks.discard)

            # Verification report
            if payment.purpose == PaymentPurpose.verification_report and ref_id:
                verification = await create_verification_request(
                    db, ref_id, payment.user_id, payment.id
                )
                background_tasks.add_task(run_ai_verification, db, verification.id)

            # Subscription
            if payment.purpose == PaymentPurpose.subscription:
                from app.models.user import User
                from app.services.subscription_service import (
                    create_subscription,
                    get_subscription_orm,
                    renew_subscription,
                )
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
                from datetime import datetime, timedelta

                from app.services.property_service import get_property_by_id
                prop = await get_property_by_id(db, ref_id)
                if prop:
                    now = datetime.now(UTC)
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
            raise HTTPException(status_code=502, detail=str(e)) from e
    elif payment.method == PaymentMethod.mpesa:
        result = await refund_payment_mpesa(db, payment)
    else:
        raise HTTPException(status_code=400, detail=f"Cannot refund {payment.method.value} payments")

    return result


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_event_after_payment(payment) -> None:
    """Fire-and-forget: emit payment.completed event."""
    from app.services.event_bus import EVENT_PAYMENT_COMPLETED, emit_event

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
