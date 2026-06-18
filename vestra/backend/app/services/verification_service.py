from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from app.models.document import Verification, VerificationStatus, Document
from app.models.property import Property
from app.models.user import User
from app.services.ai_service import analyze_property_with_ai
from app.services.property_service import get_property_by_id
from app.core.redis import cache_delete


async def create_verification_request(
    db: AsyncSession,
    property_id: int,
    requester_id: int,
    payment_id: Optional[int] = None,
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
) -> Optional[Verification]:
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
    verification.reviewed_at = datetime.now(timezone.utc)

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
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        label = month_names[(now.month - 1 - i) % 12]
        months.append({"month": label, "verifications": data.get(label, 0)})
    return months
