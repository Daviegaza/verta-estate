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
