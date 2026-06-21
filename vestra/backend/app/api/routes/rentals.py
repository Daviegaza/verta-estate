"""
Rental Management API — units, tenants, leases, rent collection, maintenance.
Subscription-gated: Free (2 units), Basic (10), Pro (30), Premium (100).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.rental_service import (
    create_rental_unit, get_landlord_units, get_unit_detail,
    add_tenant, get_tenant, list_landlord_tenants,
    generate_monthly_rent_bills, request_rent_payment, record_rent_payment,
    create_maintenance_request, get_unit_maintenance, update_maintenance_status,
    get_rental_dashboard,
)
from app.services.subscription_service import get_listing_limit, enforce_subscription
from app.models.rental import (
    Lease, RentPayment, Tenant, PaymentArrangement, ArrangementStatus,
    InstallmentPayment, RentCollectionConfig,
)

router = APIRouter(prefix="/rentals", tags=["Rental Management"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def rental_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Landlord rental portfolio dashboard."""
    await enforce_subscription(db, current_user.id, current_user.role)
    return await get_rental_dashboard(db, current_user.id)


# ── Units ─────────────────────────────────────────────────────────────────────

@router.post("/units")
async def create_unit(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a rental unit to manage."""
    limit = await get_listing_limit(db, current_user.id, current_user.role.value)
    current_units = await get_landlord_units(db, current_user.id)
    if len(current_units) >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Unit limit reached ({limit}). Upgrade your subscription to add more units.",
        )
    unit = await create_rental_unit(db, current_user.id, data)
    return {"id": unit.id, "name": unit.name, "message": "Unit created"}


@router.get("/units")
async def list_my_units(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all my rental units with apartment details."""
    units = await get_landlord_units(db, current_user.id)
    return [
        {
            "id": u.id,
            "building_name": u.building_name,
            "name": u.name,
            "unit_number": u.unit_number,
            "unit_type": u.unit_type,
            "bedrooms": u.bedrooms,
            "bathrooms": u.bathrooms,
            "floor": u.floor,
            "size_sqft": float(u.size_sqft) if u.size_sqft else None,
            "city": u.city,
            "address": u.address,
            "monthly_rent_kes": float(u.monthly_rent_kes) if u.monthly_rent_kes else 0,
            "deposit_kes": float(u.deposit_kes) if u.deposit_kes else 0,
            "water_kes": float(u.water_kes) if u.water_kes else 0,
            "electricity_kes": float(u.electricity_kes) if u.electricity_kes else 0,
            "service_charge_kes": float(u.service_charge_kes) if u.service_charge_kes else 0,
            "total_monthly_kes": float(u.monthly_rent_kes or 0) + float(u.water_kes or 0) + float(u.electricity_kes or 0) + float(u.service_charge_kes or 0),
            "is_occupied": u.is_occupied,
            "amenities": u.amenities or [],
            "tenants": [
                {"id": t.id, "name": t.full_name, "phone": t.phone, "is_active": t.is_active}
                for t in (u.tenants or []) if t.is_active
            ],
        }
        for u in units
    ]


@router.get("/units/{unit_id}")
async def get_unit(unit_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get unit details with tenants and leases."""
    unit = await get_unit_detail(db, unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {
        "id": unit.id, "name": unit.name, "unit_type": unit.unit_type,
        "bedrooms": unit.bedrooms, "bathrooms": unit.bathrooms,
        "monthly_rent_kes": unit.monthly_rent_kes, "deposit_kes": unit.deposit_kes,
        "address": unit.address, "city": unit.city, "is_occupied": unit.is_occupied,
        "tenants": [
            {"id": t.id, "name": t.full_name, "phone": t.phone, "email": t.email,
             "move_in": t.move_in_date.isoformat() if t.move_in_date else None,
             "is_active": t.is_active}
            for t in (unit.tenants or [])
        ],
        "leases": [
            {"id": l.id, "start": l.start_date.isoformat(), "end": l.end_date.isoformat(),
             "rent": l.monthly_rent_kes, "status": l.status.value}
            for l in (unit.leases or [])
        ],
    }


# ── Tenants ───────────────────────────────────────────────────────────────────

@router.post("/tenants")
async def create_tenant(
    unit_id: int = Query(...),
    full_name: str = Query(...),
    phone: str = Query(...),
    email: Optional[str] = Query(None),
    national_id: Optional[str] = Query(None),
    move_in_date: Optional[str] = Query(None),
    rent_due_day: int = Query(1),
    lease_start: Optional[str] = Query(None),
    lease_end: Optional[str] = Query(None),
    monthly_rent: Optional[float] = Query(None),
    deposit: Optional[float] = Query(0),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a tenant to a unit with lease."""
    from datetime import datetime

    tenant_data = {
        "full_name": full_name, "phone": phone, "email": email,
        "national_id": national_id,
        "move_in_date": datetime.fromisoformat(move_in_date) if move_in_date else datetime.now(timezone.utc),
        "rent_due_day": rent_due_day,
    }
    lease_data = {
        "start_date": datetime.fromisoformat(lease_start) if lease_start else datetime.now(timezone.utc),
        "end_date": datetime.fromisoformat(lease_end) if lease_end else datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1),
        "monthly_rent_kes": monthly_rent,
        "deposit_kes": deposit,
    }

    tenant = await add_tenant(db, unit_id, tenant_data, lease_data)
    return {"id": tenant.id, "name": tenant.full_name, "message": "Tenant added with lease"}


@router.get("/tenants")
async def list_my_tenants(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all my tenants across all units."""
    tenants = await list_landlord_tenants(db, current_user.id)
    return [
        {
            "id": t.id, "name": t.full_name, "phone": t.phone,
            "unit": t.unit.name if t.unit else "N/A",
            "rent": t.lease.monthly_rent_kes if t.lease else 0,
            "due_day": t.rent_due_day, "is_active": t.is_active,
        }
        for t in tenants
    ]


# ── Rent Collection ───────────────────────────────────────────────────────────

@router.post("/rent/generate-bills")
async def generate_bills(
    month: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate monthly rent bills for all tenants."""
    bills = await generate_monthly_rent_bills(db, current_user.id, month)
    return {"generated": len(bills), "month": month or datetime.now(timezone.utc).strftime("%Y-%m")}


@router.post("/rent/request-payment/{tenant_id}")
async def request_rent(
    tenant_id: int,
    month: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send M-Pesa STK Push to a tenant for rent payment."""
    result = await request_rent_payment(db, tenant_id, month)
    return result


@router.post("/rent/record-payment/{tenant_id}")
async def record_rent(
    tenant_id: int,
    amount: float = Query(...),
    mpesa_receipt: str = Query(""),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually record a rent payment."""
    bill = await record_rent_payment(db, tenant_id, amount, mpesa_receipt)
    return {"status": bill.status.value, "amount_paid": bill.amount_paid_kes}


# ── Maintenance ───────────────────────────────────────────────────────────────

@router.post("/maintenance/report")
async def report_maintenance(
    unit_id: int = Query(...),
    title: str = Query(...),
    description: str = Query(""),
    priority: str = Query("medium"),
    category: str = Query("other"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Report a maintenance issue."""
    # Find tenant for this user's phone
    units = await get_landlord_units(db, current_user.id)
    # For simplicity, use current user's phone; in production, match tenant by phone
    req = await create_maintenance_request(db, unit_id, current_user.id, {
        "title": title, "description": description,
        "priority": priority, "category": category,
    })
    return {"id": req.id, "title": req.title, "status": req.status.value}


@router.get("/maintenance/{unit_id}")
async def list_maintenance(
    unit_id: int,
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get maintenance requests for a unit."""
    requests = await get_unit_maintenance(db, unit_id, status)
    return [
        {"id": r.id, "title": r.title, "priority": r.priority.value,
         "status": r.status.value, "category": r.category,
         "created_at": r.created_at.isoformat()}
        for r in requests
    ]


@router.put("/maintenance/{request_id}")
async def update_maintenance(
    request_id: int,
    status: str = Query(...),
    notes: str = Query(""),
    actual_cost: Optional[float] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update maintenance request status."""
    req = await update_maintenance_status(db, request_id, status, notes, actual_cost)
    return {"id": req.id, "status": req.status.value, "message": "Updated"}


# ── Tenant: My Rental ────────────────────────────────────────────────────────

@router.get("/my-rental")
async def get_my_rental(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's rental (for tenant role)."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.rental import Tenant, RentalUnit, Lease

    # Find tenant record matching user's phone or email
    result = await db.execute(
        select(Tenant)
        .options(joinedload(Tenant.unit).joinedload(RentalUnit.landlord))
        .options(joinedload(Tenant.lease))
        .where(
            Tenant.is_active == True,
            Tenant.phone == current_user.phone,
        )
        .limit(1)
    )
    tenant = result.unique().scalar_one_or_none()

    if not tenant:
        return None

    unit = tenant.unit
    lease = tenant.lease
    landlord = unit.landlord if unit else None

    return {
        "id": unit.id if unit else None,
        "unit_name": unit.name if unit else None,
        "unit_type": unit.unit_type if unit else None,
        "city": unit.city if unit else None,
        "bedrooms": unit.bedrooms if unit else None,
        "monthly_rent_kes": float(unit.monthly_rent_kes) if unit and unit.monthly_rent_kes else 0,
        "deposit_kes": float(unit.deposit_kes) if unit and unit.deposit_kes else 0,
        "lease_start": lease.start_date.isoformat() if lease and lease.start_date else None,
        "lease_end": lease.end_date.isoformat() if lease and lease.end_date else None,
        "days_remaining": (lease.end_date - datetime.now(timezone.utc)).days if lease and lease.end_date else 0,
        "landlord_name": landlord.full_name if landlord else None,
        "landlord_phone": landlord.phone if landlord else None,
        "landlord_email": landlord.email if landlord else None,
        "next_payment_due": None,  # Calculated in frontend from rent_due_day
        "payment_status": "pending",
        "tenant_id": tenant.id,
    }


@router.post("/rent/pay")
async def tenant_pay_rent(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant initiates rent payment via M-Pesa."""
    from sqlalchemy import select
    from app.models.rental import Tenant

    # Find tenant by phone
    result = await db.execute(
        select(Tenant).where(
            Tenant.is_active == True,
            Tenant.phone == current_user.phone,
        ).limit(1)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="No active rental found for your account")

    amount = data.get("amount", 0)
    phone_number = data.get("phone_number") or current_user.phone

    # Trigger M-Pesa STK Push
    result = await request_rent_payment(db, tenant.id, month=None)
    return result


# ── Maintenance (Tenant-friendly) ────────────────────────────────────────────

@router.get("/maintenance")
async def get_my_maintenance(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get maintenance requests — tenant sees own, landlord sees all for their units."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.rental import Tenant, MaintenanceRequest, RentalUnit

    if current_user.role.value == 'landlord':
        # Landlord: get all maintenance for their units
        result = await db.execute(
            select(RentalUnit).where(RentalUnit.landlord_id == current_user.id)
        )
        units = result.scalars().all()
        unit_ids = [u.id for u in units]

        if not unit_ids:
            return {"items": [], "total": 0}

        result = await db.execute(
            select(MaintenanceRequest)
            .options(joinedload(MaintenanceRequest.tenant), joinedload(MaintenanceRequest.unit))
            .where(MaintenanceRequest.unit_id.in_(unit_ids))
            .order_by(MaintenanceRequest.created_at.desc())
            .limit(50)
        )
        requests = result.unique().scalars().all()
    elif current_user.role.value == 'tenant':
        # Tenant: find their tenant record by phone
        result = await db.execute(
            select(Tenant).where(
                Tenant.is_active == True,
                Tenant.phone == current_user.phone,
            ).limit(1)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"items": [], "total": 0}

        result = await db.execute(
            select(MaintenanceRequest)
            .options(joinedload(MaintenanceRequest.unit))
            .where(MaintenanceRequest.tenant_id == tenant.id)
            .order_by(MaintenanceRequest.created_at.desc())
            .limit(50)
        )
        requests = result.unique().scalars().all()
    else:
        return {"items": [], "total": 0}

    return {
        "items": [
            {
                "id": r.id,
                "unit_id": r.unit_id,
                "unit_name": r.unit.name if r.unit else None,
                "tenant_id": r.tenant_id,
                "tenant_name": r.tenant.full_name if r.tenant else None,
                "title": r.title,
                "issue": r.title,
                "description": r.description,
                "priority": r.priority.value if r.priority else "medium",
                "status": r.status.value if r.status else "reported",
                "category": r.category,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in requests
        ],
        "total": len(requests),
    }


@router.post("/maintenance")
async def create_tenant_maintenance(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant-friendly: submit maintenance request without needing unit_id as query param."""
    from sqlalchemy import select
    from app.models.rental import Tenant

    # Find tenant by phone
    result = await db.execute(
        select(Tenant).where(
            Tenant.is_active == True,
            Tenant.phone == current_user.phone,
        ).limit(1)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="No active rental found for your account")

    req = await create_maintenance_request(db, tenant.unit_id, tenant.id, {
        "title": data.get("issue") or data.get("title", "Maintenance Request"),
        "description": data.get("description", ""),
        "priority": data.get("priority", "medium"),
        "category": data.get("issue") or data.get("category", "other"),
    })
    return {"id": req.id, "title": req.title, "status": req.status.value, "message": "Request submitted"}


@router.put("/maintenance/{request_id}/resolve")
async def resolve_maintenance(
    request_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Landlord: mark maintenance as resolved."""
    req = await update_maintenance_status(db, request_id, "completed", "Resolved by landlord", None)
    return {"id": req.id, "status": req.status.value, "message": "Resolved"}


# ── Automation — Reminders & Smart Features ─────────────────────────────────

@router.post("/automation/send-reminders")
async def trigger_rent_reminders(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger rent due reminders for all tenants approaching due date.
    Sends in-app notifications and WhatsApp reminders.
    Typically called by a daily cron job but can be triggered manually.
    """
    from app.services.smart_automation import send_rent_due_reminders, send_lease_expiry_alerts

    rent_result = await send_rent_due_reminders(db)
    lease_result = await send_lease_expiry_alerts(db)

    return {
        "message": "Reminders sent",
        "rent_reminders": rent_result,
        "lease_alerts": lease_result,
    }


@router.get("/payment-feed")
async def landlord_payment_feed(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Real-time payment feed for landlord — all rent payments across all units."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.rental import RentPayment, RentalUnit, Tenant

    # Get landlord's units
    result = await db.execute(
        select(RentalUnit).where(RentalUnit.landlord_id == current_user.id)
    )
    units = result.scalars().all()
    unit_ids = [u.id for u in units]

    if not unit_ids:
        return {"items": [], "total_collected": 0}

    # Get all rent payments
    result = await db.execute(
        select(RentPayment)
        .options(joinedload(RentPayment.tenant), joinedload(RentPayment.unit))
        .where(RentPayment.unit_id.in_(unit_ids))
        .order_by(RentPayment.paid_date.desc().nulls_last(), RentPayment.created_at.desc())
        .limit(50)
    )
    payments = result.unique().scalars().all()

    total = sum(float(p.amount_paid_kes or 0) for p in payments if p.status.value == 'paid')

    return {
        "items": [
            {
                "id": p.id,
                "tenant_name": p.tenant.full_name if p.tenant else "Unknown",
                "tenant_phone": p.tenant.phone if p.tenant else "",
                "unit_name": p.unit.name if p.unit else "",
                "building": p.unit.building_name if p.unit else "",
                "amount_kes": float(p.amount_kes),
                "amount_paid_kes": float(p.amount_paid_kes or 0),
                "status": p.status.value,
                "month": p.month,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                "mpesa_receipt": p.mpesa_receipt,
                "late_fee_kes": float(p.late_fee_kes or 0),
            }
            for p in payments
        ],
        "total_collected": round(total, 2),
        "payment_count": len(payments),
    }


# ── Schedule & Auto-Collection ──────────────────────────────────────────────

@router.post("/schedule/{lease_id}")
async def schedule_auto_collection(
    lease_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable auto-collection for a lease via monthly M-Pesa STK Push."""
    from sqlalchemy import select
    from app.models.rental import Lease, LeaseStatus

    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    unit = await get_unit_detail(db, lease.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    lease.auto_renew = True
    await db.commit()
    return {"lease_id": lease.id, "auto_collect": True, "message": "Auto-collection enabled via M-Pesa"}


@router.delete("/schedule/{lease_id}")
async def cancel_auto_collection(
    lease_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable auto-collection for a lease."""
    from sqlalchemy import select
    from app.models.rental import Lease

    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    unit = await get_unit_detail(db, lease.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    lease.auto_renew = False
    await db.commit()
    return {"lease_id": lease.id, "auto_collect": False, "message": "Auto-collection disabled"}


# ── Payment History & Receipts ──────────────────────────────────────────────

@router.get("/unit/{unit_id}/payments")
async def unit_payment_history(
    unit_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for a rental unit."""
    from sqlalchemy import select
    from app.models.rental import RentPayment

    unit = await get_unit_detail(db, unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(RentPayment)
        .where(RentPayment.unit_id == unit_id)
        .order_by(RentPayment.created_at.desc())
        .limit(50)
    )
    payments = result.scalars().all()
    return [
        {
            "id": p.id, "tenant_id": p.tenant_id,
            "amount_kes": float(p.amount_kes), "amount_paid_kes": float(p.amount_paid_kes or 0),
            "status": p.status.value, "month": p.month,
            "due_date": p.due_date.isoformat() if p.due_date else None,
            "paid_date": p.paid_date.isoformat() if p.paid_date else None,
            "mpesa_receipt": p.mpesa_receipt,
            "late_fee_kes": float(p.late_fee_kes or 0),
        }
        for p in payments
    ]


@router.get("/unit/{unit_id}/receipt/{payment_id}")
async def download_rent_receipt(
    unit_id: int,
    payment_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a rent payment receipt as PDF."""
    from fastapi.responses import Response
    from app.services.receipt_service import generate_rent_receipt_pdf

    unit = await get_unit_detail(db, unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    pdf_bytes = await generate_rent_receipt_pdf(db, payment_id, unit_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Receipt not found or PDF generation unavailable")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Vestra_Rent_Receipt_{payment_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ── Flexible Payments — Arrangements, Partial Payments, Grace Periods ─────────

@router.post("/arrangements/request")
async def request_arrangement(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tenant requests a flexible payment arrangement.
    Example: { "tenant_id": 1, "amount_kes": 30000, "installments": 3, "reason": "Paid on 15th" }
    """
    from app.services.rental_service import request_payment_arrangement

    tenant_id = data.get("tenant_id")
    if not tenant_id:
        # Find tenant by user's phone
        from sqlalchemy import select
        from app.models.rental import Tenant
        result = await db.execute(
            select(Tenant).where(
                Tenant.is_active == True,
                Tenant.phone == current_user.phone,
            ).limit(1)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="No active rental found for your account")
        tenant_id = tenant.id

    arrangement = await request_payment_arrangement(
        db,
        tenant_id=tenant_id,
        amount_kes=data.get("amount_kes", 0),
        number_of_installments=data.get("installments", 2),
        reason=data.get("reason", ""),
    )
    return {
        "id": arrangement.id,
        "status": arrangement.status.value,
        "total_amount_kes": float(arrangement.total_amount_kes),
        "installments": arrangement.number_of_installments,
        "remaining_balance_kes": float(arrangement.remaining_balance_kes),
        "message": "Payment arrangement requested. Awaiting landlord approval.",
    }


@router.put("/arrangements/{arrangement_id}/approve")
async def approve_arrangement(
    arrangement_id: int,
    notes: str = Query(""),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Landlord approves a payment arrangement."""
    from app.services.rental_service import approve_payment_arrangement, get_active_arrangement
    from sqlalchemy import select
    from app.models.rental import PaymentArrangement, ArrangementStatus

    result = await db.execute(
        select(PaymentArrangement).where(PaymentArrangement.id == arrangement_id)
    )
    arr = result.scalar_one_or_none()
    if not arr:
        raise HTTPException(status_code=404, detail="Arrangement not found")

    # Verify landlord owns the unit
    unit = await get_unit_detail(db, arr.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    arr = await approve_payment_arrangement(db, arrangement_id, notes)
    return {
        "id": arr.id,
        "status": arr.status.value,
        "message": "Payment arrangement approved",
    }


@router.put("/arrangements/{arrangement_id}/decline")
async def decline_arrangement(
    arrangement_id: int,
    reason: str = Query(""),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Landlord declines a payment arrangement."""
    from app.services.rental_service import decline_payment_arrangement
    from app.models.rental import PaymentArrangement

    result = await db.execute(
        select(PaymentArrangement).where(PaymentArrangement.id == arrangement_id)
    )
    arr = result.scalar_one_or_none()
    if not arr:
        raise HTTPException(status_code=404, detail="Arrangement not found")

    unit = await get_unit_detail(db, arr.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    arr = await decline_payment_arrangement(db, arrangement_id, reason)
    return {"id": arr.id, "status": arr.status.value, "message": "Arrangement declined"}


@router.get("/arrangements")
async def list_arrangements(
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment arrangements. Tenant sees own, landlord sees all for their units."""
    from app.services.rental_service import get_tenant_arrangements, get_landlord_units
    from app.models.rental import PaymentArrangement, ArrangementStatus

    if current_user.role.value == "landlord":
        units = await get_landlord_units(db, current_user.id)
        unit_ids = [u.id for u in units]
        if not unit_ids:
            return {"items": [], "total": 0}

        query = select(PaymentArrangement).where(PaymentArrangement.unit_id.in_(unit_ids))
        if status:
            query = query.where(PaymentArrangement.status == ArrangementStatus(status))
        result = await db.execute(query.order_by(PaymentArrangement.created_at.desc()))
        items = result.scalars().all()
    else:
        # Tenant — find by phone
        from sqlalchemy import select as sa_select
        from app.models.rental import Tenant
        result = await db.execute(
            sa_select(Tenant).where(
                Tenant.is_active == True,
                Tenant.phone == current_user.phone,
            ).limit(1)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"items": [], "total": 0}
        items = await get_tenant_arrangements(db, tenant.id, status)

    return {
        "items": [
            {
                "id": a.id,
                "tenant_id": a.tenant_id,
                "total_amount_kes": float(a.total_amount_kes),
                "remaining_balance_kes": float(a.remaining_balance_kes),
                "installments": a.number_of_installments,
                "installments_paid": a.installments_paid,
                "status": a.status.value,
                "reason": a.reason,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
        "total": len(items),
    }


@router.post("/partial-payment")
async def partial_payment(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a partial rent payment.
    Tenant pays what they can — balance is tracked automatically.
    Example: { "tenant_id": 1, "amount_kes": 5000, "mpesa_receipt": "RCPT123" }
    """
    from app.services.rental_service import record_partial_rent_payment

    tenant_id = data.get("tenant_id")
    if not tenant_id:
        from sqlalchemy import select
        from app.models.rental import Tenant
        result = await db.execute(
            select(Tenant).where(
                Tenant.is_active == True,
                Tenant.phone == current_user.phone,
            ).limit(1)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="No active rental found for your account")
        tenant_id = tenant.id

    result = await record_partial_rent_payment(
        db,
        tenant_id=tenant_id,
        amount=data.get("amount_kes", 0),
        mpesa_receipt=data.get("mpesa_receipt", ""),
    )
    return result


@router.get("/balance/{tenant_id}")
async def get_balance(
    tenant_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get outstanding rent balance for a tenant."""
    from app.services.rental_service import get_tenant, get_active_arrangement
    from datetime import datetime, timezone

    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    result = await db.execute(
        select(RentPayment).where(
            RentPayment.tenant_id == tenant_id,
            RentPayment.month == month,
        )
    )
    bill = result.scalar_one_or_none()

    arrangement = await get_active_arrangement(db, tenant_id)

    full_rent = float(tenant.lease.monthly_rent_kes) if tenant.lease else 0
    paid = float(bill.amount_paid_kes) if bill else 0
    balance = max(0, full_rent - paid)

    # Grace period info
    config = None
    if tenant.lease:
        from app.services.rental_service import get_rent_collection_config
        config = await get_rent_collection_config(db, tenant.lease.id)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.full_name,
        "month": month,
        "full_rent_kes": full_rent,
        "amount_paid_kes": paid,
        "outstanding_balance_kes": balance,
        "status": bill.status.value if bill else "unbilled",
        "due_date": bill.due_date.isoformat() if bill and bill.due_date else None,
        "grace_period_days": config.grace_period_days if config else 5,
        "late_fee_kes": float(bill.late_fee_kes or 0) if bill else 0,
        "allow_partial_payments": config.allow_partial_payments if config else True,
        "active_arrangement": {
            "id": arrangement.id,
            "remaining_balance_kes": float(arrangement.remaining_balance_kes),
            "installments_paid": arrangement.installments_paid,
            "total_installments": arrangement.number_of_installments,
            "status": arrangement.status.value,
        } if arrangement else None,
    }


@router.get("/collection-config/{lease_id}")
async def get_collection_config(
    lease_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get rent collection configuration for a lease."""
    from app.services.rental_service import get_rent_collection_config

    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    unit = await get_unit_detail(db, lease.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    config = await get_rent_collection_config(db, lease_id)
    return {
        "lease_id": lease_id,
        "grace_period_days": config.grace_period_days,
        "late_fee_type": config.late_fee_type,
        "late_fee_amount_kes": float(config.late_fee_amount_kes),
        "late_fee_percent": float(config.late_fee_percent),
        "late_fee_max_kes": float(config.late_fee_max_kes),
        "allow_partial_payments": config.allow_partial_payments,
        "allow_payment_arrangements": config.allow_payment_arrangements,
        "auto_apply_late_fees": config.auto_apply_late_fees,
        "reminders_enabled": config.reminders_enabled,
    }


@router.put("/collection-config/{lease_id}")
async def update_collection_config(
    lease_id: int,
    grace_period_days: Optional[int] = Query(None),
    late_fee_type: Optional[str] = Query(None),
    late_fee_amount_kes: Optional[float] = Query(None),
    late_fee_max_kes: Optional[float] = Query(None),
    allow_partial_payments: Optional[bool] = Query(None),
    allow_payment_arrangements: Optional[bool] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Landlord updates rent collection settings for a lease.

    - grace_period_days: Days after due date before late fees apply (0-30)
    - late_fee_type: "fixed" (per day), "percentage" (of rent), or "none"
    - late_fee_amount_kes: Fixed daily late fee in KES
    - late_fee_max_kes: Cap on total late fees
    - allow_partial_payments: Accept less than full rent
    - allow_payment_arrangements: Allow installment plans
    """
    from app.services.rental_service import update_rent_collection_config

    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    unit = await get_unit_detail(db, lease.unit_id)
    if not unit or unit.landlord_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    config = await update_rent_collection_config(
        db, lease_id,
        grace_period_days=grace_period_days,
        late_fee_type=late_fee_type,
        late_fee_amount_kes=late_fee_amount_kes,
        late_fee_max_kes=late_fee_max_kes,
        allow_partial_payments=allow_partial_payments,
        allow_payment_arrangements=allow_payment_arrangements,
    )
    return {
        "lease_id": lease_id,
        "grace_period_days": config.grace_period_days,
        "late_fee_type": config.late_fee_type,
        "allow_partial_payments": config.allow_partial_payments,
        "allow_payment_arrangements": config.allow_payment_arrangements,
        "message": "Collection configuration updated",
    }