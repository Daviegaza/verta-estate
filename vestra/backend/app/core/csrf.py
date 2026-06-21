"""
CSRF Protection Middleware

Implements the Double-Submit Cookie pattern:
- For safe methods (GET, HEAD, OPTIONS): sets a samesite=strict CSRF token cookie.
- For state-changing methods (POST, PUT, PATCH, DELETE): validates the
  X-CSRF-Token header matches the cookie value.

Skips validation for:
  - API-key-authenticated requests (enterprise / internal)
  - M-Pesa and Stripe webhook callbacks (signed via their own schemes)
  - Requests without an origin (CLI tools, curl, etc.)
"""
from __future__ import annotations

import secrets
import logging

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger("vestra")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_COOKIE_NAME = "vestra_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SKIP_PATHS = (
    "/api/payments/mpesa/callback",
    "/api/v1/payments/mpesa/callback",
    "/api/stripe/webhook",
    "/api/v1/stripe/webhook",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.CSRF_ENABLED:
            return await call_next(request)

        # ── Skip CSRF for webhook callbacks ───────────────────────────────
        if any(request.url.path.endswith(skip) for skip in CSRF_SKIP_PATHS):
            return await call_next(request)

        # ── Skip CSRF for API-key-authenticated requests ───────────────────
        if request.headers.get("X-API-Key"):
            return await call_next(request)

        # ── Skip CSRF for requests without an Origin header ───────────────
        # (CLI tools, mobile apps, server-to-server)
        origin = request.headers.get("Origin")
        if not origin:
            return await call_next(request)

        # ── Safe methods: set CSRF cookie ─────────────────────────────────
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            self._set_csrf_cookie(request, response)
            return response

        # ── State-changing methods: validate ──────────────────────────────
        token_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        token_header = request.headers.get(CSRF_HEADER_NAME)

        if not token_cookie or not token_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "csrf_missing",
                    "message": "CSRF token missing. Refresh the page and try again.",
                },
            )

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(token_cookie, token_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "csrf_invalid",
                    "message": "CSRF token mismatch. This could be a cross-site request forgery attempt.",
                },
            )

        response = await call_next(request)
        # Rotate CSRF token after each state-changing request
        self._set_csrf_cookie(request, response)
        return response

    @staticmethod
    def _set_csrf_cookie(request: Request, response: Response) -> None:
        """Set or refresh the CSRF cookie on the response."""
        token = secrets.token_hex(32)
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=token,
            httponly=True,       # Not readable by JavaScript (defeats XSS exfiltration)
            samesite="strict",   # Never sent on cross-site requests
            secure=request.url.scheme == "https" or settings.ENVIRONMENT == "production",
            max_age=3600,        # 1 hour
            path="/",
        )
