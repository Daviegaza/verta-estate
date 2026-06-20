"""
VESTRA Rental Management Service
=================================
Complete property management for landlords:
- Tenant management (add, screen, track)
- Automated M-Pesa rent collection with STK Push reminders
- Lease management with auto-renew
- Maintenance request tracking
- Late fee calculation
- Rent payment analytics

Subscription-gated: Free (2 units), Basic (10), Pro (30), Premium (100)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from app.models.rental import (
    RentalUnit, Tenant, Lease, RentPayment, MaintenanceRequest,
    LeaseStatus, RentPaymentStatus, MaintenanceStatus, MaintenancePriority,
)
from app.core.redis import cache_get, cache_set, cache_delete
from app.services.subscription_service import get_listing_limit

logger = logging.getLogger("vestra")

LATE_FEE_PER_DAY_KES = 100  # KES 100 per day late
LATE_FEE_MAX_KES = 3000     # Max KES 3,000 late fee


# ── Rental Units ──────────────────────────────────────────────────────────────

async def create_rental_unit(
    db: AsyncSession, landlord_id: int, data: dict,
) -> RentalUnit:
    """Add a rental unit to manage."""
    unit = RentalUnit(landlord_id=landlord_id, **data)
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    logger.info('{"event":"rental_unit_created","landlord":%d,"unit":%d}', landlord_id, unit.id)
    return unit


async def get_landlord_units(
    db: AsyncSession, landlord_id: int,
) -> List[RentalUnit]:
    """Get all rental units for a landlord."""
    result = await db.execute(
        select(RentalUnit)
        .options(joinedload(RentalUnit.tenants))
        .where(RentalUnit.landlord_id == landlord_id)
        .order_by(RentalUnit.created_at.desc())
    )
    return result.unique().scalars().all()


async def get_unit_detail(db: AsyncSession, unit_id: int) -> Optional[RentalUnit]:
    """Get a rental unit with tenants and leases."""
    result = await db.execute(
        select(RentalUnit)
        .options(
            joinedload(RentalUnit.tenants),
            joinedload(RentalUnit.leases),
        )
        .where(RentalUnit.id == unit_id)
    )
    return result.unique().scalar_one_or_none()


# ── Tenant Management ─────────────────────────────────────────────────────────

async def add_tenant(
    db: AsyncSession, unit_id: int, data: dict, lease_data: Optional[dict] = None,
) -> Tenant:
    """Add a tenant to a unit and optionally create a lease."""
    # Check unit is vacant
    unit = await get_unit_detail(db, unit_id)
    if not unit:
        raise ValueError("Unit not found")
    if unit.is_occupied:
        raise ValueError("Unit is already occupied")

    tenant = Tenant(unit_id=unit_id, **data)
    db.add(tenant)
    await db.flush()

    # Create lease
    if lease_data:
        lease = Lease(
            unit_id=unit_id,
            tenant_id=tenant.id,
            start_date=lease_data.get("start_date", datetime.now(timezone.utc)),
            end_date=lease_data.get("end_date", datetime.now(timezone.utc) + timedelta(days=365)),
            monthly_rent_kes=lease_data.get("monthly_rent_kes", unit.monthly_rent_kes),
            deposit_kes=lease_data.get("deposit_kes", unit.deposit_kes),
            terms=lease_data.get("terms", ""),
            auto_renew=lease_data.get("auto_renew", False),
        )
        db.add(lease)

    # Mark unit occupied
    unit.is_occupied = True

    await db.commit()
    await db.refresh(tenant)
    logger.info('{"event":"tenant_added","unit":%d,"tenant":%d}', unit_id, tenant.id)
    return tenant


async def get_tenant(db: AsyncSession, tenant_id: int) -> Optional[Tenant]:
    """Get tenant with lease and payment history."""
    result = await db.execute(
        select(Tenant)
        .options(
            joinedload(Tenant.lease),
            joinedload(Tenant.payments),
        )
        .where(Tenant.id == tenant_id)
    )
    return result.unique().scalar_one_or_none()


async def list_landlord_tenants(db: AsyncSession, landlord_id: int) -> List[Tenant]:
    """Get all tenants across all units for a landlord."""
    result = await db.execute(
        select(Tenant)
        .join(RentalUnit)
        .options(joinedload(Tenant.unit), joinedload(Tenant.lease))
        .where(RentalUnit.landlord_id == landlord_id)
        .order_by(Tenant.move_in_date.desc())
    )
    return result.unique().scalars().all()


# ── Rent Collection (M-Pesa STK Push) ─────────────────────────────────────────

async def generate_monthly_rent_bills(
    db: AsyncSession, landlord_id: int, month: str = None,
) -> List[RentPayment]:
    """Generate rent payment bills for all active tenants for the current month."""
    if not month:
        now = datetime.now(timezone.utc)
        month = now.strftime("%Y-%m")

    # Get all active tenants for this landlord
    tenants = await list_landlord_tenants(db, landlord_id)
    bills = []

    for tenant in tenants:
        if not tenant.is_active or not tenant.lease:
            continue

        # Check if bill already exists for this month
        existing = await db.execute(
            select(RentPayment).where(
                RentPayment.tenant_id == tenant.id,
                RentPayment.month == month,
            )
        )
        if existing.scalar_one_or_none():
            continue

        lease = tenant.lease
        rent = lease.monthly_rent_kes
        due_date = datetime.now(timezone.utc).replace(day=tenant.rent_due_day)

        bill = RentPayment(
            tenant_id=tenant.id,
            unit_id=tenant.unit_id,
            lease_id=lease.id,
            amount_kes=rent,
            amount_paid_kes=0,
            status=RentPaymentStatus.pending,
            due_date=due_date,
            month=month,
        )
        db.add(bill)
        bills.append(bill)

    if bills:
        await db.commit()
        logger.info('{"event":"rent_bills_generated","landlord":%d,"count":%d}', landlord_id, len(bills))

    return bills


async def request_rent_payment(
    db: AsyncSession, tenant_id: int, month: str = None,
) -> dict:
    """
    Send M-Pesa STK Push to a tenant for rent payment.
    This is the automated rent collection engine.
    """
    from app.services.mpesa_service import initiate_stk_push

    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise ValueError("Tenant not found")

    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Get or create rent bill
    result = await db.execute(
        select(RentPayment).where(
            RentPayment.tenant_id == tenant_id,
            RentPayment.month == month,
        )
    )
    bill = result.scalar_one_or_none()

    if not bill:
        bill = RentPayment(
            tenant_id=tenant_id,
            unit_id=tenant.unit_id,
            lease_id=tenant.lease.id if tenant.lease else None,
            amount_kes=tenant.lease.monthly_rent_kes if tenant.lease else tenant.unit.monthly_rent_kes,
            status=RentPaymentStatus.pending,
            due_date=datetime.now(timezone.utc),
            month=month,
        )
        db.add(bill)
        await db.commit()

    # Apply late fee if overdue
    if bill.due_date and datetime.now(timezone.utc) > bill.due_date:
        days_late = (datetime.now(timezone.utc) - bill.due_date).days
        late_fee = min(days_late * LATE_FEE_PER_DAY_KES, LATE_FEE_MAX_KES)
        bill.late_fee_kes = late_fee
        bill.amount_kes = (tenant.lease.monthly_rent_kes if tenant.lease else 0) + late_fee
        await db.commit()

    # Initiate M-Pesa STK Push
    phone = tenant.phone
    amount = bill.amount_kes
    description = f"Rent {month}"

    mpesa_response = await initiate_stk_push(
        phone_number=phone,
        amount=amount,
        account_reference=f"RENT{tenant_id}",
        transaction_desc=description[:13],
    )

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.full_name,
        "amount_kes": amount,
        "month": month,
        "late_fee_kes": bill.late_fee_kes,
        "mpesa_response": mpesa_response,
        "payment_id": bill.id,
    }


async def record_rent_payment(
    db: AsyncSession, tenant_id: int, amount: float,
    mpesa_receipt: str = "", payment_id: int = None,
) -> RentPayment:
    """Record a rent payment (called by M-Pesa callback or manual entry)."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    # Find pending bill
    result = await db.execute(
        select(RentPayment).where(
            RentPayment.tenant_id == tenant_id,
            RentPayment.month == month,
            RentPayment.status.in_([RentPaymentStatus.pending, RentPaymentStatus.late]),
        )
    )
    bill = result.scalar_one_or_none()

    if not bill:
        # Auto-create bill
        tenant = await get_tenant(db, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        bill = RentPayment(
            tenant_id=tenant_id,
            unit_id=tenant.unit_id,
            amount_kes=tenant.lease.monthly_rent_kes if tenant.lease else 0,
            amount_paid_kes=amount,
            status=RentPaymentStatus.paid,
            due_date=now,
            paid_date=now,
            month=month,
            mpesa_receipt=mpesa_receipt,
            payment_id=payment_id,
        )
        db.add(bill)
    else:
        bill.amount_paid_kes = amount
        bill.status = RentPaymentStatus.paid if amount >= bill.amount_kes else RentPaymentStatus.partial
        bill.paid_date = now
        bill.mpesa_receipt = mpesa_receipt
        bill.payment_id = payment_id

    await db.commit()
    logger.info('{"event":"rent_paid","tenant":%d,"amount":%f,"month":"%s"}', tenant_id, amount, month)
    return bill


# ── Flexible Payment Arrangements ─────────────────────────────────────────────

async def request_payment_arrangement(
    db: AsyncSession,
    tenant_id: int,
    amount_kes: float,
    number_of_installments: int,
    reason: str = "",
    start_date: datetime = None,
) -> PaymentArrangement:
    """
    Tenant requests a flexible payment plan.
    Example: "I can pay KES 30,000 in 3 installments of KES 10,000"
    """
    from app.models.rental import PaymentArrangement, ArrangementStatus

    tenant = await get_tenant(db, tenant_id)
    if not tenant or not tenant.is_active:
        raise ValueError("Tenant not found or inactive")

    if number_of_installments < 1 or number_of_installments > 6:
        raise ValueError("Installments must be between 1 and 6")

    now = datetime.now(timezone.utc)
    if not start_date:
        start_date = now

    # End date: spread installments roughly evenly within the month
    end_date = start_date + timedelta(days=min(30, number_of_installments * 7))

    arrangement = PaymentArrangement(
        tenant_id=tenant.id,
        unit_id=tenant.unit_id,
        lease_id=tenant.lease.id if tenant.lease else None,
        total_amount_kes=amount_kes,
        remaining_balance_kes=amount_kes,
        number_of_installments=number_of_installments,
        installments_paid=0,
        status=ArrangementStatus.requested,
        reason=reason,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(arrangement)
    await db.flush()

    # Create installment schedule
    installment_amount = amount_kes / number_of_installments
    for i in range(number_of_installments):
        due = start_date + timedelta(days=i * max(1, 30 // number_of_installments))
        inst = InstallmentPayment(
            arrangement_id=arrangement.id,
            amount_kes=installment_amount,
            due_date=due,
            status="pending",
        )
        db.add(inst)

    await db.commit()
    await db.refresh(arrangement)
    logger.info(
        '{"event":"payment_arrangement_requested","tenant":%d,"amount":%f,"installments":%d}',
        tenant_id, amount_kes, number_of_installments,
    )
    return arrangement


async def approve_payment_arrangement(
    db: AsyncSession,
    arrangement_id: int,
    landlord_notes: str = "",
) -> PaymentArrangement:
    """Landlord approves a payment arrangement."""
    result = await db.execute(
        select(PaymentArrangement).where(PaymentArrangement.id == arrangement_id)
    )
    arr = result.scalar_one_or_none()
    if not arr:
        raise ValueError("Payment arrangement not found")

    arr.status = ArrangementStatus.active
    if landlord_notes:
        arr.landlord_notes = landlord_notes
    await db.commit()
    await db.refresh(arr)
    logger.info(
        '{"event":"payment_arrangement_approved","arrangement":%d,"tenant":%d}',
        arrangement_id, arr.tenant_id,
    )
    return arr


async def decline_payment_arrangement(
    db: AsyncSession,
    arrangement_id: int,
    reason: str = "",
) -> PaymentArrangement:
    """Landlord declines a payment arrangement."""
    result = await db.execute(
        select(PaymentArrangement).where(PaymentArrangement.id == arrangement_id)
    )
    arr = result.scalar_one_or_none()
    if not arr:
        raise ValueError("Payment arrangement not found")

    arr.status = ArrangementStatus.declined
    if reason:
        arr.landlord_notes = reason
    await db.commit()
    return arr


async def get_tenant_arrangements(
    db: AsyncSession,
    tenant_id: int,
    status: str = None,
) -> list[PaymentArrangement]:
    """Get all payment arrangements for a tenant."""
    query = select(PaymentArrangement).where(PaymentArrangement.tenant_id == tenant_id)
    if status:
        query = query.where(PaymentArrangement.status == ArrangementStatus(status))
    result = await db.execute(query.order_by(PaymentArrangement.created_at.desc()))
    return result.scalars().all()


async def get_active_arrangement(
    db: AsyncSession,
    tenant_id: int,
) -> Optional[PaymentArrangement]:
    """Get the currently active payment arrangement for a tenant."""
    result = await db.execute(
        select(PaymentArrangement)
        .where(
            PaymentArrangement.tenant_id == tenant_id,
            PaymentArrangement.status.in_([ArrangementStatus.active, ArrangementStatus.requested]),
        )
        .order_by(PaymentArrangement.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def record_installment_payment(
    db: AsyncSession,
    arrangement_id: int,
    installment_index: int,
    amount: float,
    mpesa_receipt: str = "",
) -> InstallmentPayment:
    """Record a payment against a specific installment."""
    result = await db.execute(
        select(PaymentArrangement).where(PaymentArrangement.id == arrangement_id)
    )
    arr = result.scalar_one_or_none()
    if not arr:
        raise ValueError("Payment arrangement not found")

    # Get the installment
    result = await db.execute(
        select(InstallmentPayment)
        .where(InstallmentPayment.arrangement_id == arrangement_id)
        .order_by(InstallmentPayment.due_date)
    )
    installments = result.scalars().all()

    if installment_index >= len(installments):
        raise ValueError(f"Installment {installment_index} not found")

    inst = installments[installment_index]
    inst.amount_paid_kes = amount
    inst.status = "paid" if amount >= inst.amount_kes else "pending"
    inst.paid_date = datetime.now(timezone.utc)
    inst.mpesa_receipt = mpesa_receipt

    arr.remaining_balance_kes -= amount
    arr.installments_paid = sum(1 for i in installments if i.status == "paid")

    if arr.remaining_balance_kes <= 0:
        arr.status = ArrangementStatus.completed

    await db.commit()
    await db.refresh(inst)
    logger.info(
        '{"event":"installment_paid","arrangement":%d,"installment":%d,"amount":%f}',
        arrangement_id, installment_index, amount,
    )
    return inst


# ── Partial Payments & Balance Tracking ───────────────────────────────────────

async def record_partial_rent_payment(
    db: AsyncSession,
    tenant_id: int,
    amount: float,
    mpesa_receipt: str = "",
    payment_id: int = None,
) -> dict:
    """
    Record a partial rent payment when tenant pays less than full rent.
    Tracks remaining balance and supports multiple payments per month.
    """
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise ValueError("Tenant not found")

    full_rent = float(tenant.lease.monthly_rent_kes) if tenant.lease else float(tenant.unit.monthly_rent_kes)

    # Find existing bill for this month
    result = await db.execute(
        select(RentPayment).where(
            RentPayment.tenant_id == tenant_id,
            RentPayment.month == month,
        )
    )
    bill = result.scalar_one_or_none()

    if not bill:
        # Create new bill
        due_day = tenant.rent_due_day or 1
        due_date = now.replace(day=min(due_day, 28))

        # Check for active payment arrangement
        arrangement = await get_active_arrangement(db, tenant_id)

        bill = RentPayment(
            tenant_id=tenant_id,
            unit_id=tenant.unit_id,
            lease_id=tenant.lease.id if tenant.lease else None,
            amount_kes=full_rent,
            amount_paid_kes=0,
            status=RentPaymentStatus.pending,
            due_date=due_date,
            month=month,
        )
        db.add(bill)
        await db.flush()

    # Add this payment
    new_total_paid = float(bill.amount_paid_kes or 0) + amount
    bill.amount_paid_kes = new_total_paid

    if new_total_paid >= float(bill.amount_kes):
        bill.status = RentPaymentStatus.paid
        bill.paid_date = now
        remaining = 0
    else:
        bill.status = RentPaymentStatus.partial
        remaining = float(bill.amount_kes) - new_total_paid

    bill.mpesa_receipt = mpesa_receipt or bill.mpesa_receipt
    bill.payment_id = payment_id or bill.payment_id

    await db.commit()
    await db.refresh(bill)

    # Auto-update arrangement if exists
    arrangement = await get_active_arrangement(db, tenant_id)
    if arrangement and arrangement.status == ArrangementStatus.active:
        # Apply this payment toward the arrangement
        arrangement.remaining_balance_kes -= amount
        arrangement.installments_paid += 1
        if arrangement.remaining_balance_kes <= 0:
            arrangement.status = ArrangementStatus.completed
        await db.commit()

    logger.info(
        '{"event":"partial_rent_paid","tenant":%d,"amount":%f,"remaining":%f,"month":"%s"}',
        tenant_id, amount, remaining, month,
    )

    return {
        "bill_id": bill.id,
        "tenant_id": tenant_id,
        "full_rent_kes": full_rent,
        "amount_paid_kes": new_total_paid,
        "remaining_balance_kes": remaining,
        "status": bill.status.value,
        "month": month,
        "next_payment_due": bill.due_date.isoformat(),
    }


# ── Grace Period & Late Fee Configuration ─────────────────────────────────────

async def get_rent_collection_config(
    db: AsyncSession,
    lease_id: int,
) -> RentCollectionConfig:
    """Get or create rent collection config for a lease."""
    result = await db.execute(
        select(RentCollectionConfig).where(RentCollectionConfig.lease_id == lease_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = RentCollectionConfig(lease_id=lease_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


async def update_rent_collection_config(
    db: AsyncSession,
    lease_id: int,
    grace_period_days: int = None,
    late_fee_type: str = None,
    late_fee_amount_kes: float = None,
    late_fee_max_kes: float = None,
    allow_partial_payments: bool = None,
    allow_payment_arrangements: bool = None,
) -> RentCollectionConfig:
    """Update rent collection configuration for a lease."""
    config = await get_rent_collection_config(db, lease_id)

    if grace_period_days is not None:
        config.grace_period_days = max(0, grace_period_days)
    if late_fee_type is not None:
        config.late_fee_type = late_fee_type
    if late_fee_amount_kes is not None:
        config.late_fee_amount_kes = late_fee_amount_kes
    if late_fee_max_kes is not None:
        config.late_fee_max_kes = late_fee_max_kes
    if allow_partial_payments is not None:
        config.allow_partial_payments = allow_partial_payments
    if allow_payment_arrangements is not None:
        config.allow_payment_arrangements = allow_payment_arrangements

    await db.commit()
    await db.refresh(config)
    return config


async def calculate_late_fee_with_grace(
    db: AsyncSession,
    tenant_id: int,
    bill: RentPayment,
) -> float:
    """
    Calculate late fee considering grace period.
    Returns 0 if within grace period.
    """
    if not bill.due_date:
        return 0

    now = datetime.now(timezone.utc)
    if now <= bill.due_date:
        return 0

    days_late = (now - bill.due_date).days

    # Get config
    tenant = await get_tenant(db, tenant_id)
    config = None
    if tenant and tenant.lease:
        config = await get_rent_collection_config(db, tenant.lease.id)

    grace_days = config.grace_period_days if config else 5

    if days_late <= grace_days:
        return 0  # Within grace period — no late fee

    # Calculate late fee after grace
    chargeable_days = days_late - grace_days

    if config and config.late_fee_type == "none":
        return 0
    elif config and config.late_fee_type == "percentage":
        rent = float(bill.amount_kes)
        fee = rent * (float(config.late_fee_percent or 2) / 100) * chargeable_days
    else:
        # Fixed daily fee
        daily_fee = float(config.late_fee_amount_kes) if config else LATE_FEE_PER_DAY_KES
        fee = chargeable_days * daily_fee

    max_fee = float(config.late_fee_max_kes) if config else LATE_FEE_MAX_KES
    return min(fee, max_fee)


# ── Maintenance ───────────────────────────────────────────────────────────────

async def create_maintenance_request(
    db: AsyncSession, unit_id: int, tenant_id: int, data: dict,
) -> MaintenanceRequest:
    """Tenant reports a maintenance issue."""
    req = MaintenanceRequest(
        unit_id=unit_id,
        tenant_id=tenant_id,
        title=data["title"],
        description=data.get("description", ""),
        priority=MaintenancePriority(data.get("priority", "medium")),
        category=data.get("category", "other"),
        images=data.get("images", []),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    logger.info('{"event":"maintenance_reported","unit":%d,"tenant":%d}', unit_id, tenant_id)
    return req


async def get_unit_maintenance(
    db: AsyncSession, unit_id: int, status: str = None,
) -> List[MaintenanceRequest]:
    """Get maintenance requests for a unit."""
    query = select(MaintenanceRequest).where(MaintenanceRequest.unit_id == unit_id)
    if status:
        query = query.where(MaintenanceRequest.status == MaintenanceStatus(status))
    result = await db.execute(query.order_by(MaintenanceRequest.created_at.desc()))
    return result.scalars().all()


async def update_maintenance_status(
    db: AsyncSession, request_id: int, new_status: str,
    notes: str = "", actual_cost: float = None,
) -> MaintenanceRequest:
    """Update maintenance request status (landlord action)."""
    result = await db.execute(
        select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise ValueError("Maintenance request not found")

    req.status = MaintenanceStatus(new_status)
    if notes:
        req.notes = notes
    if actual_cost:
        req.actual_cost_kes = actual_cost
    if new_status == "completed":
        req.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(req)
    return req


# ── Analytics ──────────────────────────────────────────────────────────────────

async def get_rental_dashboard(db: AsyncSession, landlord_id: int) -> dict:
    """Landlord rental dashboard with apartment-focused metrics."""
    units = await get_landlord_units(db, landlord_id)
    tenants = await list_landlord_tenants(db, landlord_id)

    total_units = len(units)
    occupied_units = sum(1 for u in units if u.is_occupied)
    vacant_units = total_units - occupied_units
    total_tenants = len([t for t in tenants if t.is_active])

    # Building-level grouping
    buildings = {}
    for u in units:
        bldg = u.building_name or u.address.split(',')[0].strip() or 'Unnamed Building'
        if bldg not in buildings:
            buildings[bldg] = {"total": 0, "occupied": 0, "units": []}
        buildings[bldg]["total"] += 1
        if u.is_occupied:
            buildings[bldg]["occupied"] += 1
        buildings[bldg]["units"].append({
            "id": u.id, "name": u.name, "unit_number": u.unit_number,
            "unit_type": u.unit_type, "floor": u.floor, "bedrooms": u.bedrooms,
            "monthly_rent_kes": float(u.monthly_rent_kes), "is_occupied": u.is_occupied,
            "amenities": u.amenities or [],
        })

    # This month's rent
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    unit_ids = [u.id for u in units]

    month_payments = await db.execute(
        select(
            func.count(RentPayment.id),
            func.sum(RentPayment.amount_paid_kes),
            func.sum(RentPayment.late_fee_kes),
        ).where(
            RentPayment.month == month,
            RentPayment.status.in_([RentPaymentStatus.paid, RentPaymentStatus.partial]),
            RentPayment.unit_id.in_(unit_ids) if unit_ids else [0],
        )
    )
    paid_count, total_collected, total_late_fees = month_payments.one()

    # Late payments this month
    late_result = await db.execute(
        select(func.count(RentPayment.id)).where(
            RentPayment.month == month,
            RentPayment.status == RentPaymentStatus.late,
            RentPayment.unit_id.in_(unit_ids) if unit_ids else [0],
        )
    )
    late_count = late_result.scalar_one() or 0

    # Expected rent (only occupied units)
    expected_rent = sum(float(u.monthly_rent_kes) for u in units if u.is_occupied)
    collection_rate = round((float(total_collected or 0) / expected_rent * 100), 1) if expected_rent > 0 else 0

    # Utility totals
    total_water = sum(float(u.water_kes or 0) for u in units)
    total_electricity = sum(float(u.electricity_kes or 0) for u in units)
    total_service_charge = sum(float(u.service_charge_kes or 0) for u in units)

    # Pending maintenance
    maint_result = await db.execute(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.unit_id.in_(unit_ids) if unit_ids else [0],
            MaintenanceRequest.status.in_(["reported", "assigned", "in_progress"]),
        )
    )
    pending_maintenance = maint_result.scalar_one() or 0

    # Unit type breakdown
    unit_types = {}
    for u in units:
        t = u.unit_type or 'other'
        unit_types[t] = unit_types.get(t, 0) + 1

    # Efficiency metrics (time & money saved by using Vestra)
    # Assume manual rent collection takes ~30 min/tenant/month, M-Pesa automation saves that
    hours_saved = total_tenants * 0.5  # 30 min per tenant per month
    # Assume manual receipt generation takes 10 min each
    receipt_time_saved = paid_count * 10 / 60  # hours
    # Late fees automatically calculated and applied
    auto_late_fees = float(total_late_fees or 0)
    # Assume 5% higher collection rate with automated reminders vs manual
    efficiency_boost = 5 if total_tenants > 0 else 0

    return {
        "total_units": total_units,
        "occupied_units": occupied_units,
        "vacant_units": vacant_units,
        "vacancy_rate": round((vacant_units / total_units * 100), 1) if total_units else 0,
        "total_tenants": total_tenants,
        "expected_monthly_rent": round(expected_rent, 2),
        "collected_this_month": round(float(total_collected or 0), 2),
        "collection_rate": round(collection_rate, 1),
        "pending_maintenance": pending_maintenance,
        "late_payments": late_count,
        "late_fees_collected": round(auto_late_fees, 2),
        # Apartment-specific
        "buildings": [
            {
                "name": name,
                "total_units": data["total"],
                "occupied": data["occupied"],
                "vacant": data["total"] - data["occupied"],
                "occupancy_rate": round(data["occupied"] / data["total"] * 100, 1) if data["total"] else 0,
                "units": data["units"][:6],  # Top 6 units per building
            }
            for name, data in buildings.items()
        ],
        "unit_types": unit_types,
        "utilities": {
            "water": round(total_water, 2),
            "electricity": round(total_electricity, 2),
            "service_charge": round(total_service_charge, 2),
            "total": round(total_water + total_electricity + total_service_charge, 2),
        },
        # Why VESTRA? — Efficiency metrics
        "efficiency": {
            "hours_saved_per_month": round(hours_saved + receipt_time_saved, 1),
            "automated_collections": paid_count,
            "auto_late_fees_kes": round(auto_late_fees, 2),
            "collection_boost_pct": f"+{efficiency_boost}%",
            "maintenance_resolved": pending_maintenance,
            "total_rent_managed_kes": round(expected_rent, 2),
        },
    }
