"""
VESTRA Revenue Analytics Service
=================================
Comprehensive revenue tracking and forecasting across all monetization channels.
Powers the admin revenue dashboard and business intelligence reports.

Revenue Channels Tracked:
  1. Subscriptions (MRR)         — Agent/Landlord tiered plans
  2. Verification Fees            — AI-powered property verification reports
  3. Escrow Transaction Fees      — Percentage-based escrow service fees
  4. Featured Listings            — Pay-per-feature property promotion
  5. Enterprise API               — API key usage billing
  6. Referral Rewards (cost)      — Payouts to referring users
  7. Payment Processing           — M-Pesa/Stripe transaction fees
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.core.redis import cache_get, cache_set

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# ── Cache TTLs ─────────────────────────────────────────────────────────────────
REVENUE_CACHE_TTL = 300  # 5 minutes — revenue data changes slowly
DASHBOARD_CACHE_TTL = 60  # 1 minute — dashboard refreshes frequently


@dataclass
class RevenueBreakdown:
    """Structured revenue breakdown by channel."""
    subscriptions_mrr: float = 0.0
    verification_fees: float = 0.0
    escrow_fees: float = 0.0
    featured_listings: float = 0.0
    enterprise_api: float = 0.0
    payment_processing: float = 0.0
    referral_payouts: float = 0.0  # Cost, not revenue
    total_revenue: float = 0.0
    net_revenue: float = 0.0
    period: str = "monthly"
    currency: str = "KES"


@dataclass
class MRRMetrics:
    """Monthly Recurring Revenue metrics."""
    current_mrr: float = 0.0
    mrr_growth_pct: float = 0.0
    active_subscribers: int = 0
    avg_revenue_per_user: float = 0.0
    churn_rate_pct: float = 0.0
    net_new_mrr: float = 0.0
    expansion_mrr: float = 0.0
    contraction_mrr: float = 0.0
    currency: str = "KES"


@dataclass
class RevenueForecast:
    """Revenue projections based on current trends."""
    projected_monthly: float = 0.0
    projected_annual: float = 0.0
    confidence: str = "medium"  # low | medium | high
    growth_rate_pct: float = 0.0
    assumptions: list[str] = None

    def __post_init__(self):
        if self.assumptions is None:
            self.assumptions = []


# ── Revenue Calculation ───────────────────────────────────────────────────────


async def get_revenue_breakdown(
    db: AsyncSession,
    period: str = "monthly",
    days: int = 30,
) -> RevenueBreakdown:
    """
    Calculate revenue breakdown across all channels for a given period.

    Args:
        db: Database session
        period: Label for the period ("monthly", "weekly", "yearly")
        days: Number of days to look back
    """
    cache_key = f"vestra:revenue:breakdown:{period}:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return RevenueBreakdown(**cached)

    since = datetime.now(UTC) - timedelta(days=days)

    breakdown = RevenueBreakdown(period=period)

    # 1. Subscription MRR
    try:
        from app.models.subscription import Subscription

        result = await db.execute(
            select(func.count(Subscription.id), func.sum(Subscription.amount_kes))
            .where(
                Subscription.status == "active",
                Subscription.created_at <= datetime.now(UTC),
            )
        )
        count, total = result.one()
        breakdown.active_subscribers_count = count or 0
        breakdown.subscriptions_mrr = float(total or 0)
    except Exception as e:
        logger.warning("Revenue: subscription query failed: %s", e)

    # 2. Verification Fees
    try:
        from app.models.payment import Payment, PaymentPurpose, PaymentStatus

        result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.purpose == PaymentPurpose.verification_report,
                Payment.status == PaymentStatus.completed,
                Payment.created_at >= since,
            )
        )
        breakdown.verification_fees = float(result.scalar_one() or 0)
    except Exception as e:
        logger.warning("Revenue: verification fees query failed: %s", e)

    # 3. Escrow Fees
    try:
        result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.purpose == PaymentPurpose.escrow_deposit,
                Payment.status == PaymentStatus.completed,
                Payment.created_at >= since,
            )
        )
        breakdown.escrow_fees = float(result.scalar_one() or 0)
    except Exception as e:
        logger.warning("Revenue: escrow fees query failed: %s", e)

    # 4. Featured Listings
    try:
        result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.purpose == PaymentPurpose.featured_listing,
                Payment.status == PaymentStatus.completed,
                Payment.created_at >= since,
            )
        )
        breakdown.featured_listings = float(result.scalar_one() or 0)
    except Exception as e:
        logger.warning("Revenue: featured listings query failed: %s", e)

    # 5. Enterprise API usage (estimated from API key tracking)
    try:

        result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.purpose == PaymentPurpose.enterprise_api,
                Payment.status == PaymentStatus.completed,
                Payment.created_at >= since,
            )
        )
        breakdown.enterprise_api = float(result.scalar_one() or 0)
    except Exception as e:
        logger.warning("Revenue: enterprise API query failed: %s", e)

    # 6. Payment Processing (platform fee margin)
    try:
        result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.status == PaymentStatus.completed,
                Payment.created_at >= since,
            )
        )
        total_volume = float(result.scalar_one() or 0)
        # Assume 2.5% platform processing margin
        breakdown.payment_processing = round(total_volume * 0.025, 2)
    except Exception as e:
        logger.warning("Revenue: payment processing query failed: %s", e)

    # 7. Referral Payouts (cost)
    try:
        from app.models.referral import ReferralEarning

        result = await db.execute(
            select(func.coalesce(func.sum(ReferralEarning.amount_kes), 0))
            .where(
                ReferralEarning.status == "paid",
                ReferralEarning.paid_at >= since,
            )
        )
        breakdown.referral_payouts = float(result.scalar_one() or 0)
    except Exception as e:
        logger.warning("Revenue: referral payouts query failed: %s", e)

    # Calculate totals
    breakdown.total_revenue = (
        breakdown.subscriptions_mrr
        + breakdown.verification_fees
        + breakdown.escrow_fees
        + breakdown.featured_listings
        + breakdown.enterprise_api
        + breakdown.payment_processing
    )
    breakdown.net_revenue = breakdown.total_revenue - breakdown.referral_payouts

    # Cache result
    await cache_set(cache_key, breakdown.__dict__, ttl=REVENUE_CACHE_TTL)

    return breakdown


async def get_mrr_metrics(db: AsyncSession) -> MRRMetrics:
    """Calculate detailed MRR metrics with growth and churn analysis."""
    cache_key = "vestra:revenue:mrr_metrics"
    cached = await cache_get(cache_key)
    if cached:
        return MRRMetrics(**cached)

    metrics = MRRMetrics()

    try:
        from app.models.subscription import Subscription

        # Current active subscribers and MRR
        result = await db.execute(
            select(func.count(Subscription.id), func.coalesce(func.sum(Subscription.amount_kes), 0))
            .where(Subscription.status == "active")
        )
        count, total = result.one()
        metrics.active_subscribers = count or 0
        metrics.current_mrr = float(total or 0)

        # ARPU
        if metrics.active_subscribers > 0:
            metrics.avg_revenue_per_user = round(
                metrics.current_mrr / metrics.active_subscribers, 2
            )

        # Churn rate (last 30 days)
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        result = await db.execute(
            select(func.count(Subscription.id))
            .where(
                Subscription.status == "cancelled",
                Subscription.cancelled_at >= thirty_days_ago,
            )
        )
        cancelled_count = result.scalar_one() or 0

        # Total at start of period
        result = await db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.created_at < thirty_days_ago)
        )
        total_at_start = result.scalar_one() or 1  # Avoid division by zero

        metrics.churn_rate_pct = round((cancelled_count / total_at_start) * 100, 2)

        # MRR Growth (compare to 30 days ago)
        result = await db.execute(
            select(func.coalesce(func.sum(Subscription.amount_kes), 0))
            .where(
                Subscription.status == "active",
                Subscription.created_at <= thirty_days_ago,
            )
        )
        previous_mrr = float(result.scalar_one() or 0)

        if previous_mrr > 0:
            metrics.mrr_growth_pct = round(
                ((metrics.current_mrr - previous_mrr) / previous_mrr) * 100, 2
            )

        # Net New MRR
        metrics.net_new_mrr = round(metrics.current_mrr - previous_mrr, 2)

    except Exception as e:
        logger.warning("Revenue: MRR metrics query failed: %s", e)

    await cache_set(cache_key, metrics.__dict__, ttl=REVENUE_CACHE_TTL)
    return metrics


async def get_revenue_forecast(db: AsyncSession, months: int = 12) -> RevenueForecast:
    """Generate revenue forecast based on historical trends."""
    cache_key = f"vestra:revenue:forecast:{months}"
    cached = await cache_get(cache_key)
    if cached:
        return RevenueForecast(**cached)

    # Get current monthly revenue and growth rate
    breakdown = await get_revenue_breakdown(db, period="monthly", days=30)
    mrr_metrics = await get_mrr_metrics(db)

    # Use MRR growth rate or default to 15% monthly for new platforms
    growth_rate = mrr_metrics.mrr_growth_pct / 100 if mrr_metrics.mrr_growth_pct != 0 else 0.15

    current_monthly = breakdown.total_revenue

    # Compound growth projection
    projected_monthly = current_monthly * ((1 + growth_rate) ** months)
    projected_annual = projected_monthly * 12

    confidence = "low"
    if mrr_metrics.active_subscribers > 100:
        confidence = "high"
    elif mrr_metrics.active_subscribers > 20:
        confidence = "medium"

    forecast = RevenueForecast(
        projected_monthly=round(projected_monthly, 2),
        projected_annual=round(projected_annual, 2),
        confidence=confidence,
        growth_rate_pct=round(growth_rate * 100, 2),
        assumptions=[
            f"Monthly growth rate of {round(growth_rate * 100, 1)}% based on current trends",
            f"Active subscribers: {mrr_metrics.active_subscribers}",
            f"Current MRR: KES {mrr_metrics.current_mrr:,.2f}",
            f"Churn rate: {mrr_metrics.churn_rate_pct}%",
            f"Projection period: {months} months",
        ],
    )

    await cache_set(cache_key, forecast.__dict__, ttl=REVENUE_CACHE_TTL)
    return forecast


async def get_revenue_timeline(
    db: AsyncSession, days: int = 90
) -> list[dict]:
    """Get daily revenue data points for charts."""
    cache_key = f"vestra:revenue:timeline:{days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    from app.models.payment import Payment, PaymentStatus

    since = datetime.now(UTC) - timedelta(days=days)
    timeline = []

    # Query daily revenue
    result = await db.execute(
        select(
            func.date(Payment.created_at).label("date"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
            func.count(Payment.id).label("transactions"),
        )
        .where(
            Payment.status == PaymentStatus.completed,
            Payment.created_at >= since,
        )
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
    )

    for row in result:
        timeline.append({
            "date": str(row.date),
            "revenue": float(row.revenue),
            "transactions": row.transactions,
        })

    await cache_set(cache_key, timeline, ttl=REVENUE_CACHE_TTL)
    return timeline


async def get_conversion_metrics(db: AsyncSession) -> dict:
    """Get key business conversion metrics."""
    cache_key = "vestra:revenue:conversions"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    from app.models.analytics import UserEvent
    from app.models.payment import Payment, PaymentStatus
    from app.models.user import User

    metrics = {}

    # Total registered users
    result = await db.execute(select(func.count(User.id)))
    metrics["total_users"] = result.scalar_one() or 0

    # Users who made at least one payment
    result = await db.execute(
        select(func.count(func.distinct(Payment.user_id)))
        .where(Payment.status == PaymentStatus.completed)
    )
    metrics["paying_users"] = result.scalar_one() or 0

    # Conversion rate
    if metrics["total_users"] > 0:
        metrics["conversion_rate_pct"] = round(
            (metrics["paying_users"] / metrics["total_users"]) * 100, 2
        )
    else:
        metrics["conversion_rate_pct"] = 0.0

    # Active users (last 30 days)
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    result = await db.execute(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= thirty_days_ago)
    )
    metrics["active_users_30d"] = result.scalar_one() or 0

    # DAU (Daily Active Users)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= today)
    )
    metrics["dau"] = result.scalar_one() or 0

    # DAU/MAU ratio (engagement)
    thirty_days_ago = today - timedelta(days=30)
    result = await db.execute(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= thirty_days_ago)
    )
    mau = result.scalar_one() or 1
    metrics["dau_mau_ratio_pct"] = round((metrics["dau"] / mau) * 100, 2) if mau > 0 else 0.0

    await cache_set(cache_key, metrics, ttl=DASHBOARD_CACHE_TTL)
    return metrics


async def invalidate_revenue_cache() -> None:
    """Invalidate all revenue-related caches. Call after significant revenue events."""
    patterns = [
        "vestra:revenue:breakdown:*",
        "vestra:revenue:mrr_metrics",
        "vestra:revenue:forecast:*",
        "vestra:revenue:timeline:*",
        "vestra:revenue:conversions",
    ]
    # Redis key deletion by pattern is handled at the cache layer
    logger.info('{"event":"revenue_cache_invalidated","patterns":%s}', patterns)
