"""
Vestra API — Main Application
=============================
AI-Powered Property Trust & Operating System for Africa.
Production-ready FastAPI application with Redis caching,
structured logging, rate limiting, and comprehensive monitoring.
"""
from __future__ import annotations

import os
import time
import logging
from contextlib import asynccontextmanager
from decimal import Decimal

import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from starlette.exceptions import HTTPException as StarletteHTTPException

# ── Custom JSON encoder — handles Decimal from PostgreSQL Numeric columns ──
import json as _json


def _json_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class DecimalAwareJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return _json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=_json_serializer,
        ).encode("utf-8")

from app.core.config import settings
from app.core.database import create_tables, AsyncSessionLocal, engine
from app.core.redis import get_redis, close_redis
from app.core.metrics import metrics_endpoint, metrics_middleware
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    GzipCompressionMiddleware,
    RequestSizeLimitMiddleware,
)
from app.core.indexes import create_performance_indexes
from app.api import api_router, legacy_router

logger = logging.getLogger("vestra")


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    # IMPORTANT: In production, run `alembic upgrade head` before starting the app.
    # Schema is managed through Alembic migrations — not auto-created.
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await create_tables()

    # Ensure performance indexes
    async with AsyncSessionLocal() as db:
        await create_performance_indexes(db)

    # Warm Redis connection
    try:
        r = await get_redis()
        await r.ping()
        logger.info('{"event":"startup","redis":"connected"}')
    except Exception:
        logger.warning('{"event":"startup","redis":"unavailable — caching disabled"}')

    # Initialize Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            environment=settings.ENVIRONMENT,
            release=settings.APP_VERSION,
            traces_sample_rate=(
                settings.SENTRY_TRACES_SAMPLE_RATE
                if settings.ENVIRONMENT == "production"
                else 1.0
            ),
            profiles_sample_rate=0.1,
        )
        logger.info(
            '{"event":"startup","sentry":"enabled","env":"%s"}',
            settings.ENVIRONMENT,
        )

    logger.info(
        '{"event":"startup","app":"%s","version":"%s","env":"%s"}',
        settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT,
    )
    yield

    # ── Shutdown ──
    await close_redis()
    try:
        from app.services.mpesa_service import close_mpesa_client
        await close_mpesa_client()
    except Exception:
        pass
    await engine.dispose()
    logger.info('{"event":"shutdown","app":"%s"}', settings.APP_NAME)


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Vestra API",
    description="AI-Powered Property Trust & Operating System for Africa",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    default_response_class=DecimalAwareJSONResponse,
)

# ── Middleware Stack (applied in order — first added = outermost) ───────────────

# 1. Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request size limit
app.add_middleware(RequestSizeLimitMiddleware)

# 3. Rate limiting (Redis-backed)
app.add_middleware(RateLimitMiddleware)

# 4. Compression
app.add_middleware(GzipCompressionMiddleware)

# 5. Prometheus metrics tracking
app.middleware("http")(metrics_middleware)

# 6. Structured request logging
app.add_middleware(RequestLoggingMiddleware)

# 7. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-RateLimit-Remaining", "X-Response-Time-Ms"],
    max_age=3600,
)

# ── API Deprecation Middleware ───────────────────────────────────────────────────
# Adds deprecation headers to unversioned /api/* paths (not /api/v1/*).
# Clients should migrate to the canonical /api/v1/ prefix.

@app.middleware("http")
async def api_deprecation_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/v1/"):
        response.headers["X-API-Deprecated"] = "true"
        response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
        logger.warning(
            '{"event":"deprecated_api_call","path":"%s","method":"%s"}',
            path, request.method,
        )
    return response


# ── API Key Tracking Middleware ─────────────────────────────────────────────────
# Intercepts enterprise routes, validates X-API-Key headers, tracks usage,
# and enforces per-key rate limits. Non-enterprise routes pass through.

@app.middleware("http")
async def api_key_tracking_middleware(request: Request, call_next):
    """Track API key usage for enterprise endpoints from X-API-Key header."""
    path = request.url.path
    is_enterprise = "/enterprise/" in path

    if not is_enterprise:
        return await call_next(request)

    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return await call_next(request)

    # ── Validate and track (non-blocking — the route dependency handles auth) ──
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as mid_db:
            from app.services.api_key_service import validate_api_key, record_api_key_usage
            from app.core.redis import get_redis

            key = await validate_api_key(mid_db, api_key_header)
            if key:
                # Track usage asynchronously
                await record_api_key_usage(
                    mid_db, key.id, endpoint=path, response_status=200, response_time_ms=0.0,
                )

                # Enforce rate limit
                from app.core.redis import RedisRateLimiter
                limiter = RedisRateLimiter(max_requests=key.rate_limit_per_min, window_seconds=60)
                allowed = await limiter.is_allowed(f"api_key:{key.id}")
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": f"Max {key.rate_limit_per_min} requests per minute exceeded.",
                        },
                    )
    except Exception:
        logger.warning('{"event":"api_key_middleware_error","path":"%s"}', path)

    response = await call_next(request)
    return response


# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(api_router)
app.include_router(legacy_router)

# Prometheus metrics endpoint (secured in production via reverse proxy)
app.add_route("/metrics", metrics_endpoint, methods=["GET"])

# ── Static Files ───────────────────────────────────────────────────────────────

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Global Exception Handlers ──────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Consistent JSON error responses for all HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": _error_code_for_status(exc.status_code),
            "message": str(exc.detail),
            "path": request.url.path,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(HTTPException)
async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException with structured detail."""
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        error_code = detail.get("error", _error_code_for_status(exc.status_code))
    else:
        message = str(detail)
        error_code = _error_code_for_status(exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": message,
            "path": request.url.path,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors gracefully."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": str(exc),
            "path": request.url.path,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions. Logs full traceback."""
    logger.error(
        '{"event":"unhandled_error","path":"%s","error":"%s"}',
        request.url.path, str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Our team has been notified.",
            "path": request.url.path,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


# ── Root & Health ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else None,
        "description": "Africa's most trusted property platform",
    }


@app.get("/health")
async def health():
    """Detailed health check with dependency status."""
    health_data = {
        "status": "healthy",
        "service": "vestra-api",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }

    # Check database
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        health_data["database"] = "connected"
    except Exception as e:
        health_data["database"] = f"error: {str(e)[:100]}"
        health_data["status"] = "degraded"

    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
        health_data["redis"] = "connected"
    except Exception:
        health_data["redis"] = "unavailable"
        health_data["status"] = "degraded"

    return health_data


@app.get("/health/live")
async def liveness():
    """Kubernetes liveness probe — minimal check."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe — checks dependencies."""
    ready = True
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        ready = False
    return {"status": "ready" if ready else "not_ready"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_code_for_status(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "http_error")
