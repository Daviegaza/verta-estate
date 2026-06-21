"""
VESTRA Monitoring API
=====================
Internal monitoring endpoints that feed the admin dashboard
with real-time system health, metrics, and alerting data.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import get_current_admin

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ── Response Models ────────────────────────────────────────────────────────────

class SystemHealth(BaseModel):
    status: str  # healthy | degraded | critical
    uptime_seconds: float
    version: str
    environment: str
    timestamp: float

class ServiceStatus(BaseModel):
    name: str
    status: str  # up | down | degraded
    latency_ms: float
    message: str | None = None

class ResourceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float

class APIMetrics(BaseModel):
    requests_per_minute: float
    avg_latency_ms: float
    p95_latency_ms: float
    error_rate_5xx: float
    error_rate_4xx: float
    active_connections: int

class BusinessMetrics(BaseModel):
    total_properties: int
    total_users: int
    total_verifications: int
    total_payments_today: int
    revenue_today_kes: float
    pending_verifications: int
    fraud_rate: float

class FullHealthResponse(BaseModel):
    system: SystemHealth
    services: list[ServiceStatus]
    resources: ResourceMetrics
    api: APIMetrics
    business: BusinessMetrics
    recent_alerts: list[dict]


# ── Helpers ────────────────────────────────────────────────────────────────────

START_TIME = time.time()


async def _check_db() -> tuple[bool, float, str]:
    """Check database connectivity and latency."""
    start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return True, round(latency, 2), None
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return False, round(latency, 2), str(e)[:200]


async def _check_redis() -> tuple[bool, float, str]:
    """Check Redis connectivity and latency."""
    start = time.perf_counter()
    try:
        r = await get_redis()
        await r.ping()
        latency = (time.perf_counter() - start) * 1000
        return True, round(latency, 2), None
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return False, round(latency, 2), str(e)[:200]


def _get_resource_metrics() -> ResourceMetrics:
    """Collect host-level resource metrics via psutil."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return ResourceMetrics(
        cpu_percent=round(cpu, 1),
        memory_percent=round(mem.percent, 1),
        memory_used_mb=round(mem.used / (1024 * 1024), 0),
        memory_total_mb=round(mem.total / (1024 * 1024), 0),
        disk_percent=round(disk.percent, 1),
        disk_free_gb=round(disk.free / (1024 * 1024 * 1024), 2),
        disk_total_gb=round(disk.total / (1024 * 1024 * 1024), 2),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/health/full", response_model=FullHealthResponse)
async def full_health_check(
    admin=Depends(get_current_admin),
):
    """
    Comprehensive system health check.
    Returns status of all services, resource metrics, and business KPIs.
    Used by the monitoring dashboard. Admin only.
    """
    # Check services
    db_ok, db_lat, db_msg = await _check_db()
    redis_ok, redis_lat, redis_msg = await _check_redis()

    services = [
        ServiceStatus(
            name="database",
            status="up" if db_ok else "down",
            latency_ms=db_lat,
            message=db_msg,
        ),
        ServiceStatus(
            name="redis",
            status="up" if redis_ok else "down",
            latency_ms=redis_lat,
            message=redis_msg,
        ),
        ServiceStatus(
            name="api",
            status="up",
            latency_ms=0,
            message="Operational",
        ),
    ]

    # Determine overall status
    if db_ok and redis_ok:
        overall = "healthy"
    elif db_ok or redis_ok:
        overall = "degraded"
    else:
        overall = "critical"

    # Resources
    resources = _get_resource_metrics()

    # Business metrics
    business = BusinessMetrics(
        total_properties=0,
        total_users=0,
        total_verifications=0,
        total_payments_today=0,
        revenue_today_kes=0.0,
        pending_verifications=0,
        fraud_rate=0.0,
    )

    # Try to get real business metrics if DB is available
    if db_ok:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import func, select

                from app.models.document import Verification
                from app.models.payment import Payment
                from app.models.property import Property
                from app.models.user import User

                business.total_properties = (await db.execute(
                    select(func.count()).select_from(Property)
                )).scalar() or 0

                business.total_users = (await db.execute(
                    select(func.count()).select_from(User)
                )).scalar() or 0

                business.total_verifications = (await db.execute(
                    select(func.count()).select_from(Verification)
                )).scalar() or 0

                today = datetime.now(UTC).date()
                payments_today = (await db.execute(
                    select(func.count(), func.sum(Payment.amount))
                    .where(func.date(Payment.created_at) == today)
                    .where(Payment.status == "completed")
                )).first()
                if payments_today:
                    business.total_payments_today = payments_today[0] or 0
                    business.revenue_today_kes = float(payments_today[1] or 0)

                business.pending_verifications = (await db.execute(
                    select(func.count())
                    .select_from(Verification)
                    .where(Verification.status == "pending")
                )).scalar() or 0
        except Exception:
            pass

    return FullHealthResponse(
        system=SystemHealth(
            status=overall,
            uptime_seconds=round(time.time() - START_TIME, 0),
            version="3.0.0",
            environment=os.getenv("ENVIRONMENT", "development"),
            timestamp=time.time(),
        ),
        services=services,
        resources=resources,
        api=APIMetrics(
            requests_per_minute=0,
            avg_latency_ms=0,
            p95_latency_ms=0,
            error_rate_5xx=0,
            error_rate_4xx=0,
            active_connections=0,
        ),
        business=business,
        recent_alerts=[],
    )


@router.get("/health/services")
async def services_status(
    admin=Depends(get_current_admin),
):
    """Lightweight check: returns status of all dependencies. Admin only."""
    db_ok, db_lat, _ = await _check_db()
    redis_ok, redis_lat, _ = await _check_redis()

    return {
        "database": {"up": db_ok, "latency_ms": db_lat},
        "redis": {"up": redis_ok, "latency_ms": redis_lat},
        "api": {"up": True},
        "checked_at": time.time(),
    }


@router.get("/health/resources")
async def resource_metrics(
    admin=Depends(get_current_admin),
):
    """Host-level resource utilization. Admin only."""
    return _get_resource_metrics().model_dump()


@router.get("/health/database")
async def database_metrics(
    admin=Depends(get_current_admin),
):
    """Database-specific metrics including connection pool and table sizes. Admin only."""
    try:
        async with AsyncSessionLocal() as db:
            # Connection count
            conns = (await db.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )).scalar()

            # Table sizes
            sizes = (await db.execute(text("""
                SELECT
                    relname AS table_name,
                    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                    pg_size_pretty(pg_relation_size(relid)) AS data_size,
                    n_live_tup AS row_count
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 20
            """))).fetchall()

            return {
                "active_connections": conns,
                "pool_size": 20,
                "max_overflow": 40,
                "tables": [
                    {
                        "name": row.table_name,
                        "size": row.total_size,
                        "data_size": row.data_size,
                        "rows": row.row_count,
                    }
                    for row in sizes
                ],
            }
    except Exception as e:
        raise HTTPException(500, f"Database metrics unavailable: {e}") from e


@router.get("/health/redis")
async def redis_metrics(
    admin=Depends(get_current_admin),
):
    """Redis-specific metrics including memory, keys, and hit rate. Admin only."""
    try:
        r = await get_redis()
        info = await r.info()

        return {
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
            "used_memory_peak_mb": round(info.get("used_memory_peak", 0) / (1024 * 1024), 2),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            "total_keys": info.get("db0", {}).get("keys", 0) if isinstance(info.get("db0"), dict) else 0,
            "hit_rate": round(
                info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100,
                1,
            ),
            "evicted_keys": info.get("evicted_keys", 0),
            "expired_keys": info.get("expired_keys", 0),
            "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
        }
    except Exception as e:
        raise HTTPException(500, f"Redis metrics unavailable: {e}") from e
