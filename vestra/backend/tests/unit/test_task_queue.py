"""Unit tests for the durable task queue."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call

from app.core.task_queue import (
    enqueue,
    TASK_CONFIGS,
    DEFAULT_TASK_CONFIG,
    STREAM_EVENTS,
    STREAM_DEAD_LETTER,
    register_handler,
    _handlers,
)


# ── Enqueue Tests ─────────────────────────────────────────────────────────────

class TestEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_returns_message_id(self):
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1234567890-0"

        with patch("app.core.task_queue.get_redis", new=AsyncMock(return_value=mock_redis)):
            msg_id = await enqueue("notification", {"user_id": 42, "text": "hello"})
            assert msg_id == "1234567890-0"
            mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_none_when_redis_down(self):
        with patch("app.core.task_queue.get_redis", new=AsyncMock(return_value=None)):
            msg_id = await enqueue("notification", {"user_id": 42})
            assert msg_id is None

    @pytest.mark.asyncio
    async def test_enqueue_exception_returns_none(self):
        mock_redis = AsyncMock()
        mock_redis.xadd.side_effect = RuntimeError("Redis error")

        with patch("app.core.task_queue.get_redis", new=AsyncMock(return_value=mock_redis)):
            msg_id = await enqueue("notification", {"user_id": 42})
            assert msg_id is None

    @pytest.mark.asyncio
    async def test_enqueue_includes_task_metadata(self):
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "id-1"

        with patch("app.core.task_queue.get_redis", new=AsyncMock(return_value=mock_redis)):
            await enqueue("notification", {"user_id": 42})

        call_args = mock_redis.xadd.call_args
        message = call_args[0][1]  # Second positional arg is the message dict
        assert message["task_type"] == "notification"
        assert "payload" in message
        assert "attempt" in message
        assert "max_retries" in message
        assert "created_at" in message

    @pytest.mark.asyncio
    async def test_enqueue_uses_stream_maxlen(self):
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "id-1"

        with patch("app.core.task_queue.get_redis", new=AsyncMock(return_value=mock_redis)):
            await enqueue("notification", {"x": 1})

        # Should include maxlen parameter
        _, kwargs = mock_redis.xadd.call_args
        assert "maxlen" in kwargs


# ── Task Config Tests ─────────────────────────────────────────────────────────

class TestTaskConfigs:
    def test_all_registered_tasks_have_config(self):
        registered = {"notification", "email", "webhook", "analytics", "cleanup", "report", "lifecycle_notifications"}
        for task_type in registered:
            config = TASK_CONFIGS.get(task_type, DEFAULT_TASK_CONFIG)
            assert config[0] > 0, f"{task_type}: max_retries must be > 0"
            assert config[1] > 0, f"{task_type}: backoff must be > 0"

    def test_default_config_is_reasonable(self):
        assert DEFAULT_TASK_CONFIG[0] >= 1  # At least 1 retry
        assert DEFAULT_TASK_CONFIG[1] >= 0.5  # Reasonable backoff


# ── Handler Registration Tests ───────────────────────────────────────────────

class TestHandlerRegistration:
    def test_register_handler_decorator(self):
        was_called = []

        @register_handler("test_task")
        async def handler(**kwargs):
            was_called.append(kwargs)

        assert "test_task" in _handlers
        assert _handlers["test_task"] is handler

    def test_notification_handler_registered(self):
        assert "notification" in _handlers, "notification handler should be registered on import"

    def test_webhook_handler_registered(self):
        assert "webhook" in _handlers, "webhook handler should be registered on import"

    def test_email_handler_registered(self):
        assert "email" in _handlers, "email handler should be registered on import"

    def test_analytics_handler_registered(self):
        assert "analytics" in _handlers, "analytics handler should be registered on import"

    def test_cleanup_handler_registered(self):
        assert "cleanup" in _handlers, "cleanup handler should be registered on import"

    def test_lifecycle_notifications_handler_registered(self):
        assert "lifecycle_notifications" in _handlers, \
            "lifecycle_notifications handler should be registered on import"
