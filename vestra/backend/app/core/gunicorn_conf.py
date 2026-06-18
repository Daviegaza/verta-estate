"""
Gunicorn configuration for Vestra production deployment.
Run: gunicorn -c app/core/gunicorn_conf.py app.main:app
"""
import multiprocessing
import os

# ── Server Socket ──────────────────────────────────────────────────────────────

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# ── Worker Processes ───────────────────────────────────────────────────────────

workers = int(os.getenv("GUNICORN_WORKERS", str(multiprocessing.cpu_count() * 2 + 1)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "10000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "1000"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "10"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# ── Logging ────────────────────────────────────────────────────────────────────

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '{"time":"%(t)s","method":"%(m)s","path":"%(U)s","status":"%(s)s",'
    '"duration_ms":"%(L)s","size_bytes":"%(b)s","referer":"%(f)s","agent":"%(a)s"}'
)

# ── Process Naming ─────────────────────────────────────────────────────────────

proc_name = "vestra-api"


def when_ready(server):
    """Log when the server is ready to accept connections."""
    server.log.info('{"event":"gunicorn_ready","workers":%d}', server.cfg.workers)


def worker_exit(server, worker):
    """Log when a worker exits."""
    server.log.info('{"event":"worker_exit","pid":%d}', worker.pid)
