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
    """Landlord rental dashboard with key metrics."""
    units = await get_landlord_units(db, landlord_id)
    tenants = await list_landlord_tenants(db, landlord_id)

    total_units = len(units)
    occupied_units = sum(1 for u in units if u.is_occupied)
    total_tenants = len([t for t in tenants if t.is_active])

    # This month's rent
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    month_payments = await db.execute(
        select(
            func.count(RentPayment.id),
            func.sum(RentPayment.amount_paid_kes),
        ).where(
            RentPayment.month == month,
            RentPayment.status == RentPaymentStatus.paid,
            RentPayment.unit_id.in_([u.id for u in units]),
        )
    )
    paid_count, total_collected = month_payments.one()

    # Expected rent
    expected_rent = sum(u.monthly_rent_kes for u in units if u.is_occupied)
    collection_rate = (float(total_collected or 0) / expected_rent * 100) if expected_rent > 0 else 0

    # Pending maintenance
    maint_result = await db.execute(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.unit_id.in_([u.id for u in units]),
            MaintenanceRequest.status.in_(["reported", "assigned", "in_progress"]),
        )
    )
    pending_maintenance = maint_result.scalar_one()

    return {
        "total_units": total_units,
        "occupied_units": occupied_units,
        "vacancy_rate": round((1 - occupied_units / total_units) * 100, 1) if total_units else 0,
        "total_tenants": total_tenants,
        "expected_monthly_rent": expected_rent,
        "collected_this_month": float(total_collected or 0),
        "collection_rate": round(collection_rate, 1),
        "pending_maintenance": pending_maintenance,
        "late_payments": paid_count or 0,
    }
