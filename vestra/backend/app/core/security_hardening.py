"""
VESTRA Security Hardening — Additional Protection Layer
========================================================
Adds: request sanitization, SQL injection guards, XSS prevention,
header validation, and advanced rate limiting patterns.
Activated automatically via middleware stack.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request

logger = logging.getLogger("vestra.security")

# ── SQL Injection Pattern Detection ──────────────────────────────────────────
SQL_INJECTION_PATTERNS = [
    r"(?i)(\bUNION\b.*\bSELECT\b)",
    r"(?i)(\bDROP\b.*\bTABLE\b)",
    r"(?i)(\bALTER\b.*\bTABLE\b)",
    r"(?i)(\bINSERT\b.*\bINTO\b)",
    r"(?i)(\bDELETE\b.*\bFROM\b)",
    r"(?i)(\bUPDATE\b.*\bSET\b)",
    r"(?i)(--\s*$)",
    r"(?i)(;\s*DROP)",
    r"(?i)(\/\*.*\*\/)",
    r"(?i)(\bEXEC\b.*\bxp_cmdshell\b)",
    r"(?i)(\bSLEEP\b\s*\()",
    r"(?i)(\bBENCHMARK\b\s*\()",
]

# ── XSS Pattern Detection ───────────────────────────────────────────────────
XSS_PATTERNS = [
    r"(?i)(<script[\s>])",
    r"(?i)(javascript\s*:)",
    r"(?i)(on\w+\s*=)",
    r"(?i)(<iframe[\s>])",
    r"(?i)(<embed[\s>])",
    r"(?i)(<object[\s>])",
    r"(?i)(expression\s*\()",
    r"(?i)(eval\s*\()",
    r"(?i)(document\.cookie)",
    r"(?i)(document\.location)",
]

# ── Path Traversal Detection ─────────────────────────────────────────────────
PATH_TRAVERSAL_PATTERNS = [
    r"\.\.\/",
    r"\.\.\\",
    r"\.\.%2f",
    r"\.\.%5c",
    r"%2e%2e%2f",
    r"%2e%2e/",
]


def contains_sql_injection(value: str) -> bool:
    """Check if a string contains SQL injection patterns."""
    return any(re.search(pattern, value) for pattern in SQL_INJECTION_PATTERNS)


def contains_xss(value: str) -> bool:
    """Check if a string contains XSS patterns."""
    return any(re.search(pattern, value) for pattern in XSS_PATTERNS)


def contains_path_traversal(value: str) -> bool:
    """Check if a string contains path traversal patterns."""
    return any(re.search(pattern, value) for pattern in PATH_TRAVERSAL_PATTERNS)


def sanitize_input(value: str) -> str:
    """Basic input sanitization — strips dangerous characters."""
    if not isinstance(value, str):
        return value
    # Strip null bytes
    value = value.replace("\x00", "")
    # Strip Unicode control characters except common whitespace
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", value)
    return value


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitize all incoming request data against common attack patterns.
    Logs and blocks suspicious requests before they reach route handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip health check and metrics endpoints
        if request.url.path in ("/health", "/health/live", "/health/ready", "/metrics"):
            return await call_next(request)

        suspicious = []

        # Check query parameters
        for key, value in request.query_params.items():
            value_str = str(value)
            if contains_sql_injection(value_str):
                suspicious.append(f"SQL injection in query param '{key}'")
            if contains_xss(value_str):
                suspicious.append(f"XSS in query param '{key}'")
            if contains_path_traversal(value_str):
                suspicious.append(f"Path traversal in query param '{key}'")

        # Check headers for suspicious patterns
        for key, value in request.headers.items():
            if key.lower() in ("user-agent", "referer", "x-forwarded-for"):
                value_str = str(value)
                if contains_sql_injection(value_str) or contains_xss(value_str):
                    suspicious.append(f"Suspicious pattern in header '{key}'")

        if suspicious:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                '{"event":"blocked_attack","ip":"%s","path":"%s","reasons":%s}',
                client_ip,
                request.url.path,
                suspicious,
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "bad_request",
                    "message": "The request contains invalid or suspicious content.",
                },
            )

        return await call_next(request)


# ── Additional Security Headers ───────────────────────────────────────────────


def get_hardened_security_headers() -> dict[str, str]:
    """Return additional security headers for maximum protection."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Download-Options": "noopen",
        "X-Permitted-Cross-Domain-Policies": "none",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
        "Cross-Origin-Embedder-Policy": "credentialless",
        "Origin-Agent-Cluster": "?1",
    }
