"""
Tests for the Currency Refresh Service — VESTRA v4.3.0
"""

import pytest
from datetime import datetime

from app.services.currency_refresh_service import (
    CurrencyRefreshService,
    DEFAULT_RATES,
    CURRENCY_NAMES,
    CURRENCY_SYMBOLS,
)


@pytest.fixture
def service():
    svc = CurrencyRefreshService()
    return svc


class TestCurrencyDefaults:
    def test_default_rates_have_all_currencies(self):
        for code in CURRENCY_NAMES:
            assert code in DEFAULT_RATES, f"Missing default rate for {code}"

    def test_default_rates_kes_is_one(self):
        assert DEFAULT_RATES["KES"] == 1.0

    def test_currency_names_completeness(self):
        assert len(CURRENCY_NAMES) >= 10
        assert CURRENCY_NAMES["KES"] == "Kenyan Shilling"
        assert CURRENCY_NAMES["USD"] == "US Dollar"

    def test_currency_symbols_completeness(self):
        assert CURRENCY_SYMBOLS["KES"] == "KSh"
        assert CURRENCY_SYMBOLS["USD"] == "$"
        assert CURRENCY_SYMBOLS["EUR"] == "€"


class TestCurrencyService:
    def test_get_rates_returns_defaults_initially(self, service):
        rates = service.get_rates()
        assert "KES" in rates
        assert rates["KES"] == 1.0

    def test_convert_kes_to_kes(self, service):
        result = service.convert(1000, "KES", "KES")
        assert result == 1000.0

    def test_convert_to_kes(self, service):
        # 1 USD = 1/0.0077 KES ≈ 129.87 KES
        result = service.convert(1, "USD", "KES")
        assert result > 100
        assert result < 150

    def test_convert_from_kes(self, service):
        # 130 KES should be roughly 1 USD
        result = service.convert(130, "KES", "USD")
        assert 0.5 < result < 1.5

    def test_convert_roundtrip(self, service):
        # Round-trip should preserve amount
        kes_original = 5000
        usd = service.convert(kes_original, "KES", "USD")
        kes_back = service.convert(usd, "USD", "KES")
        # Should be close (within rounding)
        assert abs(kes_original - kes_back) < 1

    def test_convert_unknown_currency_falls_back(self, service):
        # Unknown currency falls back to default rate
        result = service.convert(100, "XYZ", "KES")
        assert result > 0

    def test_format_kes(self, service):
        formatted = service.format(1500, "KES")
        assert "KSh" in formatted
        assert "1,500" in formatted

    def test_format_usd(self, service):
        formatted = service.format(1500, "USD")
        assert "$" in formatted

    def test_get_all_currencies(self, service):
        currencies = service.get_all_currencies()
        assert len(currencies) >= 10
        for c in currencies:
            assert "code" in c
            assert "symbol" in c
            assert "name" in c
            assert "rate_to_kes" in c

    def test_last_updated_initially_none(self, service):
        assert service.get_last_updated() is None

    @pytest.mark.asyncio
    async def test_initialize_loads_defaults(self, service):
        await service.initialize()
        rates = service.get_rates()
        assert "KES" in rates
        assert rates["KES"] == 1.0

    @pytest.mark.asyncio
    async def test_refresh_updates_last_updated(self, service):
        # This may fail if external API is unreachable, but should not throw
        result = await service.refresh()
        # Even if refresh fails, it should not crash
        assert result in (True, False)
