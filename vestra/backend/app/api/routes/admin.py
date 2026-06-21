
import contextlib
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.payment import PaymentStatus
from app.models.user import UserRole
from app.services.payment_service import (
    get_daily_revenue,
    get_monthly_revenue_stats,
    get_payment_by_id,
    get_revenue_by_method,
    get_revenue_by_purpose,
    get_revenue_reconciliation,
    get_revenue_summary,
    get_total_revenue,
)
from app.services.property_service import (
    count_active_listings,
    count_properties,
    count_verified_properties,
    get_all_properties_admin,
    get_city_distribution,
    get_monthly_listing_stats,
    get_property_type_distribution,
    update_property_status,
)
from app.services.user_service import (
    count_agents,
    count_users,
    get_all_users,
    get_monthly_user_growth,
    get_user_by_id,
    get_user_role_distribution,
    toggle_user_active,
    update_user_role,
)
from app.services.verification_service import (
    admin_review_verification,
    bulk_review_verifications,
    count_pending_verifications,
    count_verifications,
    get_monthly_verification_stats,
    get_pending_verifications,
    get_verification_admin_stats,
    get_verification_queue,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get("/stats")
async def get_admin_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Full admin dashboard stats with chart data. Cached for 2 min."""
    import logging as _log
    import traceback as _tb

    from app.core.redis import cache_get, cache_set

    cache_key = "vestra:admin:stats"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        total_users = await count_users(db)
        total_properties = await count_properties(db)
        total_verifications = await count_verifications(db)
        total_revenue = await get_total_revenue(db)
        pending_verifications = await count_pending_verifications(db)
        active_listings = await count_active_listings(db)
        verified_properties = await count_verified_properties(db)
        agents_count = await count_agents(db)

        # Chart data
        monthly_revenue = await get_monthly_revenue_stats(db)
        monthly_listings = await get_monthly_listing_stats(db)
        monthly_verifications = await get_monthly_verification_stats(db)
        user_growth = await get_monthly_user_growth(db)
        user_distribution = await get_user_role_distribution(db)
        property_types = await get_property_type_distribution(db)
        city_distribution = await get_city_distribution(db)

        # Recent activity
        recent_users = await get_all_users(db, skip=0, limit=5)
        recent_properties = await get_all_properties_admin(db, skip=0, limit=5)
        pending_reviews = await get_pending_verifications(db, limit=5)
    except Exception as e:
        _log.getLogger("vestra").error(
            '{"event":"admin_stats_error","step":"data_fetch","error":"%s","trace":"%s"}',
            str(e), _tb.format_exc()[:500]
        )
        raise

    result = {
        "total_users": total_users,
        "total_properties": total_properties,
        "total_verifications": total_verifications,
        "total_revenue": round(total_revenue, 2),
        "pending_verifications": pending_verifications,
        "active_listings": active_listings,
        "verified_properties": verified_properties,
        "agents_count": agents_count,
        # Chart data
        "charts": {
            "monthly_revenue": monthly_revenue,
            "monthly_listings": monthly_listings,
            "monthly_verifications": monthly_verifications,
            "user_growth": user_growth,
            "user_distribution": user_distribution,
            "property_types": property_types,
            "city_distribution": city_distribution,
        },
        # Recent activity
        "recent_users": [
            {
                "id": u.id, "email": u.email, "full_name": u.full_name,
                "role": u.role.value, "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in recent_users
        ],
        "recent_properties": [
            {
                "id": p.id, "title": p.title, "city": p.city,
                "price": p.price, "status": p.status.value if p.status else None,
                "trust_score": p.trust_score, "is_verified": p.is_verified,
                "created_at": p.created_at.isoformat(),
            }
            for p in recent_properties
        ],
        "pending_reviews": [
            {
                "id": v.id, "property_id": v.property_id,
                "fraud_risk_score": v.fraud_risk_score,
                "trust_score": v.trust_score,
                "ai_recommendation": v.ai_recommendation,
                "status": v.status.value,
                "created_at": v.created_at.isoformat(),
            }
            for v in pending_reviews
        ],
    }

    # Cache for 2 minutes (admin stats are expensive — 15+ queries)
    await cache_set(cache_key, result, ttl=120)
    return result


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/users")
async def list_all_users(
    skip: int = 0,
    limit: int = 50,
    role: str | None = Query(None),
    search: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional role filter and search."""
    users = await get_all_users(db, skip=skip, limit=limit, role=role, search=search)
    total = await count_users(db, role=role)
    return {
        "items": [
            {
                "id": u.id, "email": u.email, "phone": u.phone,
                "full_name": u.full_name, "role": u.role.value,
                "is_active": u.is_active, "is_verified": u.is_verified,
                "location": u.location,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
    }


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    role: str = Query(..., pattern="^(buyer|seller|agent|landlord|admin|super_admin)$"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Promote or demote a user."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}") from None

    updated = await update_user_role(db, user, new_role)
    return {
        "message": f"User {updated.full_name} role changed to {updated.role.value}",
        "user_id": updated.id,
        "new_role": updated.role.value,
    }


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_status(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ban or unban a user."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot toggle your own status")

    updated = await toggle_user_active(db, user)
    return {
        "message": f"User {updated.full_name} is now {'active' if updated.is_active else 'suspended'}",
        "user_id": updated.id,
        "is_active": updated.is_active,
    }


# ─── Property Management ──────────────────────────────────────────────────────

@router.get("/properties")
async def list_all_properties_admin(
    skip: int = 0,
    limit: int = 50,
    status: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all properties for admin management."""
    properties = await get_all_properties_admin(db, skip=skip, limit=limit, status=status)
    total = await count_properties(db, status=status)
    return {
        "items": [
            {
                "id": p.id, "title": p.title, "city": p.city,
                "county": p.county, "price": p.price,
                "property_type": p.property_type.value if p.property_type else None,
                "listing_type": p.listing_type.value if p.listing_type else None,
                "status": p.status.value if p.status else None,
                "trust_score": p.trust_score, "is_verified": p.is_verified,
                "verification_badge": p.verification_badge,
                "views": p.views, "inquiries": p.inquiries,
                "created_at": p.created_at.isoformat(),
                "owner": {
                    "id": p.owner.id if p.owner else None,
                    "full_name": p.owner.full_name if p.owner else "Unknown",
                    "email": p.owner.email if p.owner else None,
                },
            }
            for p in properties
        ],
        "total": total,
    }


@router.put("/properties/{property_id}/status")
async def set_property_status(
    property_id: int,
    status: str = Query(..., pattern="^(draft|pending_review|active|suspended|sold|rented)$"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve, reject, suspend, or change property status."""
    from app.models.property import PropertyStatus

    try:
        new_status = PropertyStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from None

    prop = await update_property_status(db, property_id, new_status)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    return {
        "message": f"Property '{prop.title}' status changed to {prop.status.value}",
        "property_id": prop.id,
        "new_status": prop.status.value,
    }


# ─── User Deletion ─────────────────────────────────────────────────────────────

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user and all their data."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete user's properties, payments, documents, etc.
    from app.models.document import Document
    from app.models.payment import Payment
    from app.models.property import Property

    await db.execute(sql_delete(Property).where(Property.owner_id == user_id))
    await db.execute(sql_delete(Payment).where(Payment.user_id == user_id))
    await db.execute(sql_delete(Document).where(Document.uploader_id == user_id))
    await db.delete(user)
    await db.commit()

    return {"message": f"User {user.full_name} and all associated data deleted"}


# ─── Payment Management ────────────────────────────────────────────────────────

@router.get("/payments")
async def list_all_payments(
    skip: int = 0,
    limit: int = 50,
    status: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all payments across the platform."""
    from sqlalchemy import select as sa_select

    from app.models.payment import Payment

    query = sa_select(Payment).order_by(Payment.created_at.desc())
    count_query = sa_select(func.count(Payment.id))

    if status:
        try:
            ps = PaymentStatus(status)
            query = query.where(Payment.status == ps)
            count_query = count_query.where(Payment.status == ps)
        except ValueError:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.offset(skip).limit(limit))
    payments = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id, "user_id": p.user_id, "amount": float(p.amount),
                "currency": p.currency, "method": p.method.value if p.method else None,
                "purpose": p.purpose.value if p.purpose else None,
                "status": p.status.value if p.status else None,
                "mpesa_receipt": p.mpesa_receipt_number,
                "phone_number": p.phone_number,
                "description": p.description,
                "reference": p.reference,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ],
        "total": total,
    }


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Refund a completed payment (Stripe API or M-Pesa manual mark)."""
    from app.models.payment import PaymentMethod
    from app.services.payment_service import refund_payment_mpesa, refund_payment_stripe

    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
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


# ─── Revenue Dashboard ─────────────────────────────────────────────────────────


@router.get("/revenue/summary")
async def revenue_summary(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Total revenue, this month, today, projected monthly, growth rate."""
    return await get_revenue_summary(db)


@router.get("/revenue/by-purpose")
async def revenue_by_purpose(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by payment purpose."""
    return {"items": await get_revenue_by_purpose(db)}


@router.get("/revenue/by-method")
async def revenue_by_method(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by payment method (mpesa, stripe, bank)."""
    return {"items": await get_revenue_by_method(db)}


@router.get("/revenue/daily")
async def revenue_daily(
    days: int = Query(30, ge=1, le=365),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daily revenue for the last N days with zero-fill for missing days."""
    return {"items": await get_daily_revenue(db, days=days), "period_days": days}


@router.get("/revenue/reconcile")
async def revenue_reconcile(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reconcile completed payments sum with expected revenue to detect discrepancies."""
    return await get_revenue_reconciliation(db)

@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """View system audit trail."""
    from app.models.audit_log import AuditLog

    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_query = select(func.count(AuditLog.id))

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.offset(skip).limit(limit))
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": log_entry.id, "user_id": log_entry.user_id, "action": log_entry.action,
                "resource_type": log_entry.resource_type, "resource_id": log_entry.resource_id,
                "details": log_entry.details, "ip_address": log_entry.ip_address,
                "created_at": log_entry.created_at.isoformat() if log_entry.created_at else None,
            }
            for log_entry in logs
        ],
        "total": total,
    }


# ─── Fraud Report Management ───────────────────────────────────────────────────

@router.get("/fraud-reports")
async def list_fraud_reports(
    limit: int = 50,
    status: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """View all fraud reports."""
    from app.models.trust_safety import FraudReport, FraudReportStatus

    query = select(FraudReport).order_by(FraudReport.created_at.desc())
    if status:
        with contextlib.suppress(ValueError):
            query = query.where(FraudReport.status == FraudReportStatus(status))

    result = await db.execute(query.limit(limit))
    reports = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id, "reporter_id": r.reporter_id,
                "reported_phone": r.reported_phone, "reported_email": r.reported_email,
                "reported_name": r.reported_name, "reported_title_deed": r.reported_title_deed,
                "description": r.description, "evidence_urls": r.evidence_urls or [],
                "status": r.status.value if r.status else None,
                "review_notes": r.review_notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
    }


# ─── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/analytics/funnel")
async def analytics_conversion_funnel(
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Conversion funnel: visitor -> registered -> verified -> made_payment -> subscribed."""
    from datetime import datetime

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    from app.services.analytics_service import get_conversion_funnel
    funnel = await get_conversion_funnel(db, start_date=start, end_date=end)
    return {"funnel": funnel}


@router.get("/analytics/cohorts")
async def analytics_retention_cohorts(
    weeks: int = Query(8, ge=4, le=52),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Weekly user retention cohorts."""
    from app.services.analytics_service import get_cohort_retention
    cohorts = await get_cohort_retention(db, weeks=weeks)
    return {"cohorts": cohorts}


@router.get("/analytics/events")
async def analytics_event_counts(
    days: int = Query(30, ge=1, le=365),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Event type distribution for the last N days."""
    from datetime import datetime, timedelta

    from app.services.analytics_service import get_event_counts_by_type

    start = datetime.now(UTC) - timedelta(days=days)
    events = await get_event_counts_by_type(db, start_date=start)
    return {"items": events, "period_days": days}


@router.get("/analytics/dau")
async def analytics_daily_active_users(
    days: int = Query(30, ge=1, le=90),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daily active users for the last N days."""
    from app.services.analytics_service import get_daily_active_users
    dau = await get_daily_active_users(db, days=days)
    return {"dau": dau, "period_days": days}


@router.put("/fraud-reports/{report_id}/review")
async def review_fraud_report(
    report_id: int,
    status: str = Query(..., pattern="^(pending|investigating|confirmed|false_report)$"),
    notes: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Review and update a fraud report."""
    from app.models.trust_safety import FraudReportStatus
    from app.services.fraud_service import admin_review_fraud

    report = await admin_review_fraud(db, report_id, admin.id, FraudReportStatus(status), notes)
    if not report:
        raise HTTPException(status_code=404, detail="Fraud report not found")
    return {"message": f"Fraud report #{report.id} marked as {status}", "report_id": report.id}


# ─── KYC Review ────────────────────────────────────────────────────────────────

@router.get("/kyc/pending")
async def list_pending_kyc(
    limit: int = 20,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get KYC submissions awaiting review."""
    from app.services.kyc_service import count_pending_kyc, get_pending_kyc

    items = await get_pending_kyc(db, limit)
    total = await count_pending_kyc(db)

    return {
        "total": total,
        "items": [
            {
                "id": k.id, "user_id": k.user_id,
                "id_type": k.id_type, "id_number": k.id_number,
                "status": k.status.value if k.status else None,
                "id_front_url": k.id_front_url,
                "ocr_data": k.ocr_data,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in items
        ],
    }


@router.put("/kyc/{kyc_id}/review")
async def review_kyc(
    kyc_id: int,
    status: str = Query(..., pattern="^(approved|rejected)$"),
    rejection_reason: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a KYC submission."""
    from app.models.kyc_notification import KYCStatus
    from app.services.kyc_service import admin_review_kyc

    kyc = await admin_review_kyc(
        db, kyc_id, admin.id,
        KYCStatus.approved if status == "approved" else KYCStatus.rejected,
        rejection_reason
    )
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return {"message": f"KYC #{kyc.id} {status}", "kyc_id": kyc.id}


# ─── Verification Review ──────────────────────────────────────────────────────

@router.get("/verifications/pending")
async def list_pending_verifications(
    limit: int = 20,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get verifications needing admin review."""
    verifications = await get_pending_verifications(db, limit=limit)
    return [
        {
            "id": v.id, "property_id": v.property_id,
            "fraud_risk_score": v.fraud_risk_score,
            "trust_score": v.trust_score,
            "price_reasonableness": v.price_reasonableness,
            "ownership_confidence": v.ownership_confidence,
            "ai_recommendation": v.ai_recommendation,
            "ai_summary": v.ai_summary,
            "document_flags": v.document_flags or [],
            "status": v.status.value,
            "created_at": v.created_at.isoformat(),
            "user": {
                "id": v.user.id if v.user else None,
                "full_name": v.user.full_name if v.user else "Unknown",
                "email": v.user.email if v.user else None,
            },
        }
        for v in verifications
    ]


@router.put("/verifications/{verification_id}/review")
async def review_verification(
    verification_id: int,
    status: str = Query(..., pattern="^(approved|flagged|rejected)$"),
    notes: str | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin reviews a verification and approves/flaggs/rejects it."""
    from app.models.document import VerificationStatus

    try:
        vstatus = VerificationStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from None

    verification = await admin_review_verification(
        db, verification_id, admin.id, vstatus, notes
    )
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    return {
        "message": f"Verification #{verification.id} {verification.status.value}",
        "verification_id": verification.id,
        "status": verification.status.value,
    }


# ─── Admin Verification Queue & Bulk Ops ────────────────────────────────────────


@router.get("/verifications/queue")
async def admin_verification_queue(
    status: str | None = Query(None, description="Filter by status: pending, in_progress, flagged, approved, rejected"),
    city: str | None = Query(None, description="Filter by city name"),
    risk_level: str | None = Query(None, description="Filter by risk: high, medium, low"),
    date_from: str | None = Query(None, description="Start date YYYY-MM-DD"),
    date_to: str | None = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin verification queue sorted by fraud_risk_score DESC (riskiest first).
    Includes property title, owner name, document count, and AI recommendation.
    """
    queue = await get_verification_queue(
        db=db,
        status_filter=status,
        city=city,
        risk_level=risk_level,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return {
        "total": len(queue),
        "items": queue,
    }


@router.post("/verifications/bulk-review")
async def admin_bulk_review_verifications(
    reviews: list[dict],
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch approve/reject verifications.
    Body: [{"id": 1, "status": "approved", "notes": "All docs verified"}, ...]
    Status options: approved, flagged, rejected
    """
    results = await bulk_review_verifications(
        db=db,
        reviewer_id=admin.id,
        reviews=reviews,
    )
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = sum(1 for r in results if not r.get("success"))
    return {
        "message": f"Processed {len(results)} reviews: {success_count} succeeded, {fail_count} failed",
        "total": len(results),
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results,
    }


@router.get("/verifications/stats")
async def admin_verification_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Verification dashboard stats for admin:
    - total_pending: pending + in_progress
    - reviewed_today: approved/flagged/rejected today
    - average_review_time_hours: avg time from created to review
    - approval_rate_percent: % of decided that are approved
    """
    return await get_verification_admin_stats(db=db)
