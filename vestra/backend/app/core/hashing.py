"""
Async bcrypt hashing — prevents event-loop blocking.

bcrypt.checkpw and bcrypt.hashpw are CPU-bound and can block the asyncio
event loop for 100-500ms per call on production hardware. Under load, this
cascades into request timeouts. All bcrypt calls go through the default
ThreadPoolExecutor so the event loop stays free.

Usage (drop-in replacement):
    from app.core.hashing import verify_password, get_password_hash

    is_valid = await verify_password(plain, hashed)
    new_hash = await get_password_hash(plain)
"""
from __future__ import annotations

import asyncio

import bcrypt


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash — async, non-blocking."""
    loop = asyncio.get_event_loop()

    def _check() -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    return await loop.run_in_executor(None, _check)


async def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt — async, non-blocking."""
    loop = asyncio.get_event_loop()

    def _hash() -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

    return await loop.run_in_executor(None, _hash)
