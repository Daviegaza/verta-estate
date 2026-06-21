"""
Production middleware: rate limiting, request logging, security headers, compression.
Uses Redis for distributed rate limiting.
"""
from __future__ import annotations

import gzip
import json as _json
import logging
import time
import uuid

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.core.config import settings
from app.core.redis import RedisRateLimiter

# ── Structured JSON logger ─────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
        return _json.dumps(log_entry, default=str)

logger = logging.getLogger("vestra")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]


# ── Rate Limiters (Redis-backed) ───────────────────────────────────────────────

auth_limiter = RedisRateLimiter(
    max_requests=settings.RATE_LIMIT_AUTH_PER_MINUTE,
    window_seconds=60,
    fail_open=False,  # Auth endpoints must never have rate limiting silently disappear
)
general_limiter = RedisRateLimiter(
    max_requests=settings.RATE_LIMIT_GENERAL_PER_MINUTE,
    window_seconds=60,
    fail_open=False,  # Enforce even during Redis outage (in-memory fallback)
)
admin_limiter = RedisRateLimiter(
    max_requests=settings.RATE_LIMIT_ADMIN_PER_MINUTE,
    window_seconds=60,
    fail_open=False,  # Admin endpoints are high-value targets
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiter with per-endpoint-type limits."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        if path.startswith("/api/auth"):
            limiter = auth_limiter
            key = f"auth:{client}"
        elif path.startswith("/api/admin"):
            limiter = admin_limiter
            key = f"admin:{client}"
        else:
            limiter = general_limiter
            key = f"general:{client}"

        allowed = await limiter.is_allowed(key)
        if not allowed:
            remaining = await limiter.get_remaining(key)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after_seconds": 60,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Remaining": str(remaining),
                },
            )

        response = await call_next(request)
        remaining = await limiter.get_remaining(key)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# ── Request Logging ────────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging with correlation IDs, timing, and slow query detection."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:12])
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        extra = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": elapsed_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "")[:200],
        }

        if elapsed_ms > 1000:
            logger.warning("Slow request: %s", _json.dumps(extra))
        else:
            logger.info("Request: %s", _json.dumps(extra))

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response


# ── Security Headers ───────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # HSTS (1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy (disable camera/mic/geolocation by default)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), "
            "payment=(self)"
        )
        # Content Security Policy
        if settings.CSP_ENABLED:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self'; "
                "frame-src https://js.stripe.com; "
                "connect-src 'self' https://api.stripe.com; "
                "form-action 'self'; "
                "base-uri 'self'; "
            )
        # Cache control for API responses (prevent caching of sensitive data)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


# ── Compression ────────────────────────────────────────────────────────────────

class GzipCompressionMiddleware(BaseHTTPMiddleware):
    """Gzip compress responses > 1KB for text-based content types."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip if client doesn't accept gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        response = await call_next(request)

        # Only compress text-based, non-streaming responses > 1KB
        content_type = response.headers.get("content-type", "")
        is_compressible = any(
            ct in content_type for ct in ("text/", "application/json", "application/javascript")
        )
        if not is_compressible or isinstance(response, StreamingResponse):
            return response

        # Safely extract response body
        body = b""
        try:
            if hasattr(response, "body"):
                raw = response.body
                if isinstance(raw, memoryview):
                    body = bytes(raw)
                elif isinstance(raw, str):
                    body = raw.encode("utf-8")
                elif isinstance(raw, (bytes, bytearray)):
                    body = bytes(raw)
        except Exception:
            pass  # Cannot read body, skip compression

        if len(body) < 1024:
            return response

        compressed = gzip.compress(body, compresslevel=6)
        # Build a new response to avoid mutating internal state
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers={
                **{k: v for k, v in response.headers.items() if k.lower() != "content-length"},
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
                "Vary": "Accept-Encoding",
            },
        )


# ── Request Size Limiter ───────────────────────────────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies larger than the configured limit."""

    MAX_BODY_SIZE = 5 * 1024 * 1024  # 5MB general limit

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds {self.MAX_BODY_SIZE // (1024*1024)}MB limit",
                },
            )
        return await call_next(request)
