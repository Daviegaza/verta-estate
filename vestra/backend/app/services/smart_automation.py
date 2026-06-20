"""
VESTRA Smart Automation Engine
===============================
Handles all automatic workflows across every role:

Buyer:    Price alerts, saved search matches, escrow updates, AI recommendations
Seller:   View/inquiry alerts, price optimization, listing expiry reminders
Landlord: Auto rent collection, late fees, tenant reminders, lease expiry
Tenant:   Rent due reminders, auto-receipts, payment confirmations
Agent:    Lead tracking, commission auto-calc, inquiry notifications
Admin:    System health alerts, fraud detection alerts

Design principle: ZERO manual intervention. Everything that can be
automated IS automated. Money flows, receipts generate, notifications
fire — without anyone clicking a button.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.models.rental import RentPayment, RentPaymentStatus, RentalUnit, Tenant, Lease, LeaseStatus
from app.models.payment import Payment, PaymentStatus, PaymentPurpose
from app.models.user import User, UserRole

logger = logging.getLogger("vestra")

LATE_FEE_PER_DAY_KES = 100
LATE_FEE_MAX_KES = 3000


# ═══════════════════════════════════════════════════════════════════════════════
# RENT PAYMENT — Auto-update on M-Pesa callback
# ═══════════════════════════════════════════════════════════════════════════════

async def auto_update_rent_on_payment(
    db: AsyncSession,
    payment: Payment,
) -> Optional[dict]:
    """
    When a rent M-Pesa payment completes:
    1. Find the matching RentPayment record for this month
    2. Mark it as paid
    3. Generate receipt
    4. Notify landlord: "Rent Paid!"
    5. Notify tenant: "Receipt Ready"

    Returns summary dict for event bus.
    """
    if payment.purpose != PaymentPurpose.rent and 'rent' not in (payment.description or '').lower():
        return None

    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    # Find the tenant associated with the paying phone number
    phone = payment.phone_number
    if not phone:
        return None

    result = await db.execute(
        select(Tenant)
        .options(joinedload(Tenant.unit).joinedload(RentalUnit.landlord))
        .where(Tenant.phone == phone, Tenant.is_active == True)
        .limit(1)
    )
    tenant = result.unique().scalar_one_or_none()
    if not tenant:
        logger.info('{"event":"rent_auto_update_no_tenant","phone":"%s"}', phone)
        return None

    unit = tenant.unit
    landlord = unit.landlord if unit else None

    # Find or create the RentPayment for this month
    result = await db.execute(
        select(RentPayment).where(
            RentPayment.tenant_id == tenant.id,
            RentPayment.month == month,
        )
    )
    rent_bill = result.scalar_one_or_none()

    if not rent_bill:
        # Auto-create the bill
        lease = tenant.lease
        rent_amount = float(lease.monthly_rent_kes) if lease else float(unit.monthly_rent_kes or 0)
        rent_bill = RentPayment(
            tenant_id=tenant.id,
            unit_id=unit.id,
            lease_id=lease.id if lease else None,
            amount_kes=rent_amount,
            amount_paid_kes=float(payment.amount),
            status=RentPaymentStatus.paid,
            due_date=now.replace(day=tenant.rent_due_day or 1),
            paid_date=now,
            month=month,
            mpesa_receipt=payment.mpesa_receipt_number or payment.reference or '',
            payment_id=payment.id,
        )
        db.add(rent_bill)
    else:
        # Update existing bill
        rent_bill.amount_paid_kes = float(payment.amount)
        rent_bill.status = RentPaymentStatus.paid
        rent_bill.paid_date = now
        rent_bill.mpesa_receipt = payment.mpesa_receipt_number or payment.reference or ''
        rent_bill.payment_id = payment.id

    await db.commit()
    await db.refresh(rent_bill)

    # ── Generate Receipt ───────────────────────────────────────────────────
    receipt_data = {
        "receipt_number": f"RCP-{rent_bill.id:06d}",
        "tenant_name": tenant.full_name,
        "tenant_phone": tenant.phone,
        "unit_name": unit.name,
        "building": unit.building_name or unit.address,
        "amount_paid": float(payment.amount),
        "rent_amount": float(rent_bill.amount_kes),
        "late_fee": float(rent_bill.late_fee_kes or 0),
        "month": month,
        "paid_date": now.strftime("%d %B %Y at %H:%M"),
        "mpesa_ref": payment.mpesa_receipt_number or '',
        "landlord_name": landlord.full_name if landlord else 'Landlord',
    }

    # ── Notify Landlord ────────────────────────────────────────────────────
    if landlord:
        await send_notification(
            db,
            user_id=landlord.id,
            title="💰 Rent Paid!",
            body=f"{tenant.full_name} paid KES {float(payment.amount):,.0f} for {unit.name} — {month}",
            notification_type="rent_paid",
            action_url=f"/dashboard/landlord",
        )

    # ── Notify Tenant (Receipt Ready) ─────────────────────────────────────
    # Find the tenant's Vestra user account by phone
    result = await db.execute(
        select(User).where(User.phone == tenant.phone).limit(1)
    )
    tenant_user = result.scalar_one_or_none()
    if tenant_user:
        await send_notification(
            db,
            user_id=tenant_user.id,
            title="✅ Payment Confirmed",
            body=f"Your rent of KES {float(payment.amount):,.0f} for {unit.name} has been received. Receipt #RCP-{rent_bill.id:06d}",
            notification_type="rent_receipt",
            action_url=f"/dashboard/tenant",
        )

    logger.info(
        '{"event":"rent_auto_updated","tenant":"%s","amount":%f,"receipt":"RCP-%06d"}',
        tenant.full_name, float(payment.amount), rent_bill.id
    )

    return receipt_data


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-REMINDERS — Rent Due, Lease Expiry
# ═══════════════════════════════════════════════════════════════════════════════

async def send_rent_due_reminders(db: AsyncSession) -> dict:
    """
    Send reminders to tenants whose rent is due in 3 days.
    Should be called by a daily cron/scheduler.
    """
    now = datetime.now(timezone.utc)
    reminder_date = now + timedelta(days=3)
    due_day = reminder_date.day
    month = now.strftime("%Y-%m")

    result = await db.execute(
        select(Tenant)
        .options(joinedload(Tenant.unit), joinedload(Tenant.lease))
        .where(Tenant.is_active == True, Tenant.rent_due_day == due_day)
    )
    tenants = result.unique().scalars().all()

    sent = 0
    for tenant in tenants:
        unit = tenant.unit
        if not unit or not unit.is_occupied:
            continue

        # Check if already paid this month
        result = await db.execute(
            select(RentPayment).where(
                RentPayment.tenant_id == tenant.id,
                RentPayment.month == month,
                RentPayment.status == RentPaymentStatus.paid,
            )
        )
        if result.scalar_one_or_none():
            continue

        rent = float(tenant.lease.monthly_rent_kes) if tenant.lease else float(unit.monthly_rent_kes or 0)

        # Notify tenant via app + WhatsApp
        user_result = await db.execute(
            select(User).where(User.phone == tenant.phone).limit(1)
        )
        user = user_result.scalar_one_or_none()
        if user:
            await send_notification(
                db, user_id=user.id,
                title="📅 Rent Due in 3 Days",
                body=f"Your rent of KES {rent:,.0f} for {unit.name} is due on {reminder_date.strftime('%d %B')}. Pay now to avoid late fees.",
                notification_type="rent_reminder",
                action_url="/dashboard/tenant/rent",
            )

        # Try WhatsApp reminder
        try:
            from app.services.whatsapp_service import send_whatsapp_message
            await send_whatsapp_message(
                to_phone=tenant.phone,
                message=f"🏠 *Rent Reminder from Vestra*\n\n"
                        f"Your rent of *KES {rent:,.0f}* for *{unit.name}* is due in 3 days "
                        f"({reminder_date.strftime('%d %B')}).\n\n"
                        f"Pay now via M-Pesa to avoid a late fee of KES {LATE_FEE_PER_DAY_KES}/day.\n\n"
                        f"Thank you! — Vestra",
            )
        except Exception:
            pass  # WhatsApp may not be configured

        sent += 1

    return {"reminders_sent": sent, "month": month}


async def send_lease_expiry_alerts(db: AsyncSession) -> dict:
    """Alert landlords about leases expiring within 30 days."""
    now = datetime.now(timezone.utc)
    expiry_threshold = now + timedelta(days=30)

    result = await db.execute(
        select(Lease)
        .options(joinedload(Lease.unit).joinedload(RentalUnit.landlord))
        .options(joinedload(Lease.tenant))
        .where(
            Lease.status == LeaseStatus.active,
            Lease.end_date <= expiry_threshold,
            Lease.end_date > now,
        )
    )
    leases = result.unique().scalars().all()

    alerted = 0
    for lease in leases:
        unit = lease.unit
        landlord = unit.landlord if unit else None
        tenant = lease.tenant
        days_left = (lease.end_date - now).days

        if landlord:
            await send_notification(
                db, user_id=landlord.id,
                title="⚠️ Lease Expiring Soon",
                body=f"Lease for {tenant.full_name if tenant else 'tenant'} in {unit.name} expires in {days_left} days. Consider renewal.",
                notification_type="lease_expiry",
                action_url=f"/dashboard/landlord/tenants",
            )

            # Auto-mark lease as expiring_soon
            if days_left <= 14:
                lease.status = LeaseStatus.expiring_soon
                await db.commit()

        alerted += 1

    return {"leases_expiring": alerted}


# ═══════════════════════════════════════════════════════════════════════════════
# BUYER AUTOMATION — Price Alerts, Saved Search Matches
# ═══════════════════════════════════════════════════════════════════════════════

async def send_price_drop_alerts(db: AsyncSession, property_id: int, old_price: float, new_price: float) -> int:
    """Alert buyers who saved this property that the price dropped."""
    if new_price >= old_price:
        return 0

    from app.models.kyc_notification import SavedProperty as SP

    result = await db.execute(
        select(SP).where(SP.property_id == property_id)
    )
    saved = result.scalars().all()

    sent = 0
    for s in saved:
        drop_pct = round((1 - new_price / old_price) * 100) if old_price > 0 else 0
        await send_notification(
            db, user_id=s.user_id,
            title="📉 Price Drop Alert!",
            body=f"A property you saved dropped {drop_pct}% — from KES {old_price:,.0f} to KES {new_price:,.0f}",
            notification_type="price_drop",
            action_url=f"/properties/{property_id}",
        )
        sent += 1

    return sent


async def match_saved_searches(db: AsyncSession, property_id: int) -> int:
    """Check if a new/updated property matches any saved searches and notify users."""
    from app.models.kyc_notification import SavedSearch
    from app.models.property import Property

    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        return 0

    result = await db.execute(
        select(SavedSearch).where(SavedSearch.notify_email == True)
    )
    searches = result.scalars().all()

    sent = 0
    for search in searches:
        filters = search.filters or {}
        # Simple matching
        if filters.get('city') and filters['city'].lower() != (prop.city or '').lower():
            continue
        if filters.get('property_type') and filters['property_type'] != prop.property_type.value if prop.property_type else None:
            continue

        await send_notification(
            db, user_id=search.user_id,
            title="🔍 New Match Found",
            body=f"A new property matches your saved search: {prop.title} in {prop.city}",
            notification_type="saved_search_match",
            action_url=f"/properties/{property_id}",
        )
        sent += 1

    return sent


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT AUTOMATION — Lead Tracking, Commission Calc
# ═══════════════════════════════════════════════════════════════════════════════

async def notify_agent_on_inquiry(db: AsyncSession, property_id: int, inquiry_count: int) -> None:
    """Notify the agent when their listing gets a new inquiry."""
    result = await db.execute(
        select(Property).options(joinedload(Property.owner)).where(Property.id == property_id)
    )
    prop = result.unique().scalar_one_or_none()
    if not prop or not prop.owner:
        return

    owner = prop.owner
    if owner.role.value not in ('agent', 'seller'):
        return

    await send_notification(
        db, user_id=owner.id,
        title="🔔 New Inquiry!",
        body=f"Your listing '{prop.title}' now has {inquiry_count} inquiries. Check your leads.",
        notification_type="new_inquiry",
        action_url=f"/dashboard/{owner.role.value}/leads" if owner.role.value == 'agent' else f"/properties/{property_id}",
    )


async def auto_calculate_commission(db: AsyncSession, agent_id: int, deal_amount: float) -> float:
    """Calculate and track agent commission (default 3% for standard agents)."""
    from app.models.property import Property as PropModel

    # Find agent's listings to determine commission rate
    result = await db.execute(
        select(PropModel).where(PropModel.owner_id == agent_id, PropModel.status == 'sold')
    )
    sold_count = len(result.scalars().all())

    # Tiered commission: 3% basic, 4% after 10 deals, 5% after 25 deals
    if sold_count >= 25:
        rate = 0.05
    elif sold_count >= 10:
        rate = 0.04
    else:
        rate = 0.03

    commission = deal_amount * rate
    return commission


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION SENDER
# ═══════════════════════════════════════════════════════════════════════════════

async def send_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    notification_type: str = "info",
    action_url: Optional[str] = None,
    send_whatsapp: bool = False,
):
    """Send an in-app notification. Optionally also send via WhatsApp."""
    from app.models.notification import Notification

    notif = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        is_read=False,
        action_url=action_url,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    # Optionally send WhatsApp
    if send_whatsapp:
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.phone:
                from app.services.whatsapp_service import send_whatsapp_message
                await send_whatsapp_message(
                    to_phone=user.phone,
                    message=f"*{title}*\n\n{body}\n\n— Vestra",
                )
        except Exception:
            pass

    return notif
