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
    """List all my rental units."""
    units = await get_landlord_units(db, current_user.id)
    return [
        {
            "id": u.id, "name": u.name, "unit_type": u.unit_type,
            "bedrooms": u.bedrooms, "city": u.city,
            "monthly_rent_kes": u.monthly_rent_kes,
            "is_occupied": u.is_occupied,
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

@router.post("/maintenance")
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