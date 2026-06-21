"""
Redis client and caching utilities for Vestra.
Provides connection pooling, cache decorators, and rate limiting.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time as _time
from collections import defaultdict
from contextlib import suppress
from functools import wraps
from typing import TYPE_CHECKING, Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("vestra.redis")

if TYPE_CHECKING:
    from collections.abc import Callable

# ── Connection Pool ────────────────────────────────────────────────────────────

_redis_pool: aioredis.ConnectionPool | None = None
_redis: aioredis.Redis | None = None
_redis_unavailable: bool = False  # Fast-fail flag when Redis is down


async def get_redis() -> aioredis.Redis | None:
    """
    Return a shared Redis connection (creates the pool on first call).
    Returns None if Redis is unavailable (fast-fail after first failed attempt).
    """
    global _redis_pool, _redis, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis is None:
        try:
            _redis_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                socket_connect_timeout=2,  # Fast fail — 2 seconds max
                socket_timeout=3,           # Operations timeout
            )
            _redis = aioredis.Redis(connection_pool=_redis_pool)
            await _redis.ping()
        except Exception:
            _redis_unavailable = True
            _redis = None
            _redis_pool = None
            return None
    return _redis


async def close_redis():
    """Gracefully close the Redis pool (call during shutdown)."""
    global _redis, _redis_pool
    if _redis:
        await _redis.close()
        _redis = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None


# ── Cache Helpers ──────────────────────────────────────────────────────────────

def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Build a deterministic cache key from function arguments."""
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"vestra:cache:{prefix}:{digest}"


async def cache_get(key: str) -> Any | None:
    """Get a value from the cache (JSON deserialised). Returns None on miss or error."""
    r = await get_redis()
    if r is None:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Set a value in the cache with a TTL (seconds). Fails silently if Redis down."""
    r = await get_redis()
    if r is None:
        return
    with suppress(Exception):
        await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(pattern: str) -> None:
    """Delete all keys matching a pattern. Fails silently if Redis down."""
    r = await get_redis()
    if r is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


def cached(prefix: str, ttl: int = 300):
    """Decorator: cache async function results in Redis.

    Usage:
        @cached("properties", ttl=120)
        async def get_property_by_id(db, pid):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = _make_cache_key(prefix, *args, **kwargs)
            cached_val = await cache_get(cache_key)
            if cached_val is not None:
                return cached_val
            result = await func(*args, **kwargs)
            await cache_set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


# ── Rate Limiter (Redis sliding-window + in-memory fallback) ────────────────────


class InMemoryRateLimiter:
    """
    Lock-free-ish in-memory sliding-window rate limiter.
    Used as a fallback when Redis is unavailable so rate limiting
    doesn't silently disappear.

    Not distributed — each worker maintains its own counters, so the
    effective limit is (N_workers x max_requests) during a Redis outage.
    That's acceptable: degraded protection is vastly better than none.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True if the request is within limits (sync, thread-safe)."""
        now = _time.monotonic()
        window_start = now - self.window

        with self._lock:
            bucket = self._buckets[key]
            # Prune expired entries
            while bucket and bucket[0] < window_start:
                bucket.pop(0)
            if len(bucket) < self.max_requests:
                bucket.append(now)
                return True
            return False

    def get_remaining(self, key: str) -> int:
        """Return remaining requests in the current window."""
        now = _time.monotonic()
        window_start = now - self.window

        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < window_start:
                bucket.pop(0)
            return max(0, self.max_requests - len(bucket))

    def cleanup(self) -> None:
        """Remove stale buckets older than 2x window to prevent memory leaks."""
        cutoff = _time.monotonic() - (2 * self.window)
        with self._lock:
            stale = [k for k, v in self._buckets.items() if not v or v[-1] < cutoff]
            for k in stale:
                del self._buckets[k]


class RedisRateLimiter:
    """
    Redis-based sliding-window rate limiter with in-memory fallback.

    When Redis is unavailable, falls back to InMemoryRateLimiter so rate
    limits are enforced instead of silently disappearing (fail-closed).

    Pass fail_open=True only for non-security-critical endpoints where
    availability matters more than rate limiting.
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        fail_open: bool = False,
    ):
        self.max_requests = max_requests
        self.window = window_seconds
        self.fail_open = fail_open
        self._fallback = InMemoryRateLimiter(max_requests, window_seconds)

    async def is_allowed(self, key: str) -> bool:
        """Return True if the request is within limits, False if rate-limited."""
        r = await get_redis()
        if r is None:
            return True if self.fail_open else self._fallback.is_allowed(key)
        try:
            now = asyncio.get_event_loop().time()
            window_start = now - self.window
            redis_key = f"vestra:ratelimit:{key}"

            async with r.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zcard(redis_key)
                pipe.zadd(redis_key, {str(now): now})
                pipe.expire(redis_key, self.window + 10)
                _, count, _, _ = await pipe.execute()

            return count <= self.max_requests
        except Exception:
            return True if self.fail_open else self._fallback.is_allowed(key)

    async def get_remaining(self, key: str) -> int:
        """Return remaining requests in the current window."""
        r = await get_redis()
        if r is None:
            return self.max_requests if self.fail_open else self._fallback.get_remaining(key)
        try:
            now = asyncio.get_event_loop().time()
            window_start = now - self.window
            redis_key = f"vestra:ratelimit:{key}"
            await r.zremrangebyscore(redis_key, 0, window_start)
            count = await r.zcard(redis_key)
            return max(0, self.max_requests - count)
        except Exception:
            return self.max_requests if self.fail_open else self._fallback.get_remaining(key)


# ── Session Store ──────────────────────────────────────────────────────────────

async def store_refresh_token(user_id: int, token_jti: str, ttl: int = 604800) -> None:
    """Store a refresh token in Redis (7-day default TTL)."""
    r = await get_redis()
    await r.setex(f"vestra:refresh:{user_id}:{token_jti}", ttl, "1")


async def is_refresh_token_valid(user_id: int, token_jti: str) -> bool:
    """Check if a refresh token is still valid."""
    r = await get_redis()
    return await r.exists(f"vestra:refresh:{user_id}:{token_jti}") > 0


async def revoke_all_refresh_tokens(user_id: int) -> None:
    """Revoke all refresh tokens for a user (e.g. on password change)."""
    await cache_delete(f"vestra:refresh:{user_id}:*")


# ── Deduplication (idempotency) ──────────────────────────────────────────────

async def check_and_mark_processed(key: str, ttl: int = 86400) -> bool:
    """
    Atomically check if a key has been processed and mark it as processed.
    Uses Redis SET NX (set if not exists) for atomicity across workers.
    Returns True if the key is new (proceed), False if already processed (skip).
    TTL default: 24 hours — M-Pesa callbacks can be retried for up to 24h.
    """
    r = await get_redis()
    if r is None:
        # Redis down — use a fallback in-memory set for this worker only
        if not hasattr(check_and_mark_processed, "_fallback"):
            check_and_mark_processed._fallback = set()
        fb = check_and_mark_processed._fallback
        if key in fb:
            return False
        fb.add(key)
        if len(fb) > 50000:
            fb.clear()
        return True
    try:
        # SET key value NX EX ttl — returns True only if key didn't exist
        result = await r.set(f"vestra:processed:{key}", "1", nx=True, ex=ttl)
        return result is True or result == "OK"
    except Exception:
        # Fail closed — never allow replay when Redis is in an error state.
        # A transient Redis error could otherwise let duplicate M-Pesa/Stripe
        # callbacks through, causing double-processing of payments.
        logger.error('{"event":"replay_check_failed","key":"%s"}', key)
        return False
