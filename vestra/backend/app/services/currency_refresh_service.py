"""
Currency Rate Refresh Service — VESTRA v4.3.0

Periodically fetches live exchange rates from open APIs and updates the
in-memory + Redis cache. Falls back to last-known rates if APIs are unavailable.

Supports: KES (base), USD, EUR, GBP, TZS, UGX, RWF, ZAR, AED, CNY
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

import httpx

from app.core.redis import redis_client

logger = logging.getLogger("vestra.currency_refresh")

# ── Default rates (hardcoded as ultimate fallback) ─────────────────────────
# All rates relative to KES (1 KES = X foreign units)
DEFAULT_RATES: dict[str, float] = {
    "KES": 1.0,
    "USD": 0.0077,
    "EUR": 0.0071,
    "GBP": 0.0061,
    "TZS": 19.67,
    "UGX": 29.12,
    "RWF": 10.23,
    "ZAR": 0.14,
    "AED": 0.028,
    "CNY": 0.055,
}

CURRENCY_NAMES: dict[str, str] = {
    "KES": "Kenyan Shilling",
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "TZS": "Tanzanian Shilling",
    "UGX": "Ugandan Shilling",
    "RWF": "Rwandan Franc",
    "ZAR": "South African Rand",
    "AED": "UAE Dirham",
    "CNY": "Chinese Yuan",
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "KES": "KSh",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "TZS": "TSh",
    "UGX": "USh",
    "RWF": "RF",
    "ZAR": "R",
    "AED": "د.إ",
    "CNY": "¥",
}

REDIS_KEY_RATES = "vestra:currency_rates"
REDIS_KEY_LAST_UPDATED = "vestra:currency_rates:updated_at"
CACHE_TTL = 3600 * 6  # 6 hours


class CurrencyRefreshService:
    """Refreshes currency exchange rates from free APIs."""

    def __init__(self) -> None:
        self._current_rates: dict[str, float] = DEFAULT_RATES.copy()
        self._last_updated: datetime | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load cached rates from Redis on startup, fall back to defaults."""
        try:
            cached = await redis_client.get(REDIS_KEY_RATES)
            if cached:
                self._current_rates = json.loads(cached)
                logger.info("Loaded currency rates from Redis cache")

            ts = await redis_client.get(REDIS_KEY_LAST_UPDATED)
            if ts:
                self._last_updated = datetime.fromisoformat(ts)
        except Exception as e:
            logger.warning("Failed to load currency rates from Redis: %s", e)

    async def refresh(self) -> bool:
        """Fetch latest rates from external API. Returns True on success."""
        async with self._lock:
            try:
                rates = await self._fetch_from_api()
                if rates:
                    self._current_rates = rates
                    self._last_updated = datetime.now(UTC)

                    # Persist to Redis
                    await redis_client.set(
                        REDIS_KEY_RATES,
                        json.dumps(rates),
                        ex=CACHE_TTL,
                    )
                    await redis_client.set(
                        REDIS_KEY_LAST_UPDATED,
                        self._last_updated.isoformat(),
                        ex=CACHE_TTL,
                    )

                    logger.info("Currency rates refreshed successfully at %s", self._last_updated)
                    return True
                else:
                    logger.warning("Currency API returned empty rates, using existing")
                    return False
            except Exception as e:
                logger.error("Failed to refresh currency rates: %s", e)
                return False

    async def _fetch_from_api(self) -> dict[str, float] | None:
        """Fetch rates from exchangerate-api (free tier, no key needed)."""
        url = "https://open.er-api.com/v6/latest/KES"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                if data.get("result") != "success":
                    logger.warning("Currency API returned non-success: %s", data)
                    return None

                api_rates = data.get("rates", {})
                # Filter to our supported currencies only
                rates: dict[str, float] = {}
                for code in CURRENCY_NAMES:
                    if code == "KES":
                        rates[code] = 1.0
                    elif code in api_rates:
                        rates[code] = api_rates[code]
                    else:
                        rates[code] = DEFAULT_RATES.get(code, 1.0)

                return rates
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching currency rates: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error fetching currency rates: %s", e)
            return None

    async def _fetch_fallback(self) -> dict[str, float] | None:
        """Fallback: fetch from frankfurter.app (no key needed, EUR base)."""
        url = "https://api.frankfurter.app/latest?from=KES&to=USD,EUR,GBP,TZS,UGX,RWF,ZAR,AED,CNY"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                rates: dict[str, float] = {"KES": 1.0}
                for code in CURRENCY_NAMES:
                    if code in data.get("rates", {}):
                        rates[code] = data["rates"][code]
                    elif code != "KES":
                        rates[code] = DEFAULT_RATES.get(code, 1.0)
                return rates
        except Exception:
            return None

    def get_rates(self) -> dict[str, float]:
        """Get current rates (non-async, from memory)."""
        return self._current_rates.copy()

    def convert(self, amount: float, from_currency: str, to_currency: str = "KES") -> float:
        """Convert an amount between currencies using current rates."""
        rates = self._current_rates
        if from_currency == to_currency:
            return amount

        # Convert to KES first
        if from_currency != "KES":
            from_rate = rates.get(from_currency, DEFAULT_RATES.get(from_currency, 1.0))
            amount_kes = amount / from_rate if from_rate > 0 else amount
        else:
            amount_kes = amount

        # Convert from KES to target
        if to_currency != "KES":
            to_rate = rates.get(to_currency, DEFAULT_RATES.get(to_currency, 1.0))
            return amount_kes * to_rate

        return amount_kes

    def format(self, amount: float, currency: str = "KES") -> str:
        """Format an amount with proper currency symbol."""
        symbol = CURRENCY_SYMBOLS.get(currency, currency)
        return f"{symbol} {amount:,.2f}"

    def get_last_updated(self) -> datetime | None:
        """When rates were last refreshed."""
        return self._last_updated

    def get_all_currencies(self) -> list[dict]:
        """Get all supported currencies with metadata."""
        rates = self._current_rates
        return [
            {
                "code": code,
                "symbol": CURRENCY_SYMBOLS.get(code, code),
                "name": CURRENCY_NAMES.get(code, code),
                "rate_to_kes": rates.get(code, 1.0),
                "updated_at": self._last_updated.isoformat() if self._last_updated else None,
            }
            for code in CURRENCY_NAMES
        ]


# Singleton
currency_service = CurrencyRefreshService()
