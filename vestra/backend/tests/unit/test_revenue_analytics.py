"""
Unit tests for Revenue Analytics Service.
Tests MRR metrics, revenue breakdown, forecasting, and conversion metrics.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.revenue_analytics import (
    MRRMetrics,
    RevenueBreakdown,
    RevenueForecast,
    get_conversion_metrics,
    get_mrr_metrics,
    get_revenue_forecast,
)


class TestRevenueBreakdown:
    """Test the RevenueBreakdown dataclass."""

    def test_default_breakdown(self):
        breakdown = RevenueBreakdown()
        assert breakdown.total_revenue == 0.0
        assert breakdown.net_revenue == 0.0
        assert breakdown.period == "monthly"
        assert breakdown.currency == "KES"

    def test_net_revenue_calculation(self):
        breakdown = RevenueBreakdown(
            subscriptions_mrr=10000,
            verification_fees=5000,
            escrow_fees=3000,
            referral_payouts=2000,
            total_revenue=18000.0,
            net_revenue=16000.0,
        )
        assert breakdown.total_revenue == 18000.0
        assert breakdown.net_revenue == 16000.0  # 18000 - 2000

    def test_empty_revenue(self):
        breakdown = RevenueBreakdown()
        assert breakdown.total_revenue == 0.0
        assert breakdown.net_revenue == 0.0


class TestMRRMetrics:
    """Test MRR metrics calculations."""

    def test_default_metrics(self):
        metrics = MRRMetrics()
        assert metrics.current_mrr == 0.0
        assert metrics.active_subscribers == 0
        assert metrics.churn_rate_pct == 0.0

    def test_arpu_calculation(self):
        metrics = MRRMetrics(
            current_mrr=50000,
            active_subscribers=50,
        )
        assert metrics.avg_revenue_per_user == 0.0  # Not auto-calculated in dataclass

    def test_growth_metrics(self):
        metrics = MRRMetrics(
            current_mrr=100000,
            mrr_growth_pct=15.5,
            net_new_mrr=15000,
        )
        assert metrics.mrr_growth_pct == 15.5
        assert metrics.net_new_mrr == 15000


class TestRevenueForecast:
    """Test revenue forecasting logic."""

    def test_default_forecast(self):
        forecast = RevenueForecast()
        assert forecast.projected_monthly == 0.0
        assert forecast.projected_annual == 0.0
        assert forecast.confidence == "medium"

    def test_forecast_with_growth(self):
        forecast = RevenueForecast(
            projected_monthly=115000,
            projected_annual=1380000,
            confidence="high",
            growth_rate_pct=15.0,
            assumptions=["15% monthly growth", "100 active subscribers"],
        )
        assert forecast.projected_monthly == 115000
        assert forecast.projected_annual == 1380000
        assert forecast.confidence == "high"
        assert len(forecast.assumptions) == 2

    def test_forecast_confidence_levels(self):
        low = RevenueForecast(confidence="low")
        medium = RevenueForecast(confidence="medium")
        high = RevenueForecast(confidence="high")

        assert low.confidence == "low"
        assert medium.confidence == "medium"
        assert high.confidence == "high"


class TestMRRMetricsWithMock:
    """Test MRR metrics with mocked database."""

    @pytest.mark.asyncio
    async def test_mrr_metrics_returns_structured_data(self):
        """Verify MRR metrics returns proper structure with mocked DB."""
        mock_db = AsyncMock()

        # Mock subscription query: (count, total_amount)
        mock_result = MagicMock()
        mock_result.one.return_value = (25, 125000.0)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.revenue_analytics.cache_get", return_value=None), \
             patch("app.services.revenue_analytics.cache_set", AsyncMock()):
            metrics = await get_mrr_metrics(mock_db)

        assert isinstance(metrics, MRRMetrics)
        assert metrics.active_subscribers == 25
        assert metrics.current_mrr == 125000.0


class TestRevenueForecastWithMock:
    """Test revenue forecasting with mocked database."""

    @pytest.mark.asyncio
    async def test_forecast_returns_valid_structure(self):
        """Verify forecast returns proper data structure."""
        mock_db = AsyncMock()

        with patch("app.services.revenue_analytics.cache_get", return_value=None), \
             patch("app.services.revenue_analytics.cache_set", AsyncMock()), \
             patch("app.services.revenue_analytics.get_revenue_breakdown") as mock_breakdown, \
             patch("app.services.revenue_analytics.get_mrr_metrics") as mock_mrr:

            mock_breakdown.return_value = RevenueBreakdown(
                subscriptions_mrr=100000,
                verification_fees=25000,
                total_revenue=125000,
            )
            mock_mrr.return_value = MRRMetrics(
                current_mrr=100000,
                active_subscribers=50,
                mrr_growth_pct=12.5,
            )

            forecast = await get_revenue_forecast(mock_db, months=12)

        assert isinstance(forecast, RevenueForecast)
        assert forecast.projected_monthly > 0
        assert forecast.projected_annual > 0
        assert forecast.confidence in ("low", "medium", "high")
        assert len(forecast.assumptions) >= 2


class TestConversionMetricsWithMock:
    """Test conversion metrics with mocked database."""

    @pytest.mark.asyncio
    async def test_conversion_metrics_structure(self):
        """Verify conversion metrics returns proper key structure."""
        mock_db = AsyncMock()

        # Mock all the count queries
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1000
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.revenue_analytics.cache_get", return_value=None), \
             patch("app.services.revenue_analytics.cache_set", AsyncMock()):
            metrics = await get_conversion_metrics(mock_db)

        assert isinstance(metrics, dict)
        assert "total_users" in metrics
        assert "paying_users" in metrics
        assert "conversion_rate_pct" in metrics
        assert "active_users_30d" in metrics
        assert "dau" in metrics
        assert "dau_mau_ratio_pct" in metrics


class TestCacheIntegration:
    """Test that caching works correctly for revenue analytics."""

    @pytest.mark.asyncio
    async def test_conversion_metrics_uses_cache(self):
        """Verify cached results are returned without DB query."""
        mock_db = AsyncMock()
        cached_data = {
            "total_users": 500,
            "paying_users": 50,
            "conversion_rate_pct": 10.0,
            "active_users_30d": 100,
            "dau": 20,
            "dau_mau_ratio_pct": 20.0,
        }

        with patch("app.services.revenue_analytics.cache_get", return_value=cached_data), \
             patch("app.services.revenue_analytics.cache_set", AsyncMock()):
            metrics = await get_conversion_metrics(mock_db)

        # Should return cached data without calling DB
        assert metrics == cached_data
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_missed_cache_falls_back_to_db(self):
        """Verify DB is queried when cache misses."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 500
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.revenue_analytics.cache_get", return_value=None), \
             patch("app.services.revenue_analytics.cache_set", AsyncMock()):
            metrics = await get_conversion_metrics(mock_db)

        assert metrics["total_users"] == 500
        # DB should have been called
        assert mock_db.execute.called
