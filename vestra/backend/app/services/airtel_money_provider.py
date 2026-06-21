"""
Airtel Money payment provider — implements the pluggable PaymentProvider interface.
STK-like push notification for Airtel Money Kenya, similar to M-Pesa.
Sandbox and production modes via AIRTEL_ENV config.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.services.payment_providers import (
    PaymentProvider, PaymentRequest, PaymentResult, ProviderType,
    register_provider,
)

logger = logging.getLogger("vestra")

AIRTEL_API_BASE = {
    "sandbox": "https://openapiuat.airtel.africa",
    "production": "https://openapi.airtel.africa",
}


def _get_api_base() -> str:
    env = settings.AIRTEL_ENV if settings.AIRTEL_ENV in AIRTEL_API_BASE else "sandbox"
    return AIRTEL_API_BASE[env]


# ── Shared HTTPX Client ──────────────────────────────────────────────────────
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
                )
    return _client


async def close_airtel_client():
    """Close the shared Airtel Money HTTP client."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def _get_access_token() -> Optional[str]:
    """Get OAuth2 access token from Airtel Money API with caching."""
    if not settings.AIRTEL_CLIENT_ID or not settings.AIRTEL_CLIENT_SECRET:
        return None

    client = await _get_client()
    try:
        credentials = f"{settings.AIRTEL_CLIENT_ID}:{settings.AIRTEL_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()

        response = await client.post(
            f"{_get_api_base()}/auth/oauth2/token",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json",
            },
            json={
                "client_id": settings.AIRTEL_CLIENT_ID,
                "client_secret": settings.AIRTEL_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        logger.error('{"event":"airtel_token_error","error":"%s"}', str(e))
        return None


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to 254XXXXXXXX format (without +)."""
    p = phone.replace("+", "").replace(" ", "").replace("-", "")
    if p.startswith("0"):
        p = "254" + p[1:]
    if not p.startswith("254"):
        p = "254" + p
    return p


class AirtelMoneyProvider(PaymentProvider):
    """Airtel Money Kenya provider implementing the PaymentProvider interface.

    Similar to M-Pesa STK Push: sends a push notification to the user's
    phone asking them to confirm the payment.
    """

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.airtel_money

    @property
    def supports_mobile_money(self) -> bool:
        return True

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Initiate Airtel Money push payment (similar to M-Pesa STK Push).

        Sends a payment request to the user's Airtel Money account.
        The user confirms on their phone.
        """
        if not settings.AIRTEL_CLIENT_ID or not settings.AIRTEL_CLIENT_SECRET:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Airtel Money is not configured",
            )

        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with Airtel Money",
            )

        try:
            reference = request.reference or f"AIRTEL-{uuid.uuid4().hex[:10].upper()}"
            phone = _normalize_phone(request.phone_number or "")
            airtel_request_id = str(uuid.uuid4())
            transaction_id = f"TXN{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"

            payload = {
                "reference": reference,
                "subscriber": {
                    "country": "KEN",
                    "currency": request.currency or "KES",
                    "msisdn": phone,
                },
                "transaction": {
                    "amount": float(request.amount),
                    "country": "KEN",
                    "currency": request.currency or "KES",
                    "id": transaction_id,
                    "type": "MERCHANT PAYMENT",
                },
                "description": request.description[:50] or "Vestra Payment",
                "callback_url": request.callback_url or settings.AIRTEL_CALLBACK_URL,
                "airtel_money_request_id": airtel_request_id,
            }

            client = await _get_client()
            response = await client.post(
                f"{_get_api_base()}/merchant/v1/payments/",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Country": "KEN",
                    "X-Currency": request.currency or "KES",
                },
            )
            response.raise_for_status()
            result = response.json()

            status = result.get("status", {}).get("code", "")
            if status in ("200", "201", "TS", "PENDING"):
                airtel_transaction_id = result.get("transaction", {}).get("id", transaction_id)
                return PaymentResult(
                    success=True,
                    provider=self.provider_type.value,
                    provider_transaction_id=airtel_transaction_id,
                    status="processing",
                    raw_response=result,
                )
            else:
                error_msg = result.get("status", {}).get("message", "Push notification failed")
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    error_message=error_msg,
                    raw_response=result,
                )

        except httpx.HTTPStatusError as e:
            logger.error('{"event":"airtel_push_error","status":%d}', e.response.status_code)
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=f"Airtel Money API error: {error_body.get('status', {}).get('message', str(e.response.status_code))}",
                raw_response=error_body,
            )
        except Exception as e:
            logger.error('{"event":"airtel_push_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Verify Airtel Money callback authenticity.

        Airtel can send an HMAC signature in the X-Airtel-Signature header.
        """
        signature = headers.get("X-Airtel-Signature", "")
        if not signature:
            logger.warning('{"event":"airtel_callback","warning":"no_signature"}')
            # In sandbox, trust without signature
            if settings.AIRTEL_ENV == "sandbox":
                return True
            return False

        # HMAC-SHA256 verification with client secret
        if settings.AIRTEL_CLIENT_SECRET:
            import json as _json
            body_str = _json.dumps(raw_data, separators=(",", ":"), sort_keys=True)
            expected = hmac.new(
                settings.AIRTEL_CLIENT_SECRET.encode(),
                body_str.encode(),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        return True

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process an Airtel Money callback."""
        transaction = raw_data.get("transaction", {})
        status_code = raw_data.get("status", {}).get("code", "")
        transaction_id = transaction.get("id", raw_data.get("airtel_money_request_id", ""))

        if status_code in ("200", "TS"):
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status="completed",
                raw_response=raw_data,
            )
        elif status_code in ("404", "500", "FAILED", "TF"):
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status="failed",
                error_message=raw_data.get("status", {}).get("message", "Airtel payment failed"),
                raw_response=raw_data,
            )
        else:
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status="processing",
                raw_response=raw_data,
            )

    async def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Airtel Money refunds require manual processing."""
        return PaymentResult(
            success=False,
            provider=self.provider_type.value,
            error_message=(
                "Airtel Money refunds require manual processing. "
                "Contact finance@vestra.co.ke."
            ),
        )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Check Airtel Money transaction status."""
        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with Airtel Money",
            )

        try:
            client = await _get_client()
            response = await client.get(
                f"{_get_api_base()}/merchant/v1/payments/{transaction_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Country": "KEN",
                    "X-Currency": "KES",
                },
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("status", {}).get("code", "")
            status_map = {
                "200": "completed",
                "TS": "completed",
                "TF": "failed",
                "404": "failed",
                "PENDING": "pending",
                "PROCESSING": "processing",
            }
            resolved_status = status_map.get(code, "pending")
            return PaymentResult(
                success=resolved_status == "completed",
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status=resolved_status,
                raw_response=result,
            )
        except httpx.HTTPStatusError as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=f"Airtel status check failed: {e.response.status_code}",
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )


# ── Register provider ──────────────────────────────────────────────────────────
register_provider(ProviderType.airtel_money, AirtelMoneyProvider)
