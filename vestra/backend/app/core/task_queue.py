"""
Durable Message Queue — Redis Streams backend.

Replaces fire-and-forget asyncio.create_task with a persistent, retryable,
horizontally-scalable message queue. Events survive process crashes and
are picked up by any available worker.

Architecture:
    Producer (web process) ──► Redis Stream ──► Consumer Group (workers)
                                │
                                ▼
                          Dead-Letter Stream (failed after N retries)

Usage:
    # Producer (in web request handler or service)
    from app.core.task_queue import enqueue
    await enqueue("notification", {"user_id": 42, "type": "welcome"})

    # Consumer (worker.py)
    from app.core.task_queue import start_workers
    await start_workers()
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Coroutine, Optional

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("vestra.task_queue")

# ── Stream keys ──────────────────────────────────────────────────────────────
STREAM_EVENTS = "vestra:stream:events"
STREAM_DEAD_LETTER = "vestra:stream:dead"
GROUP_NAME = "vestra-workers"
CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:8]}"

# Per-task-type config: (max_retries, base_backoff_seconds)
TASK_CONFIGS: dict[str, tuple[int, float]] = {
    "notification": (3, 1.0),
    "webhook": (3, 2.0),
    "email": (3, 1.0),
    "report": (2, 5.0),
    "analytics": (1, 0.5),
    "cleanup": (2, 10.0),
}
DEFAULT_TASK_CONFIG = (3, 1.0)  # (max_retries, base_backoff_s)


# ── Producer ─────────────────────────────────────────────────────────────────


async def enqueue(
    task_type: str,
    payload: dict[str, Any],
    max_retries: Optional[int] = None,
) -> Optional[str]:
    """
    Enqueue a task onto the Redis Stream for durable processing.

    Returns the stream message ID on success, None if Redis is unavailable
    (caller should fall back to asyncio.create_task).
    """
    r = await get_redis()
    if r is None:
        logger.warning(
            '{"event":"task_enqueue_failed","reason":"redis_unavailable","task_type":"%s"}',
            task_type,
        )
        return None

    retries = max_retries if max_retries is not None else TASK_CONFIGS.get(
        task_type, DEFAULT_TASK_CONFIG
    )[0]

    message = {
        "task_type": task_type,
        "payload": json.dumps(payload, default=str),
        "attempt": "0",
        "max_retries": str(retries),
        "created_at": str(time.time()),
    }

    try:
        msg_id = await r.xadd(STREAM_EVENTS, message, maxlen=100_000)
        return msg_id
    except Exception as e:
        logger.error(
            '{"event":"task_enqueue_error","task_type":"%s","error":"%s"}',
            task_type, str(e)[:200],
        )
        return None


# ── Consumer ─────────────────────────────────────────────────────────────────

# Registry of task handlers — populated at worker startup
_handlers: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}


def register_handler(task_type: str):
    """Decorator: register a function as a handler for a task type."""

    def decorator(func: Callable[..., Coroutine[Any, Any, None]]):
        _handlers[task_type] = func
        return func

    return decorator


async def _process_message(
    msg_id: str,
    data: dict[str, str],
) -> bool:
    """
    Process a single message. Returns True on success, False on failure.
    On failure, the message is re-enqueued with incremented attempt count
    or moved to the dead-letter stream.
    """
    task_type = data.get("task_type", "unknown")
    payload_str = data.get("payload", "{}")
    attempt = int(data.get("attempt", "0"))
    max_retries = int(data.get("max_retries", "3"))

    handler = _handlers.get(task_type)
    if handler is None:
        logger.warning(
            '{"event":"task_no_handler","task_type":"%s","msg_id":"%s"}',
            task_type, msg_id,
        )
        return True  # Ack — no handler, nothing to retry

    try:
        payload = json.loads(payload_str)
        await handler(**payload)
        logger.debug(
            '{"event":"task_completed","task_type":"%s","msg_id":"%s","attempt":%d}',
            task_type, msg_id, attempt,
        )
        return True
    except Exception as e:
        logger.warning(
            '{"event":"task_failed","task_type":"%s","msg_id":"%s","attempt":%d,"error":"%s"}',
            task_type, msg_id, attempt, str(e)[:200],
        )

        if attempt < max_retries:
            # Re-enqueue with incremented attempt and backoff
            backoff = TASK_CONFIGS.get(task_type, DEFAULT_TASK_CONFIG)[1] * (2 ** attempt)
            await asyncio.sleep(backoff)

            r = await get_redis()
            if r:
                await r.xadd(
                    STREAM_EVENTS,
                    {
                        "task_type": task_type,
                        "payload": payload_str,
                        "attempt": str(attempt + 1),
                        "max_retries": str(max_retries),
                        "created_at": data.get("created_at", str(time.time())),
                        "last_error": str(e)[:500],
                    },
                    maxlen=100_000,
                )
            return True  # Ack original — re-enqueued copy will be retried
        else:
            # Move to dead-letter
            r = await get_redis()
            if r:
                await r.xadd(
                    STREAM_DEAD_LETTER,
                    {
                        **data,
                        "final_error": str(e)[:500],
                        "died_at": str(time.time()),
                    },
                    maxlen=10_000,
                )
            logger.error(
                '{"event":"task_dead_letter","task_type":"%s","msg_id":"%s","error":"%s"}',
                task_type, msg_id, str(e)[:200],
            )
            return True  # Ack — moved to dead letter


async def start_workers(
    num_workers: int = 4,
    batch_size: int = 5,
    block_ms: int = 5000,
) -> None:
    """
    Start consumer workers that process tasks from the Redis Stream.

    Creates the consumer group if it doesn't exist, then enters a
    read-process-ack loop. Runs until cancelled (SIGTERM/SIGINT).

    Args:
        num_workers: Number of concurrent worker coroutines.
        batch_size: Max messages to claim per worker per iteration.
        block_ms: How long XREADGROUP blocks waiting for new messages.
    """
    r = await get_redis()
    if r is None:
        logger.critical("Cannot start workers — Redis unavailable")
        return

    # Create consumer group (idempotent — MKSTREAM creates the stream too)
    try:
        await r.xgroup_create(
            STREAM_EVENTS, GROUP_NAME, id="0", mkstream=True
        )
        logger.info('{"event":"consumer_group_created","group":"%s"}', GROUP_NAME)
    except Exception:
        # Group already exists — expected on subsequent starts
        pass

    logger.info(
        '{"event":"workers_starting","num_workers":%d,"consumer":"%s"}',
        num_workers, CONSUMER_NAME,
    )

    async def worker(worker_id: int):
        """Single worker loop — reads, processes, acks."""
        consumer = f"{CONSUMER_NAME}-{worker_id}"
        while True:
            try:
                # Read pending messages (crashed worker recovery) first
                pending = await r.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=consumer,
                    streams={STREAM_EVENTS: "0"},  # "0" = all pending
                    count=batch_size,
                    block=100,  # Short block — we prioritize pending
                )
                if pending:
                    for _stream, messages in pending:
                        for msg_id, data in messages:
                            await _process_message(msg_id, data)
                            await r.xack(STREAM_EVENTS, GROUP_NAME, msg_id)

                # Read new messages
                streams = await r.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=consumer,
                    streams={STREAM_EVENTS: ">"},  # ">" = new messages only
                    count=batch_size,
                    block=block_ms,
                )
                if streams is None:
                    continue  # Block timeout — no new messages

                for _stream, messages in streams:
                    for msg_id, data in messages:
                        success = await _process_message(msg_id, data)
                        if success:
                            await r.xack(STREAM_EVENTS, GROUP_NAME, msg_id)

            except asyncio.CancelledError:
                logger.info('{"event":"worker_stopping","worker_id":%d}', worker_id)
                break
            except Exception as e:
                logger.error(
                    '{"event":"worker_error","worker_id":%d,"error":"%s"}',
                    worker_id, str(e)[:200],
                )
                await asyncio.sleep(1)  # Back off before retry

    tasks = [asyncio.create_task(worker(i)) for i in range(num_workers)]
    logger.info('{"event":"workers_started","count":%d}', num_workers)

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info('{"event":"workers_shutdown_complete"}')


# ── Built-in handlers ────────────────────────────────────────────────────────


@register_handler("notification")
async def _handle_notification(user_id: int, type: str, title: str, body: str, data: dict | None = None, **kwargs):
    """Create an in-app notification."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import create_notification

    async with AsyncSessionLocal() as db:
        await create_notification(
            db=db,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            data=data or {},
        )


@register_handler("email")
async def _handle_email(to_email: str, subject: str, body: str, **kwargs):
    """Send an email via SMTP."""
    from app.services.email_service import send_email

    await send_email(to_email=to_email, subject=subject, body=body)


@register_handler("webhook")
async def _handle_webhook(event: str, data: dict, **kwargs):
    """Deliver a webhook event."""
    from app.core.database import AsyncSessionLocal
    from app.services.webhook_service import trigger_webhook

    async with AsyncSessionLocal() as db:
        await trigger_webhook(event=event, data=data, db=db)


@register_handler("analytics")
async def _handle_analytics(event_type: str, user_id: int = 0, data: dict | None = None, **kwargs):
    """Record an analytics event."""
    from app.core.database import AsyncSessionLocal
    from app.services.analytics_service import track_event

    async with AsyncSessionLocal() as db:
        await track_event(db, event_type, user_id, data or {})


@register_handler("lifecycle_notifications")
async def _handle_lifecycle_notifications(task: str = "all", **kwargs):
    """Send lifecycle notifications (profile reminders, subscription expiry, etc.)."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import send_complete_profile_reminders
    from app.services.subscription_service import send_subscription_lifecycle_notifications

    async with AsyncSessionLocal() as db:
        if task in ("all", "profile_reminders"):
            sent = await send_complete_profile_reminders(db)
            logger.info('{"event":"lifecycle_profile_reminders","count":%d}', len(sent))

        if task in ("all", "subscription"):
            sent = await send_subscription_lifecycle_notifications(db)
            logger.info('{"event":"lifecycle_subscription","count":%d}', len(sent))


@register_handler("cleanup")
async def _handle_cleanup(resource_type: str, **kwargs):
    """Run periodic cleanup jobs."""
    logger.info('{"event":"cleanup_task","resource_type":"%s"}', resource_type)
    # Extend with specific cleanup logic as needed
