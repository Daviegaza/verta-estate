"""
CAPTCHA verification service using Cloudflare Turnstile (free tier).
Validates user-submitted tokens against Cloudflare's siteverify endpoint.
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("vestra")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str) -> bool:
    """
    Verify a Cloudflare Turnstile token.
    Returns True if the token is valid, False otherwise.

    In development (no key configured), always returns True.
    """
    if not settings.TURNSTILE_SECRET_KEY:
        if settings.ENVIRONMENT == "production":
            logger.error('{"event":"turnstile_not_configured","environment":"production"}')
            return False
        # Development/test — skip CAPTCHA if not configured
        return True

    if not token:
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": token,
                },
            )
            result = response.json()
            success = result.get("success", False)

            if not success:
                logger.warning(
                    '{"event":"turnstile_verification_failed","errors":"%s"}',
                    result.get("error-codes", []),
                )

            return success
    except Exception as e:
        logger.error('{"event":"turnstile_error","error":"%s"}', str(e))
        # Fail open in non-production to avoid blocking dev
        if settings.ENVIRONMENT != "production":
            return True
        return False
