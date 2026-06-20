import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentPurpose
from app.services.mpesa_service import initiate_stk_push, parse_mpesa_callback


VERIFICATION_REPORT_PRICE = 500.0   # KES
AGENT_BADGE_MONTHLY_PRICE = 5000.0  # KES


async def initiate_mpesa_payment(
    db: AsyncSession,
    user_id: int,
    phone_number: str,
    amount: float,
    purpose: PaymentPurpose,
    reference_id: Optional[int] = None,
    description: str = "Vestra Payment",
) -> Payment:
    reference = f"VST-{uuid.uuid4().hex[:10].upper()}"

    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency="KES",
        method=PaymentMethod.mpesa,
        purpose=purpose,
        status=PaymentStatus.pending,
        phone_number=phone_number,
        reference=reference,
        description=description,
        payment_metadata={"reference_id": reference_id},
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    try:
        mpesa_response = await initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=reference,
            transaction_desc=description[:13],
        )

        if mpesa_response.get("ResponseCode") == "0":
            payment.mpesa_checkout_request_id = mpesa_response.get("CheckoutRequestID")
            payment.mpesa_merchant_request_id = mpesa_response.get("MerchantRequestID")
            payment.status = PaymentStatus.processing
        else:
            payment.status = PaymentStatus.failed
            payment.error_message = mpesa_response.get("errorMessage", "STK Push failed")

    except Exception as e:
        payment.status = PaymentStatus.failed
        payment.error_message = str(e)

    await db.commit()
    await db.refresh(payment)

    # ── Fire analytics event: payment_initiated ────────────────────────────
    import asyncio
    from app.services.analytics_service import fire_and_forget_track_user_event

    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=user_id,
            event_type="payment_initiated",
            event_data={
                "payment_id": payment.id,
                "amount": amount,
                "purpose": purpose.value if purpose else None,
                "status": payment.status.value,
            },
        )
    )

    return payment


async def handle_mpesa_callback(db: AsyncSession, callback_data: dict) -> Optional[Payment]:
    parsed = parse_mpesa_callback(callback_data)
    checkout_id = parsed.get("checkout_request_id")
    if not checkout_id:
        return None

    result = await db.execute(
        select(Payment).where(Payment.mpesa_checkout_request_id == checkout_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return None

    if parsed.get("success"):
        payment.status = PaymentStatus.completed
        payment.mpesa_receipt_number = parsed.get("mpesa_receipt_number")
    else:
        payment.status = PaymentStatus.failed
        payment.error_message = parsed.get("result_desc")

    await db.commit()
    await db.refresh(payment)

    # ── Fire analytics event: payment_completed / payment_failed ─────────
    import asyncio
    from app.services.analytics_service import fire_and_forget_track_user_event

    event_type = "payment_completed" if parsed.get("success") else "payment_failed"
    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=payment.user_id,
            event_type=event_type,
            event_data={
                "payment_id": payment.id,
                "amount": float(payment.amount),
                "purpose": payment.purpose.value if payment.purpose else None,
                "mpesa_receipt": payment.mpesa_receipt_number,
            },
        )
    )

    return payment


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def get_payment_by_checkout_id(
    db: AsyncSession, checkout_id: str
) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.mpesa_checkout_request_id == checkout_id)
    )
    return result.scalar_one_or_none()


async def get_total_revenue(db: AsyncSession) -> float:
    result = await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.completed)
    )
    val = result.scalar_one()
    return float(val) if val else 0.0


async def get_user_payments(db: AsyncSession, user_id: int) -> list:
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )
    return result.scalars().all()


async def get_monthly_revenue_stats(db: AsyncSession) -> list:
    """Monthly revenue for last 6 months."""
    from datetime import datetime
    result = await db.execute(
        select(
            func.date_trunc('month', Payment.created_at).label('month'),
            func.sum(Payment.amount).label('revenue'),
            func.count(Payment.id).label('count')
        ).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= func.date_trunc('month', func.now()) - func.make_interval(0, 6)
        ).group_by('month').order_by('month')
    )
    data = {}
    for row in result.all():
        label = row.month.strftime('%b')
        data[label] = {"revenue": round(float(row.revenue or 0), 0), "count": row.count}

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    now = datetime.utcnow()
    months = []
    for i in range(5, -1, -1):
        label = month_names[(now.month - 1 - i) % 12]
        entry = data.get(label, {"revenue": 0, "count": 0})
        months.append({"month": label, "revenue": entry["revenue"], "count": entry["count"]})
    return months


# ── Stripe Payment Processing ──────────────────────────────────────────────────


async def process_stripe_payment_intent(
    db: AsyncSession,
    payment_intent: dict,
) -> Optional[Payment]:
    """Create or update a Payment record from a Stripe PaymentIntent webhook event."""
    pi_id = payment_intent.get("id")
    if not pi_id:
        return None

    # Check if already exists (idempotency)
    result = await db.execute(
        select(Payment).where(Payment.stripe_payment_intent_id == pi_id)
    )
    payment = result.scalar_one_or_none()

    amount = float(payment_intent.get("amount", 0)) / 100  # Stripe amounts in cents
    currency = payment_intent.get("currency", "usd").upper()
    status = payment_intent.get("status")
    metadata = payment_intent.get("metadata", {}) or {}
    charges_data = payment_intent.get("charges", {}).get("data", [{}])
    charge_id = charges_data[0].get("id") if charges_data else None

    if payment:
        # Update existing record
        if status == "succeeded":
            payment.status = PaymentStatus.completed
            if charge_id:
                payment.stripe_charge_id = charge_id
        elif status in ("failed", "requires_payment_method"):
            payment.status = PaymentStatus.failed
            last_error = payment_intent.get("last_payment_error", {}) or {}
            payment.error_message = last_error.get("message", "Stripe payment failed")
        await db.commit()
        await db.refresh(payment)
        return payment

    # Create new payment record
    purpose_str = metadata.get("purpose", "verification_report")
    try:
        purpose = PaymentPurpose(purpose_str)
    except ValueError:
        purpose = PaymentPurpose.verification_report

    user_id = int(metadata.get("user_id", 0))
    if not user_id:
        logger.warning('{"event":"stripe_payment_no_user","pi":"%s"}', pi_id)
        return None

    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        method=PaymentMethod.stripe,
        purpose=purpose,
        status=PaymentStatus.completed if status == "succeeded" else PaymentStatus.processing,
        stripe_payment_intent_id=pi_id,
        stripe_charge_id=charge_id,
        reference=metadata.get("reference", f"STR-{pi_id[-10:]}"),
        description=metadata.get("description", "Stripe payment"),
        payment_metadata=metadata,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    logger.info(
        '{"event":"stripe_payment_created","payment_id":%d,"pi":"%s","amount":%f,"currency":"%s"}',
        payment.id, pi_id, amount, currency,
    )
    return payment


async def refund_payment_stripe(db: AsyncSession, payment: Payment) -> dict:
    """Process a refund for a Stripe payment via the Stripe API."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not payment.stripe_payment_intent_id:
        raise ValueError("No Stripe PaymentIntent ID found for this payment")

    try:
        refund = stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent_id,
        )
        payment.status = PaymentStatus.refunded
        payment.error_message = f"Refunded via Stripe: {refund.id}"
        await db.commit()

        logger.info(
            '{"event":"stripe_refund_processed","payment_id":%d,"refund_id":"%s","amount":%f}',
            payment.id, refund.id, float(payment.amount),
        )
        return {
            "message": f"Payment #{payment.id} refunded via Stripe",
            "refund_id": refund.id,
            "amount": float(payment.amount),
        }
    except Exception as e:
        logger.error(
            '{"event":"stripe_refund_failed","payment_id":%d,"error":"%s"}',
            payment.id, str(e),
        )
        raise ValueError(f"Stripe refund failed: {str(e)}")


async def refund_payment_mpesa(db: AsyncSession, payment: Payment) -> dict:
    """Mark an M-Pesa payment for manual refund processing.
    M-Pesa does not expose a customer-facing refund API for STK Push.
    The finance team must process a B2C reversal manually.
    """
    payment.status = PaymentStatus.refunded
    payment.error_message = "Refund requires manual M-Pesa B2C reversal"
    await db.commit()

    logger.info(
        '{"event":"mpesa_refund_marked","payment_id":%d,"amount":%f,"phone":"%s"}',
        payment.id, float(payment.amount), payment.phone_number,
    )
    return {
        "message": f"Payment #{payment.id} marked as refunded. Manual M-Pesa reversal required.",
        "payment_id": payment.id,
        "amount": float(payment.amount),
        "phone": payment.phone_number,
        "note": "Contact the finance team to process M-Pesa B2C reversal.",
    }


# ── Revenue Analytics ──────────────────────────────────────────────────────────


async def get_revenue_summary(db: AsyncSession) -> dict:
    """Aggregated revenue: total, this month, today, projected, growth rate."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)

    # Total all-time completed revenue
    total = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.completed)
    )).scalar_one() or 0.0)

    # This month
    this_month = float((await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= first_of_month,
        )
    )).scalar_one() or 0.0)

    # Today
    today = float((await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= today_start,
        )
    )).scalar_one() or 0.0)

    # Last month
    last_month_total = float((await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= last_month_start,
            Payment.created_at < first_of_month,
        )
    )).scalar_one() or 0.0)

    # Projected monthly
    days_elapsed = max(1, (now - first_of_month).days + 1)
    projected = (this_month / days_elapsed) * 30

    # Growth rate vs last month
    growth_rate = 0.0
    if last_month_total > 0:
        growth_rate = round(((this_month - last_month_total) / last_month_total) * 100, 1)

    return {
        "total_revenue": round(total, 2),
        "this_month": round(this_month, 2),
        "today": round(today, 2),
        "projected_monthly": round(projected, 2),
        "growth_rate": growth_rate,
        "last_month": round(last_month_total, 2),
        "currency": "KES",
    }


async def get_revenue_by_purpose(db: AsyncSession) -> list[dict]:
    """Revenue breakdown by PaymentPurpose."""
    result = await db.execute(
        select(
            Payment.purpose,
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("count"),
        ).where(
            Payment.status == PaymentStatus.completed,
        ).group_by(Payment.purpose)
        .order_by(func.sum(Payment.amount).desc())
    )
    rows = result.all()
    total = sum(float(r.revenue or 0) for r in rows) or 1
    return [
        {
            "purpose": r.purpose.value if hasattr(r.purpose, "value") else str(r.purpose),
            "revenue": round(float(r.revenue or 0), 2),
            "count": r.count,
            "percentage": round((float(r.revenue or 0) / total) * 100, 1),
        }
        for r in rows
    ]


async def get_revenue_by_method(db: AsyncSession) -> list[dict]:
    """Revenue breakdown by PaymentMethod (mpesa, stripe, bank)."""
    result = await db.execute(
        select(
            Payment.method,
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("count"),
        ).where(
            Payment.status == PaymentStatus.completed,
        ).group_by(Payment.method)
        .order_by(func.sum(Payment.amount).desc())
    )
    rows = result.all()
    total = sum(float(r.revenue or 0) for r in rows) or 1
    return [
        {
            "method": r.method.value if hasattr(r.method, "value") else str(r.method),
            "revenue": round(float(r.revenue or 0), 2),
            "count": r.count,
            "percentage": round((float(r.revenue or 0) / total) * 100, 1),
        }
        for r in rows
    ]


async def get_daily_revenue(db: AsyncSession, days: int = 30) -> list[dict]:
    """Daily revenue for last N days with zero-fill for missing days."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", Payment.created_at).label("day"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("count"),
        ).where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= start,
        ).group_by(func.date_trunc("day", Payment.created_at))
        .order_by(func.date_trunc("day", Payment.created_at))
    )

    daily_map = {}
    for row in result.all():
        label = row.day.strftime("%Y-%m-%d")
        daily_map[label] = {
            "revenue": round(float(row.revenue or 0), 2),
            "count": row.count,
        }

    entries = []
    for i in range(days, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        entry = daily_map.get(day, {"revenue": 0.0, "count": 0})
        entries.append({"date": day, **entry})
    return entries


async def get_revenue_reconciliation(db: AsyncSession) -> dict:
    """Compare actual completed-payment sums with expected revenue."""
    # Gross (all non-refunded)
    gross = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status != PaymentStatus.refunded)
    )).scalar_one() or 0.0)

    # Actual captured
    actual = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.completed)
    )).scalar_one() or 0.0)

    # Refunded
    refunded = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.refunded)
    )).scalar_one() or 0.0)

    # Pending
    pending = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.pending)
    )).scalar_one() or 0.0)

    # Processing
    processing = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.processing)
    )).scalar_one() or 0.0)

    # Failed
    failed = float((await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.failed)
    )).scalar_one() or 0.0)

    total_count = (await db.execute(select(func.count(Payment.id)))).scalar_one()
    completed_count = (await db.execute(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.completed)
    )).scalar_one()

    expected = round(gross - refunded - pending - processing - failed, 2)
    is_balanced = abs(expected - actual) < 1.0

    return {
        "gross_revenue": round(gross, 2),
        "actual_revenue": round(actual, 2),
        "refunded": round(refunded, 2),
        "pending": round(pending, 2),
        "processing": round(processing, 2),
        "failed": round(failed, 2),
        "expected_revenue": expected,
        "total_transactions": total_count,
        "completed_transactions": completed_count,
        "difference": round(expected - actual, 2),
        "reconciled": is_balanced,
        "currency": "KES",
    }
