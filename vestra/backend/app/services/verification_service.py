import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import cache_delete
from app.models.document import Document, Verification, VerificationStatus
from app.models.property import Property
from app.models.user import User
from app.services.ai_service import analyze_property_with_ai
from app.services.property_service import get_property_by_id

logger = logging.getLogger("vestra")

# ── Background task tracking (prevents GC of async tasks) ───────────────────
_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro):
    """Fire a coroutine as a background task with persistent reference."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def create_verification_request(
    db: AsyncSession,
    property_id: int,
    requester_id: int,
    payment_id: int | None = None,
) -> Verification:
    verification = Verification(
        property_id=property_id,
        user_id=requester_id,
        requester_id=requester_id,
        payment_id=payment_id,
        status=VerificationStatus.pending,
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    return verification


async def run_ai_verification(
    db: AsyncSession,
    verification_id: int,
) -> Verification:
    """Run AI analysis on a verification request."""
    result = await db.execute(
        select(Verification).where(Verification.id == verification_id)
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise ValueError(f"Verification {verification_id} not found")

    verification.status = VerificationStatus.in_progress
    await db.commit()

    # ── Fire analytics: verification_requested ────────────────────────────
    from app.services.analytics_service import fire_and_forget_track_user_event

    _fire_and_forget(
        fire_and_forget_track_user_event(
            user_id=verification.user_id,
            event_type="verification_requested",
            event_data={"verification_id": verification.id, "property_id": verification.property_id},
        )
    )

    # Get property details
    prop = await get_property_by_id(db, verification.property_id)
    if not prop:
        verification.status = VerificationStatus.rejected
        await db.commit()
        return verification

    # Get documents
    doc_result = await db.execute(
        select(Document).where(Document.property_id == prop.id)
    )
    documents = doc_result.scalars().all()
    docs_info = [
        {"type": d.document_type.value, "name": d.file_name, "is_verified": d.is_verified}
        for d in documents
    ]

    # Get owner info (handle both dict from cache and ORM object)
    owner_id = prop.owner_id if hasattr(prop, 'owner_id') else prop.get("owner_id")
    owner_result = await db.execute(select(User).where(User.id == owner_id))
    owner = owner_result.scalar_one_or_none()
    agent_info = None
    if owner:
        # Safely access agent_profile — it may not exist even if the user is an agent
        license_number = None
        if hasattr(owner, 'agent_profile') and owner.agent_profile is not None:
            license_number = owner.agent_profile.license_number
        agent_info = {
            "name": owner.full_name,
            "email": owner.email,
            "role": owner.role.value,
            "is_verified": owner.is_verified,
            "license_number": license_number,
        }

    # Build property_data dict — handle both ORM objects and cached dicts
    def _get_prop_attr(obj, attr, default=None):
        """Safely get attribute from ORM object or dict."""
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            # Handle enum values
            if hasattr(val, 'value'):
                return val.value
            return val
        elif isinstance(obj, dict):
            return obj.get(attr, default)
        return default

    property_data = {
        "title": _get_prop_attr(prop, "title", ""),
        "property_type": _get_prop_attr(prop, "property_type", "residential"),
        "listing_type": _get_prop_attr(prop, "listing_type", "sale"),
        "address": _get_prop_attr(prop, "address", ""),
        "city": _get_prop_attr(prop, "city", ""),
        "county": _get_prop_attr(prop, "county", ""),
        "price": _get_prop_attr(prop, "price", 0),
        "size_sqft": _get_prop_attr(prop, "size_sqft"),
        "bedrooms": _get_prop_attr(prop, "bedrooms"),
        "bathrooms": _get_prop_attr(prop, "bathrooms"),
        "year_built": _get_prop_attr(prop, "year_built"),
        "description": _get_prop_attr(prop, "description", ""),
        "amenities": _get_prop_attr(prop, "amenities") or [],
    }

    ai_result = await analyze_property_with_ai(property_data, docs_info, agent_info)

    # Map AI results to verification record
    verification.fraud_risk_score = ai_result.get("fraud_risk_score")
    verification.trust_score = ai_result.get("trust_score")
    verification.price_reasonableness = ai_result.get("price_reasonableness")
    verification.ownership_confidence = ai_result.get("ownership_confidence")
    verification.ai_recommendation = ai_result.get("ai_recommendation")
    verification.document_flags = ai_result.get("document_flags", [])
    verification.ai_summary = ai_result.get("ai_summary")
    verification.ai_raw_response = ai_result

    rec = ai_result.get("ai_recommendation", "review")
    if rec == "approve":
        verification.status = VerificationStatus.approved
        prop.is_verified = True
        prop.trust_score = ai_result.get("trust_score")
        prop.verification_badge = _get_badge_level(ai_result.get("trust_score", 0))
    elif rec == "reject":
        verification.status = VerificationStatus.rejected
    else:
        verification.status = VerificationStatus.flagged

    await db.commit()
    await db.refresh(verification)
    # Invalidate property cache (trust score changed)
    await cache_delete(f"vestra:prop:{prop.id}")
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:admin:stats")

    # ── Fire analytics: verification_completed ────────────────────────────
    _fire_and_forget(
        fire_and_forget_track_user_event(
            user_id=verification.user_id,
            event_type="verification_completed",
            event_data={
                "verification_id": verification.id,
                "property_id": verification.property_id,
                "status": verification.status.value if verification.status else None,
                "trust_score": float(verification.trust_score or 0),
                "ai_recommendation": verification.ai_recommendation,
            },
        )
    )

    # ── Fire event bus: verification completed ─────────────────────────────
    _fire_and_forget(
        _bg_emit_verification_event(verification, prop)
    )

    return verification


def _get_badge_level(trust_score: float) -> str:
    if trust_score >= 90:
        return "platinum"
    elif trust_score >= 75:
        return "gold"
    elif trust_score >= 60:
        return "silver"
    else:
        return "bronze"


async def get_verification_by_id(
    db: AsyncSession, verification_id: int
) -> Verification | None:
    result = await db.execute(
        select(Verification).where(Verification.id == verification_id)
    )
    return result.scalar_one_or_none()


async def get_verifications_for_property(
    db: AsyncSession, property_id: int
) -> list:
    result = await db.execute(
        select(Verification)
        .where(Verification.property_id == property_id)
        .order_by(Verification.created_at.desc())
    )
    return result.scalars().all()


async def count_verifications(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Verification.id)))
    return result.scalar_one()


async def count_pending_verifications(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.status.in_([VerificationStatus.pending, VerificationStatus.in_progress])
        )
    )
    return result.scalar_one()


async def admin_review_verification(
    db: AsyncSession,
    verification_id: int,
    reviewer_id: int,
    status: VerificationStatus,
    notes: str,
) -> Verification:
    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        return None

    verification.status = status
    verification.reviewed_by_id = reviewer_id
    verification.reviewer_notes = notes
    verification.reviewed_at = datetime.now(UTC)

    if status == VerificationStatus.approved and verification.property_id:
        prop = await get_property_by_id(db, verification.property_id)
        if prop:
            prop.is_verified = True
            prop.trust_score = verification.trust_score or 75
            await cache_delete(f"vestra:prop:{prop.id}")

    await db.commit()
    await db.refresh(verification)
    await cache_delete("vestra:list:*")
    await cache_delete("vestra:admin:stats")

    # ── Fire event bus: verification completed (admin review) ──────────────
    _fire_and_forget(
        _bg_emit_verification_event(verification, None)
    )

    # ── Fire-and-forget: track verification outcome ──────────────────────
    from app.services.analytics_service import fire_and_forget_track_verification_outcome

    _fire_and_forget(
        fire_and_forget_track_verification_outcome(
            verification_id=verification.id,
            ai_prediction={
                "fraud_risk_score": getattr(verification, "fraud_risk_score", None),
                "trust_score": getattr(verification, "trust_score", None),
                "ai_recommendation": getattr(verification, "ai_recommendation", None),
            },
            human_decision=verification.status.value if verification.status else "unknown",
            ground_truth_notes=notes,
        )
    )

    return verification


async def get_pending_verifications(
    db: AsyncSession, limit: int = 20,
) -> list:
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(Verification)
        .options(joinedload(Verification.user))
        .where(Verification.status.in_([
            VerificationStatus.pending, VerificationStatus.flagged
        ]))
        .order_by(Verification.created_at.desc())
        .limit(limit)
    )
    return result.unique().scalars().all()


async def get_monthly_verification_stats(db: AsyncSession) -> list:
    """Monthly verifications for last 6 months."""
    from datetime import datetime
    result = await db.execute(
        select(
            func.date_trunc('month', Verification.created_at).label('month'),
            func.count(Verification.id).label('count')
        ).where(
            Verification.created_at >= func.date_trunc('month', func.now()) - func.make_interval(0, 6)
        ).group_by('month').order_by('month')
    )
    data = {row.month.strftime('%b'): row.count for row in result.all()}
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    now = datetime.now(UTC)
    months = []
    for i in range(5, -1, -1):
        label = month_names[(now.month - 1 - i) % 12]
        months.append({"month": label, "verifications": data.get(label, 0)})
    return months


# ── Background event helpers ──────────────────────────────────────────────────


async def _bg_emit_verification_event(verification, prop) -> None:
    """Fire-and-forget: emit verification.completed event."""
    from app.services.event_bus import EVENT_VERIFICATION_COMPLETED, emit_event

    try:
        prop_title = prop.title if prop and hasattr(prop, "title") else str(verification.property_id)
        data = {
            "verification_id": verification.id,
            "property_id": verification.property_id,
            "property_title": prop_title,
            "status": verification.status.value if verification.status else "unknown",
            "trust_score": verification.trust_score,
        }
        await emit_event(
            event_type=EVENT_VERIFICATION_COMPLETED,
            user_id=verification.user_id,
            data=data,
        )
    except Exception:
        logger.warning(
            '{"event":"bg_verification_event_failed","verification_id":%d}',
            verification.id,
        )


# ── Admin Verification Queue ──────────────────────────────────────────────────


async def get_verification_queue(
    db: AsyncSession,
    status_filter: str | None = None,
    city: str | None = None,
    risk_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Returns pending/flagged verifications sorted by fraud_risk_score DESC
    (riskiest first). Includes property and owner info for admin review queue.
    """
    from sqlalchemy.orm import joinedload

    from app.models.user import User

    query = (
        select(Verification)
        .options(joinedload(Verification.user))
        .options(joinedload(Verification.property))
        .order_by(Verification.fraud_risk_score.desc().nullslast())
    )

    # Apply filters
    if status_filter:
        try:
            vs = VerificationStatus(status_filter)
            query = query.where(Verification.status == vs)
        except ValueError:
            pass
    else:
        # Default: pending + flagged
        query = query.where(
            Verification.status.in_([
                VerificationStatus.pending,
                VerificationStatus.in_progress,
                VerificationStatus.flagged,
            ])
        )

    if city:
        query = query.join(Property).where(Property.city.ilike(f"%{city}%"))

    if risk_level == "high":
        query = query.where(Verification.fraud_risk_score >= 55.0)
    elif risk_level == "medium":
        query = query.where(Verification.fraud_risk_score.between(25.0, 54.99))
    elif risk_level == "low":
        query = query.where(
            (Verification.fraud_risk_score < 25.0) | (Verification.fraud_risk_score.is_(None))
        )

    if date_from:
        from datetime import datetime as dt
        try:
            parsed = dt.strptime(date_from, "%Y-%m-%d")
            query = query.where(Verification.created_at >= parsed)
        except ValueError:
            pass

    if date_to:
        from datetime import datetime as dt
        from datetime import timedelta
        try:
            parsed = dt.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Verification.created_at < parsed)
        except ValueError:
            pass

    result = await db.execute(query.limit(limit))
    verifications = result.unique().scalars().all()

    queue = []
    for v in verifications:
        prop = v.property if hasattr(v, "property") else None
        owner_name = "N/A"
        if prop and hasattr(prop, "owner_id") and prop.owner_id:
            owner_result = await db.execute(
                select(User).where(User.id == prop.owner_id)
            )
            owner = owner_result.scalar_one_or_none()
            if owner:
                owner_name = owner.full_name

        doc_count = 0
        if v.property_id:
            from app.models.document import Document
            doc_result = await db.execute(
                select(func.count(Document.id)).where(
                    Document.property_id == v.property_id,
                    not Document.is_deleted,
                )
            )
            doc_count = doc_result.scalar_one()

        queue.append({
            "verification_id": v.id,
            "property_id": v.property_id,
            "property_title": prop.title if prop else "N/A",
            "owner_name": owner_name,
            "fraud_score": v.fraud_risk_score,
            "trust_score": v.trust_score,
            "ai_recommendation": v.ai_recommendation,
            "status": v.status.value if v.status else "unknown",
            "documents_count": doc_count,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        })

    return queue


async def bulk_review_verifications(
    db: AsyncSession,
    reviewer_id: int,
    reviews: list[dict],
) -> list[dict]:
    """
    Batch approve/reject verifications.
    Each review: {"id": int, "status": str, "notes": str}
    Returns list of results.
    """
    from app.services.analytics_service import fire_and_forget_track_verification_outcome

    results = []
    for review in reviews:
        vid = review.get("id")
        status_str = review.get("status", "flagged")
        notes = review.get("notes", "")

        if not vid:
            results.append({"id": None, "success": False, "error": "Missing verification id"})
            continue

        try:
            vs = VerificationStatus(status_str)
        except ValueError:
            results.append({"id": vid, "success": False, "error": f"Invalid status: {status_str}"})
            continue

        verification = await get_verification_by_id(db, vid)
        if not verification:
            results.append({"id": vid, "success": False, "error": "Verification not found"})
            continue

        verification.status = vs
        verification.reviewed_by_id = reviewer_id
        verification.reviewer_notes = notes
        from datetime import datetime
        verification.reviewed_at = datetime.now(UTC)

        if vs == VerificationStatus.approved and verification.property_id:
            from app.services.property_service import get_property_by_id
            prop = await get_property_by_id(db, verification.property_id)
            if prop:
                prop.is_verified = True
                prop.trust_score = verification.trust_score or 75
                prop.verification_badge = _get_badge_level(verification.trust_score or 75)
                await cache_delete(f"vestra:prop:{prop.id}")

        await db.commit()
        await db.refresh(verification)
        await cache_delete("vestra:list:*")
        await cache_delete("vestra:admin:stats")

        # Track analytics
        _fire_and_forget(
            fire_and_forget_track_verification_outcome(
                verification_id=verification.id,
                ai_prediction={
                    "fraud_risk_score": getattr(verification, "fraud_risk_score", None),
                    "trust_score": getattr(verification, "trust_score", None),
                    "ai_recommendation": getattr(verification, "ai_recommendation", None),
                },
                human_decision=vs.value,
                ground_truth_notes=notes,
            )
        )

        # Emit event
        _fire_and_forget(
            _bg_emit_verification_event(verification, None)
        )

        results.append({
            "id": vid,
            "success": True,
            "status": vs.value,
        })

    return results


async def get_verification_admin_stats(
    db: AsyncSession,
) -> dict:
    """
    Returns admin verification dashboard stats:
    - total_pending: pending + in_progress
    - reviewed_today: approved/flagged/rejected today
    - average_review_time: avg hours between created_at and reviewed_at
    - approval_rate: % of non-pending that are approved
    """
    from datetime import datetime

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total pending
    pending_result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.status.in_([
                VerificationStatus.pending,
                VerificationStatus.in_progress,
            ])
        )
    )
    total_pending = pending_result.scalar_one()

    # Reviewed today
    reviewed_today_result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.reviewed_at >= today_start,
            Verification.status.in_([
                VerificationStatus.approved,
                VerificationStatus.flagged,
                VerificationStatus.rejected,
            ])
        )
    )
    reviewed_today = reviewed_today_result.scalar_one()

    # Average review time (hours) for completed reviews
    avg_time_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Verification.reviewed_at - Verification.created_at) / 3600
            )
        ).where(
            Verification.reviewed_at.isnot(None),
            Verification.created_at.isnot(None),
        )
    )
    avg_review_time_hours = avg_time_result.scalar_one()
    avg_review_time = round(avg_review_time_hours, 1) if avg_review_time_hours else 0

    # Approval rate
    total_decided_result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.status.in_([
                VerificationStatus.approved,
                VerificationStatus.flagged,
                VerificationStatus.rejected,
            ])
        )
    )
    total_decided = total_decided_result.scalar_one()

    if total_decided > 0:
        approved_result = await db.execute(
            select(func.count(Verification.id)).where(
                Verification.status == VerificationStatus.approved
            )
        )
        approved_count = approved_result.scalar_one()
        approval_rate = round((approved_count / total_decided) * 100, 1)
    else:
        approval_rate = 0.0

    return {
        "total_pending": total_pending,
        "reviewed_today": reviewed_today,
        "average_review_time_hours": avg_review_time,
        "approval_rate_percent": approval_rate,
        "total_decided": total_decided,
    }
