"""
CSRF Protection Middleware

Implements the Double-Submit Cookie pattern:
- For safe methods (GET, HEAD, OPTIONS): sets a samesite=strict CSRF token cookie.
- For state-changing methods (POST, PUT, PATCH, DELETE): validates the
  X-CSRF-Token header matches the cookie value.

Exemptions (pre-auth + webhooks):
  - All /auth/* endpoints (login, register, OTP, password reset, 2FA)
  - M-Pesa and Stripe webhook callbacks
  - API-key-authenticated requests (enterprise / internal)
  - Requests without an Origin header (CLI tools, mobile apps)
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings

if TYPE_CHECKING:
    from starlette.responses import Response

logger = logging.getLogger("vestra")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_COOKIE_NAME = "vestra_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# All auth endpoints are exempt — the user has no session yet, so there is
# nothing for CSRF to protect.  CSRF only matters *after* authentication.
AUTH_PATH_PREFIXES = (
    "/api/auth/",
    "/api/v1/auth/",
)

# Webhook endpoints use their own signing schemes (M-Pesa, Stripe).
WEBHOOK_PATHS = (
    "/api/payments/mpesa/callback",
    "/api/v1/payments/mpesa/callback",
    "/api/stripe/webhook",
    "/api/v1/stripe/webhook",
)


def _is_csrf_exempt(path: str) -> bool:
    """Return True if the path should skip CSRF validation."""
    if any(path.startswith(p) for p in AUTH_PATH_PREFIXES):
        return True
    if path in WEBHOOK_PATHS:
        return True
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.CSRF_ENABLED:
            return await call_next(request)

        path = request.url.path

        # ── Skip CSRF for auth endpoints and webhook callbacks ──────────────
        if _is_csrf_exempt(path):
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
            httponly=False,      # Must be readable by JS to send back as X-CSRF-Token header
            samesite="strict",   # Never sent on cross-site requests (prevents CSRF)
            secure=request.url.scheme == "https" or settings.ENVIRONMENT == "production",
            max_age=3600,        # 1 hour
            path="/",
        )
