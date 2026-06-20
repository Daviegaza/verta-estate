"""Unit tests for Redis utilities — rate limiter, caching, idempotency."""
from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.core.redis import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    _make_cache_key,
    check_and_mark_processed,
)


# ── InMemoryRateLimiter Tests ─────────────────────────────────────────────────

class TestInMemoryRateLimiter:
    def test_allows_first_request(self):
        limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
        assert limiter.is_allowed("client-1") is True

    def test_allows_up_to_limit(self):
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("client-1") is True

    def test_blocks_over_limit(self):
        limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False

    def test_different_keys_independent(self):
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        # Exhaust client-1
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False
        # client-2 should still be allowed
        assert limiter.is_allowed("client-2") is True

    def test_get_remaining_counts_correctly(self):
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        assert limiter.get_remaining("client-1") == 5
        limiter.is_allowed("client-1")
        assert limiter.get_remaining("client-1") == 4
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")
        assert limiter.get_remaining("client-1") == 2

    def test_window_expires(self):
        """After the window passes, the bucket should reset."""
        import time as _time
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=1)
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False  # At limit
        # Wait for the window to expire
        _time.sleep(1.1)
        # Now the window has passed — should be allowed again
        assert limiter.is_allowed("client-1") is True

    def test_cleanup_removes_stale_buckets(self):
        import time as _time
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=0.1)
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-2")
        assert len(limiter._buckets) >= 2
        # Wait for 2x window to expire so cleanup removes them
        _time.sleep(0.3)
        limiter.cleanup()
        assert len(limiter._buckets) == 0

    def test_thread_safety(self):
        import threading
        limiter = InMemoryRateLimiter(max_requests=100, window_seconds=60)
        results = []
        errors = []

        def hammer(key):
            try:
                for _ in range(100):
                    limiter.is_allowed(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=hammer, args=(f"client-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


# ── RedisRateLimiter Tests (with mocked Redis) ────────────────────────────────

class TestRedisRateLimiterWithMock:
    @pytest.mark.asyncio
    async def test_fail_open_true_returns_allowed_when_redis_down(self):
        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=None)):
            limiter = RedisRateLimiter(max_requests=10, fail_open=True)
            assert await limiter.is_allowed("any-key") is True
            assert await limiter.get_remaining("any-key") == 10

    @pytest.mark.asyncio
    async def test_fail_open_false_uses_fallback_when_redis_down(self):
        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=None)):
            limiter = RedisRateLimiter(max_requests=3, fail_open=False)
            # Should use InMemoryRateLimiter fallback
            for _ in range(3):
                assert await limiter.is_allowed("key") is True
            assert await limiter.is_allowed("key") is False

    @pytest.mark.asyncio
    async def test_fallback_remaining_count(self):
        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=None)):
            limiter = RedisRateLimiter(max_requests=5, fail_open=False)
            assert await limiter.get_remaining("key") == 5
            await limiter.is_allowed("key")
            await limiter.is_allowed("key")
            assert await limiter.get_remaining("key") == 3

    @pytest.mark.asyncio
    async def test_redis_exception_falls_back(self):
        """When Redis raises an exception, fallback should be used."""
        mock_redis = AsyncMock()
        mock_redis.pipeline.side_effect = RuntimeError("Connection lost")

        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=mock_redis)):
            limiter = RedisRateLimiter(max_requests=3, fail_open=False)
            # Should fall back to in-memory — allow up to 3
            for _ in range(3):
                assert await limiter.is_allowed("key") is True
            assert await limiter.is_allowed("key") is False


# ── Cache Key Tests ───────────────────────────────────────────────────────────

class TestCacheKey:
    def test_same_args_same_key(self):
        k1 = _make_cache_key("test", 1, 2, x=3)
        k2 = _make_cache_key("test", 1, 2, x=3)
        assert k1 == k2

    def test_different_args_different_key(self):
        k1 = _make_cache_key("test", 1, 2)
        k2 = _make_cache_key("test", 1, 3)
        assert k1 != k2

    def test_different_prefix_different_key(self):
        k1 = _make_cache_key("a", 1)
        k2 = _make_cache_key("b", 1)
        assert k1 != k2

    def test_key_starts_with_vestra_prefix(self):
        key = _make_cache_key("properties", id=42)
        assert key.startswith("vestra:cache:properties:")

    def test_kwargs_order_independent(self):
        k1 = _make_cache_key("test", a=1, b=2)
        k2 = _make_cache_key("test", b=2, a=1)
        assert k1 == k2


# ── Idempotency Tests ─────────────────────────────────────────────────────────

class TestIdempotency:
    def test_fallback_set_memory(self):
        """When Redis is down, fallback to in-memory set works."""
        # Clear any prior fallback state
        if hasattr(check_and_mark_processed, "_fallback"):
            check_and_mark_processed._fallback.clear()
        else:
            check_and_mark_processed._fallback = set()

        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=None)):
            import asyncio
            result1 = asyncio.get_event_loop().run_until_complete(
                check_and_mark_processed("test-key-1")
            )
            result2 = asyncio.get_event_loop().run_until_complete(
                check_and_mark_processed("test-key-1")
            )
            assert result1 is True   # First time — allowed
            assert result2 is False  # Second time — duplicate

    def test_fallback_set_cleanup(self):
        """Fallback set should clean up when it grows too large."""
        with patch("app.core.redis.get_redis", new=AsyncMock(return_value=None)):
            # Initialize a large set
            check_and_mark_processed._fallback = {str(i) for i in range(60000)}
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                check_and_mark_processed("new-key")
            )
            assert result is True
            # Set should have been cleared
            assert len(check_and_mark_processed._fallback) < 50000
