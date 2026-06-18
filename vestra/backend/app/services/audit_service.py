"""
Audit logging service — records all state-changing operations.
Used across the app to maintain a complete audit trail.
"""
from __future__ import annotations

import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("vestra")


async def log_action(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Optional[AuditLog]:
    """Record an auditable action. Best-effort — never raises."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=(ip_address or "")[:45],
            user_agent=(user_agent or "")[:500],
            correlation_id=correlation_id,
        )
        db.add(entry)
        await db.commit()
        return entry
    except Exception as e:
        logger.warning('{"event":"audit_log_failed","error":"%s"}', str(e))
        return None


async def log_user_created(db: AsyncSession, user_id: int, email: str, **kwargs) -> None:
    await log_action(db, user_id, "user.created", "user", user_id,
                     details={"email": email}, **kwargs)


async def log_user_login(db: AsyncSession, user_id: int, **kwargs) -> None:
    await log_action(db, user_id, "user.login", "user", user_id, **kwargs)


async def log_property_created(db: AsyncSession, user_id: int, property_id: int, title: str, **kwargs) -> None:
    await log_action(db, user_id, "property.created", "property", property_id,
                     details={"title": title}, **kwargs)


async def log_property_verified(db: AsyncSession, user_id: int, property_id: int,
                                 trust_score: float, recommendation: str, **kwargs) -> None:
    await log_action(db, user_id, "property.verified", "property", property_id,
                     details={"trust_score": trust_score, "recommendation": recommendation}, **kwargs)


async def log_payment_initiated(db: AsyncSession, user_id: int, payment_id: int,
                                 amount: float, purpose: str, **kwargs) -> None:
    await log_action(db, user_id, "payment.initiated", "payment", payment_id,
                     details={"amount": amount, "purpose": purpose}, **kwargs)


async def log_payment_completed(db: AsyncSession, user_id: int, payment_id: int,
                                 amount: float, method: str, **kwargs) -> None:
    await log_action(db, user_id, "payment.completed", "payment", payment_id,
                     details={"amount": amount, "method": method}, **kwargs)


async def log_admin_action(db: AsyncSession, admin_id: int, action: str,
                            resource_type: str, resource_id: int, details: dict, **kwargs) -> None:
    await log_action(db, admin_id, f"admin.{action}", resource_type, resource_id,
                     details=details, **kwargs)
