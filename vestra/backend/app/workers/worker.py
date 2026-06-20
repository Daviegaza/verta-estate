"""
Background worker entry point.

Starts Redis Streams consumers that process durable tasks:
notifications, emails, webhooks, analytics, cleanup.

Run:
    python -m app.workers.worker
    # or with env vars for tuning:
    WORKERS=8 BATCH_SIZE=10 python -m app.workers.worker

Environment variables:
    WORKERS: Number of concurrent worker coroutines (default: 4)
    BATCH_SIZE: Max messages per worker per iteration (default: 5)
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.task_queue import start_workers

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    stream=sys.stdout,
)
logger = logging.getLogger("vestra.worker")


async def main() -> None:
    num_workers = int(os.getenv("WORKERS", "4"))
    batch_size = int(os.getenv("BATCH_SIZE", "5"))

    logger.info(
        '{"event":"worker_bootstrap","num_workers":%d,"batch_size":%d}',
        num_workers, batch_size,
    )

    # Graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_signal(sig):
        logger.info('{"event":"signal_received","signal":"%s"}', sig.name)
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal, sig)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: stop_event.set())

    worker_task = asyncio.create_task(
        start_workers(num_workers=num_workers, batch_size=batch_size)
    )

    await stop_event.wait()
    worker_task.cancel()
    await asyncio.gather(worker_task, return_exceptions=True)
    logger.info('{"event":"worker_shutdown"}')
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
