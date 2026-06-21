"""
Advanced rate limiting — per-endpoint limits, burst allowance, IP reputation,
and automatic blocking of abusive IPs.

Extends the basic sliding-window rate limiter in app.core.redis with:
  - Per-endpoint configuration (cost, burst, window)
  - IP reputation scoring (bad behaviour decays over time)
  - Automatic temporary blocks for abusive IPs
  - Rich rate-limit response headers (industry standard)

Usage in middleware:
    from app.services.rate_limit_advanced import AdvancedRateLimiter
    limiter = AdvancedRate_limiter()
    result = await limiter.check("api:auth:login", client_ip, user_id=uid)
    if not result.allowed:
        raise HTTPException(status_code=429, headers=result.headers)
"""
from __future__ import annotations

import asyncio
import logging
import time as _time
from collections import defaultdict
from dataclasses import dataclass

from app.core.redis import get_redis

logger = logging.getLogger("vestra.rate_limit_advanced")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EndpointLimit:
    """Per-endpoint rate-limit configuration."""

    name: str
    """Logical name for the endpoint group (e.g. "auth:login")."""

    max_requests: int
    """Maximum requests allowed within the window (excluding burst)."""

    window_seconds: int = 60
    """Sliding window duration in seconds."""

    burst: int = 0
    """Additional requests allowed in a short burst before the hard limit kicks in."""

    burst_window: int = 5
    """Burst window in seconds."""

    cost: int = 1
    """Cost per request. Heavy endpoints (e.g. file uploads) can cost > 1."""

    block_duration: int | None = None
    """
    If set, IPs that exceed this limit get temporarily blocked for this
    many seconds (overrides the reputation-based block).
    """

    def describe(self) -> str:
        return (
            f"{self.name}: {self.max_requests}/{self.window_seconds}s"
            f" + {self.burst}/{self.burst_window}s burst"
            f" cost={self.cost}"
        )


@dataclass
class RateLimitResult:
    """Returned by every rate-limit check."""

    allowed: bool
    remaining: int
    reset_after: int
    limit: int
    retry_after: int = 0
    blocked: bool = False
    blocked_until: int = 0

    @property
    def headers(self) -> dict[str, str]:
        """Standard rate-limit response headers (RFC-compatible)."""
        h = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(_time.time() + self.reset_after)),
        }
        if self.retry_after:
            h["Retry-After"] = str(self.retry_after)
        if self.blocked:
            h["X-RateLimit-Blocked"] = "true"
            h["X-RateLimit-Blocked-Until"] = str(self.blocked_until)
        return h


# ---------------------------------------------------------------------------
# IP reputation store
# ---------------------------------------------------------------------------


class IpReputationStore:
    """
    Tracks IP reputation scores in Redis (with in-memory fallback).

    Each IP starts at 100 (neutral). Bad events (rate-limit violations, failed
    auth, suspicious patterns) deduct points. Scores decay back to 100 over
    time. IPs below a threshold are blocked.

    Score scale:
        0 -  20   Blocked (automatic or manual)
       21 -  50   Poor (aggressive limiting)
       51 -  80   Fair (tighter limits)
       81 - 120   Normal (default)
      121 - 150   Trusted (relaxed limits)
    """

    def __init__(self, redis_ttl: int = 86400):
        self._redis_ttl = redis_ttl
        self._fallback: dict[str, dict] = {}  # ip -> {"score": int, "expires": float}
        self._lock = asyncio.Lock()

    async def get_score(self, ip: str) -> int:
        """Return the current reputation score for an IP (default 100)."""
        r = await get_redis()
        if r is not None:
            try:
                val = await r.get(f"vestra:reputation:{ip}")
                return int(val) if val else 100
            except Exception:
                pass
        # In-memory fallback
        async with self._lock:
            entry = self._fallback.get(ip)
            if entry and entry["expires"] > _time.monotonic():
                return entry["score"]
        return 100

    async def adjust_score(self, ip: str, delta: int) -> int:
        """
        Adjust the reputation score for an IP by *delta* points.
        Returns the new score, clamped to [0, 150].
        """
        r = await get_redis()
        if r is not None:
            try:
                key = f"vestra:reputation:{ip}"
                new = await r.incrby(key, delta)
                new = max(0, min(150, new))
                await r.setex(key, self._redis_ttl, new)
                return new
            except Exception:
                pass
        # In-memory fallback
        async with self._lock:
            entry = self._fallback.setdefault(
                ip, {"score": 100, "expires": _time.monotonic() + 3600}
            )
            new = max(0, min(150, entry["score"] + delta))
            entry["score"] = new
            entry["expires"] = _time.monotonic() + 3600
            return new

    async def decay_scores(self) -> int:
        """
        Periodically decay all scores back toward 100 by 1 point.
        Returns the number of IPs decayed. Called by a background task.
        """
        r = await get_redis()
        if r is not None:
            try:
                cursor = 0
                decayed = 0
                while True:
                    cursor, keys = await r.scan(
                        cursor, match="vestra:reputation:*", count=500
                    )
                    for key in keys:
                        current = int(await r.get(key) or 100)
                        if current > 100:
                            await r.decr(key, 1)
                            decayed += 1
                        elif current < 100:
                            await r.incr(key, 1)
                            decayed += 1
                    if cursor == 0:
                        break
                return decayed
            except Exception:
                pass
        # In-memory fallback — scan and decay
        async with self._lock:
            now = _time.monotonic()
            decayed = 0
            stale = []
            for ip, entry in self._fallback.items():
                if entry["expires"] < now:
                    stale.append(ip)
                    continue
                s = entry["score"]
                if s > 100:
                    entry["score"] = s - 1
                    decayed += 1
                elif s < 100:
                    entry["score"] = s + 1
                    decayed += 1
            for ip in stale:
                del self._fallback[ip]
        return decayed

    async def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked (score <= 20)."""
        score = await self.get_score(ip)
        return score <= 20

    async def block_ip(self, ip: str, ttl: int = 3600) -> None:
        """Manually block an IP (set score to 0)."""
        r = await get_redis()
        if r is not None:
            await r.setex(f"vestra:reputation:{ip}", ttl, 0)
        else:
            async with self._lock:
                self._fallback[ip] = {"score": 0, "expires": _time.monotonic() + ttl}


# ---------------------------------------------------------------------------
# Sliding-window counter (Redis sorted-set + in-memory fallback)
# ---------------------------------------------------------------------------


class _SlidingWindowCounter:
    """Per-key sliding-window counter using Redis sorted sets."""

    def __init__(self, prefix: str = "vestra:ratelimit_v2"):
        self._prefix = prefix
        self._fallback: dict[str, list[float]] = defaultdict(list)
        self._fb_lock = asyncio.Lock()

    async def count_and_check(
        self, key: str, limit: int, window: int, cost: int = 1
    ) -> tuple[int, int]:
        """
        Atomically record *cost* tokens and return (count_in_window, reset_after).
        Returns (-1, 0) if the operation should be rejected.
        """
        r = await get_redis()
        if r is not None:
            try:
                now = asyncio.get_event_loop().time()
                redis_key = f"{self._prefix}:{key}"
                min_score = now - window

                async with r.pipeline(transaction=True) as pipe:
                    pipe.zremrangebyscore(redis_key, 0, min_score)
                    pipe.zcard(redis_key)
                    pipe.zadd(redis_key, {str(now + i): now + i for i in range(cost)})
                    pipe.expire(redis_key, window + 10)
                    _, count, _, _ = await pipe.execute()

                return count, window
            except Exception:
                pass

        # In-memory fallback
        async with self._fb_lock:
            now = _time.monotonic()
            bucket = self._fallback[key]
            cutoff = now - window
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            count = len(bucket)
            for _ in range(cost):
                bucket.append(now)
            return count, window


# ---------------------------------------------------------------------------
# Advanced rate limiter
# ---------------------------------------------------------------------------


_reputation_store: IpReputationStore | None = None
_counter: _SlidingWindowCounter | None = None


def _ensure_globals():
    global _reputation_store, _counter
    if _reputation_store is None:
        _reputation_store = IpReputationStore()
    if _counter is None:
        _counter = _SlidingWindowCounter()


class AdvancedRateLimiter:
    """
    Per-endpoint rate limiter with burst, reputation, and auto-block.

    Usage:
        limiter = AdvancedRateLimiter()

        # Define endpoint limits
        limiter.register(EndpointLimit("auth:login", max_requests=10, window_seconds=60, burst=5))
        limiter.register(EndpointLimit("api:general", max_requests=120, window_seconds=60, burst=20))
        limiter.register(EndpointLimit("admin:panel", max_requests=300, window_seconds=60))

        # Check a request
        result = await limiter.check("auth:login", client_ip, user_id=user.id)
    """

    def __init__(self):
        _ensure_globals()
        self._reputation = _reputation_store
        self._counter = _counter
        self._endpoints: dict[str, EndpointLimit] = {}
        self._blocks: dict[str, tuple[float, int]] = {}  # ip -> (expires_at, reason)
        self._block_lock = asyncio.Lock()

    # -- Configuration ------------------------------------------------------

    def register(self, limit: EndpointLimit) -> None:
        """Register an endpoint limit configuration."""
        self._endpoints[limit.name] = limit
        logger.info('{"event":"ratelimit_registered","endpoint":"%s","config":"%s"}',
                     limit.name, limit.describe())

    def register_many(self, limits: list[EndpointLimit]) -> None:
        """Register multiple endpoint limits."""
        for limit in limits:
            self.register(limit)

    def get_limit(self, endpoint: str) -> EndpointLimit | None:
        """Look up the limit configuration for an endpoint."""
        return self._endpoints.get(endpoint)

    # -- Core check ---------------------------------------------------------

    async def check(
        self,
        endpoint: str,
        client_ip: str,
        user_id: int | None = None,
        cost: int | None = None,
    ) -> RateLimitResult:
        """
        Check whether a request is allowed.

        Args:
            endpoint: Endpoint name matching a registered EndpointLimit.
            client_ip: The client's IP address.
            user_id: Optional user ID for reputation tracking.
            cost: Override the per-request cost (defaults to EndpointLimit.cost).

        Returns:
            RateLimitResult with .allowed, .remaining, .headers, etc.
        """
        limit = self._endpoints.get(endpoint)
        if limit is None:
            # Unknown endpoint — allow with a warning
            logger.warning('{"event":"ratelimit_unknown_endpoint","endpoint":"%s"}', endpoint)
            return RateLimitResult(
                allowed=True, remaining=9999, reset_after=1, limit=9999,
            )

        effective_cost = cost if cost is not None else limit.cost

        # 1. Check IP block list (fast path)
        if await self._reputation.is_blocked(client_ip):
            return RateLimitResult(
                allowed=False, remaining=0, reset_after=3600,
                limit=limit.max_requests, retry_after=3600,
                blocked=True, blocked_until=int(_time.time() + 3600),
            )

        # 2. Check IP reputation — adjust limits for poor-reputation IPs
        score = await self._reputation.get_score(client_ip)
        adjusted_limit = self._apply_reputation(limit.max_requests, score)

        # 3. Check burst bucket first
        burst_key = f"{endpoint}:burst:{client_ip}"
        burst_remaining = limit.burst
        if limit.burst > 0:
            burst_count, _ = await self._counter.count_and_check(
                burst_key, limit.burst, limit.burst_window, effective_cost,
            )
            # If burst was used up, fall through to the main window
            if burst_count <= limit.burst:
                burst_remaining = max(0, limit.burst - burst_count)

        # 4. Check main sliding window
        window_key = f"{endpoint}:win:{client_ip}"
        window_count, reset_after = await self._counter.count_and_check(
            window_key, adjusted_limit, limit.window_seconds, effective_cost,
        )

        within_main = window_count <= adjusted_limit
        within_burst = burst_remaining > 0
        allowed = within_main or within_burst

        # 5. Enforce hard block for repeated violations
        if not allowed:
            await self._reputation.adjust_score(client_ip, -10)
            score = await self._reputation.get_score(client_ip)

            if limit.block_duration and window_count > adjusted_limit * 2:
                await self._reputation.block_ip(client_ip, limit.block_duration)
                logger.warning(
                    '{"event":"ratelimit_ip_blocked","ip":"%s","endpoint":"%s",'
                    '"score":%d,"duration":%d}',
                    client_ip, endpoint, score, limit.block_duration,
                )
                return RateLimitResult(
                    allowed=False, remaining=0, reset_after=limit.block_duration,
                    limit=adjusted_limit, retry_after=limit.block_duration,
                    blocked=True, blocked_until=int(_time.time() + limit.block_duration),
                )

        # 6. Build result
        remaining = max(0, adjusted_limit - window_count) + burst_remaining
        retry_after = 0
        if not allowed:
            # How long until the window resets enough?
            retry_after = max(1, reset_after)

        result = RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_after=reset_after,
            limit=adjusted_limit,
            retry_after=retry_after,
            blocked=False,
        )

        # Log at INFO if close to limit, WARNING if exceeded
        usage_pct = (window_count / max(adjusted_limit, 1)) * 100
        if not allowed:
            logger.warning(
                '{"event":"ratelimit_exceeded","endpoint":"%s","ip":"%s",'
                '"user_id":%s,"count":%d,"limit":%d,"score":%d}',
                endpoint, client_ip, str(user_id), window_count, adjusted_limit, score,
            )
        elif usage_pct > 80:
            logger.info(
                '{"event":"ratelimit_approaching","endpoint":"%s","ip":"%s",'
                '"count":%d,"limit":%d,"usage_pct":%.0f}',
                endpoint, client_ip, window_count, adjusted_limit, usage_pct,
            )

        return result

    # -- Reputation helpers --------------------------------------------------

    @staticmethod
    def _apply_reputation(base_limit: int, score: int) -> int:
        """
        Adjust the base rate limit based on IP reputation.

        - Score 0-20: blocked (handled separately above)
        - Score 21-50: 50% of base limit
        - Score 51-80: 80% of base limit
        - Score 81-120: 100% of base limit (normal)
        - Score 121-150: 150% of base limit (trusted)
        """
        if score <= 20:
            return 0
        if score <= 50:
            return max(1, int(base_limit * 0.5))
        if score <= 80:
            return max(1, int(base_limit * 0.8))
        if score >= 120:
            return int(base_limit * 1.5)
        return base_limit

    async def report_bad_event(self, ip: str, reason: str = "") -> None:
        """
        Report a bad event from this IP (failed auth, suspicious pattern, etc.).
        Deducts 20 reputation points. If the score drops below 21, the IP is
        automatically blocked for 30 minutes.
        """
        new_score = await self._reputation.adjust_score(ip, -20)
        logger.info(
            '{"event":"ratelimit_bad_event","ip":"%s","reason":"%s","new_score":%d}',
            ip, reason, new_score,
        )
        if new_score <= 20:
            await self._reputation.block_ip(ip, ttl=1800)
            logger.warning(
                '{"event":"ratelimit_auto_blocked","ip":"%s","reason":"%s","score":%d}',
                ip, reason, new_score,
            )

    async def report_good_event(self, ip: str, reason: str = "") -> None:
        """Report a good event (successful auth, valid action). Adds 5 points."""
        await self._reputation.adjust_score(ip, 5)

    async def decay_all(self) -> int:
        """Decay all reputation scores toward 100. Returns count decayed."""
        return await self._reputation.decay_scores()

    # -- Manual block / unblock ---------------------------------------------

    async def block_ip(self, ip: str, duration: int = 3600, reason: str = "manual") -> None:
        """Manually block an IP address."""
        await self._reputation.block_ip(ip, ttl=duration)
        logger.warning(
            '{"event":"ratelimit_manual_block","ip":"%s","duration":%d,"reason":"%s"}',
            ip, duration, reason,
        )

    async def unblock_ip(self, ip: str) -> None:
        """Unblock an IP address (reset reputation to 100)."""
        r = await get_redis()
        if r is not None:
            await r.delete(f"vestra:reputation:{ip}")
        async with self._reputation._lock:
            self._reputation._fallback.pop(ip, None)
        logger.info('{"event":"ratelimit_unblock","ip":"%s"}', ip)

    async def get_ip_status(self, ip: str) -> dict:
        """Return reputation status for an IP (for admin dashboard)."""
        score = await self._reputation.get_score(ip)
        return {
            "ip": ip,
            "score": score,
            "blocked": score <= 20,
            "level": "blocked" if score <= 20
            else "poor" if score <= 50
            else "fair" if score <= 80
            else "normal" if score <= 120
            else "trusted",
        }


# ---------------------------------------------------------------------------
# Singleton + default registration
# ---------------------------------------------------------------------------

_limiter: AdvancedRateLimiter | None = None


def get_advanced_limiter() -> AdvancedRateLimiter:
    """Return the application-wide AdvancedRateLimiter singleton."""
    global _limiter
    if _limiter is None:
        _limiter = AdvancedRateLimiter()
        _limiter.register_many([
            EndpointLimit(
                name="auth:login", max_requests=10, window_seconds=60,
                burst=5, block_duration=900,
            ),
            EndpointLimit(
                name="auth:register", max_requests=5, window_seconds=60,
                burst=2, block_duration=1800,
            ),
            EndpointLimit(
                name="auth:password_reset", max_requests=3, window_seconds=300,
                burst=1, block_duration=3600,
            ),
            EndpointLimit(
                name="api:general", max_requests=120, window_seconds=60,
                burst=20,
            ),
            EndpointLimit(
                name="api:search", max_requests=60, window_seconds=60,
                burst=10,
            ),
            EndpointLimit(
                name="api:property_detail", max_requests=200, window_seconds=60,
                burst=30,
            ),
            EndpointLimit(
                name="api:uploads", max_requests=20, window_seconds=60,
                cost=5, burst=3,
            ),
            EndpointLimit(
                name="api:payments", max_requests=30, window_seconds=60,
                burst=5, block_duration=600,
            ),
            EndpointLimit(
                name="admin:panel", max_requests=300, window_seconds=60,
                burst=50,
            ),
            EndpointLimit(
                name="admin:audit", max_requests=100, window_seconds=60,
                burst=20,
            ),
            EndpointLimit(
                name="webhook:inbound", max_requests=200, window_seconds=60,
                burst=40,
            ),
        ])
    return _limiter


async def run_decay_cycle(interval_seconds: int = 300) -> None:
    """
    Background coroutine that periodically decays reputation scores.
    Run as a standalone asyncio task at startup:

        asyncio.create_task(run_decay_cycle())
    """
    limiter = get_advanced_limiter()
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            count = await limiter.decay_all()
            if count:
                logger.debug('{"event":"ratelimit_decay","decayed":%d}', count)
        except Exception as e:
            logger.error('{"event":"ratelimit_decay_error","error":"%s"}', str(e)[:200])
