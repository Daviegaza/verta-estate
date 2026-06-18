"""
Prometheus metrics for Vestra API.
Exposes request counts, latencies, and business metrics on /metrics.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
import time

# ── HTTP Metrics ───────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "vestra_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "vestra_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_IN_FLIGHT = Gauge(
    "vestra_http_requests_in_flight",
    "Currently in-flight HTTP requests",
)

# ── Business Metrics ───────────────────────────────────────────────────────────

PROPERTIES_LISTED = Counter(
    "vestra_properties_listed_total",
    "Total properties listed",
    ["property_type", "listing_type"],
)

VERIFICATIONS_RUN = Counter(
    "vestra_verifications_run_total",
    "Total AI verifications run",
    ["recommendation"],
)

PAYMENTS_RECEIVED = Counter(
    "vestra_payments_received_total",
    "Total payments received",
    ["method", "purpose"],
)

PAYMENTS_AMOUNT = Counter(
    "vestra_payments_amount_kes_total",
    "Total payment amount in KES",
    ["purpose"],
)

USERS_REGISTERED = Counter(
    "vestra_users_registered_total",
    "Total user registrations",
    ["role"],
)

FRAUD_RISK_SCORE = Histogram(
    "vestra_fraud_risk_score",
    "Distribution of fraud risk scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

TRUST_SCORE = Histogram(
    "vestra_trust_score",
    "Distribution of trust scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

# ── Middleware ─────────────────────────────────────────────────────────────────

async def metrics_middleware(request: Request, call_next):
    """Track request metrics for Prometheus."""
    path = request.url.path
    # Group dynamic path segments
    for segment in path.split("/"):
        if segment.isdigit():
            path = path.replace(f"/{segment}/", "/{id}/")
            path = path.replace(f"/{segment}", "/{id}")

    REQUEST_IN_FLIGHT.inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=path,
        ).observe(time.perf_counter() - start)
        return response
    except Exception:
        REQUEST_COUNT.labels(
            method=request.method, endpoint=path, status=500
        ).inc()
        raise
    finally:
        REQUEST_IN_FLIGHT.dec()


async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics (protected by internal auth or IP whitelist in prod)."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
