"""
Currency Routes — VESTRA v4.3.0

Provides live exchange rates, currency conversion, and supported currency metadata.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.currency_refresh_service import currency_service

router = APIRouter(prefix="/currencies", tags=["currencies"])


@router.get("")
async def list_currencies():
    """List all supported currencies with current rates and metadata."""
    return {
        "success": True,
        "base": "KES",
        "currencies": currency_service.get_all_currencies(),
        "last_updated": (
            currency_service.get_last_updated().isoformat()
            if currency_service.get_last_updated()
            else None
        ),
    }


@router.get("/rates")
async def get_rates():
    """Get raw exchange rates (KES base)."""
    return {
        "success": True,
        "base": "KES",
        "rates": currency_service.get_rates(),
        "last_updated": (
            currency_service.get_last_updated().isoformat()
            if currency_service.get_last_updated()
            else None
        ),
    }


@router.get("/convert")
async def convert_currency(
    amount: float = Query(..., gt=0, description="Amount to convert"),
    from_currency: str = Query("KES", min_length=3, max_length=3, description="Source currency code"),
    to_currency: str = Query("KES", min_length=3, max_length=3, description="Target currency code"),
):
    """Convert an amount between supported currencies."""
    from_currency = from_currency.upper().strip()
    to_currency = to_currency.upper().strip()

    supported = set(currency_service.get_rates().keys())
    if from_currency not in supported:
        raise HTTPException(400, f"Unsupported currency: {from_currency}. Supported: {', '.join(sorted(supported))}")
    if to_currency not in supported:
        raise HTTPException(400, f"Unsupported currency: {to_currency}. Supported: {', '.join(sorted(supported))}")

    result = currency_service.convert(amount, from_currency, to_currency)

    return {
        "success": True,
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "result": round(result, 2),
        "formatted": currency_service.format(result, to_currency),
        "rate": result / amount if amount > 0 else 0,
    }


@router.post("/refresh")
async def refresh_rates():
    """Force-refresh exchange rates from external API."""
    success = await currency_service.refresh()
    if not success:
        raise HTTPException(502, "Failed to refresh currency rates from external API")

    return {
        "success": True,
        "message": "Currency rates refreshed successfully",
        "last_updated": (
            currency_service.get_last_updated().isoformat()
            if currency_service.get_last_updated()
            else None
        ),
    }
