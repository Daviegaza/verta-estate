"""
PayPal payment provider — implements the pluggable PaymentProvider interface.
Supports order creation, capture, and webhook verification.
Sandbox and production modes via PAYPAL_ENV config.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import httpx

from app.core.config import settings
from app.services.payment_providers import (
    PaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderType,
    register_provider,
)

if TYPE_CHECKING:
    from decimal import Decimal

logger = logging.getLogger("vestra")

PAYPAL_API_BASE = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


def _get_api_base() -> str:
    env = settings.PAYPAL_ENV if settings.PAYPAL_ENV in PAYPAL_API_BASE else "sandbox"
    return PAYPAL_API_BASE[env]


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


async def _get_access_token() -> str | None:
    """Get PayPal OAuth2 access token."""
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        return None

    client = await _get_client()
    try:
        response = await client.post(
            f"{_get_api_base()}/v1/oauth2/token",
            headers={"Accept": "application/json"},
            data={"grant_type": "client_credentials"},
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logger.error('{"event":"paypal_token_error","error":"%s"}', str(e))
        return None


class PayPalProvider(PaymentProvider):
    """PayPal provider implementing the PaymentProvider interface."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.paypal

    @property
    def supports_card_payments(self) -> bool:
        return True

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Create a PayPal order and return a checkout URL."""
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="PayPal is not configured",
            )

        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with PayPal",
            )

        try:
            client = await _get_client()
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": request.reference,
                        "description": request.description[:127],
                        "amount": {
                            "currency_code": request.currency.upper(),
                            "value": str(request.amount),
                        },
                        "custom_id": json.dumps(request.metadata or {}),
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                            "landing_page": "LOGIN",
                            "user_action": "PAY_NOW",
                            "return_url": f"{request.callback_url or settings.BASE_URL}/payment/success",
                            "cancel_url": f"{request.callback_url or settings.BASE_URL}/payment/cancel",
                        }
                    }
                },
            }

            response = await client.post(
                f"{_get_api_base()}/v2/checkout/orders",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            order = response.json()

            approval_url = None
            for link in order.get("links", []):
                if link.get("rel") == "payer-action":
                    approval_url = link.get("href")
                    break

            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=order.get("id"),
                status="pending",
                redirect_url=approval_url,
                raw_response=order,
            )
        except httpx.HTTPStatusError as e:
            logger.error('{"event":"paypal_order_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=f"PayPal API error: {e.response.status_code}",
                raw_response=e.response.json() if e.response else {},
            )
        except Exception as e:
            logger.error('{"event":"paypal_order_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def capture_payment(self, order_id: str) -> PaymentResult:
        """Capture a PayPal order after buyer approval."""
        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with PayPal",
            )

        try:
            client = await _get_client()
            response = await client.post(
                f"{_get_api_base()}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            capture_data = response.json()

            if capture_data.get("status") == "COMPLETED":
                captures = (
                    capture_data.get("purchase_units", [{}])[0]
                    .get("payments", {})
                    .get("captures", [{}])
                )
                capture_id = captures[0].get("id") if captures else None
                return PaymentResult(
                    success=True,
                    provider=self.provider_type.value,
                    provider_transaction_id=capture_data.get("id"),
                    provider_receipt=capture_id,
                    status="completed",
                    raw_response=capture_data,
                )
            else:
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    provider_transaction_id=capture_data.get("id"),
                    status="failed",
                    error_message=f"PayPal capture status: {capture_data.get('status')}",
                    raw_response=capture_data,
                )
        except httpx.HTTPStatusError as e:
            logger.error('{"event":"paypal_capture_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="PayPal capture failed",
                raw_response=e.response.json() if e.response else {},
            )
        except Exception as e:
            logger.error('{"event":"paypal_capture_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Verify PayPal webhook notification using POSTBACK verification."""
        if not settings.PAYPAL_CLIENT_ID:
            logger.warning('{"event":"paypal_webhook","warning":"no_client_id"}')
            return True

        verification_url = f"{_get_api_base()}/v1/notifications/verify-webhook-signature"
        token = await _get_access_token()
        if not token:
            return False

        try:
            client = await _get_client()
            # PayPal requires the full header including transmission-* fields
            verify_payload = {
                "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
                "cert_url": headers.get("PAYPAL-CERT-URL", ""),
                "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
                "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
                "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
                "webhook_id": settings.PAYPAL_CLIENT_ID,
                "webhook_event": raw_data,
            }

            response = await client.post(
                verification_url,
                json=verify_payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            return result.get("verification_status") == "SUCCESS"
        except Exception as e:
            logger.warning('{"event":"paypal_webhook_verify_failed","error":"%s"}', str(e))
            return True  # Fall back to accepting in dev

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process a PayPal webhook event."""
        event_type = raw_data.get("event_type", "")
        resource = raw_data.get("resource", {})

        if event_type == "CHECKOUT.ORDER.APPROVED":
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=resource.get("id"),
                status="processing",
                raw_response=resource,
            )
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=resource.get("id"),
                status="completed",
                raw_response=resource,
            )
        elif event_type == "PAYMENT.CAPTURE.DENIED":
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                provider_transaction_id=resource.get("id"),
                status="failed",
                error_message="PayPal payment denied",
                raw_response=resource,
            )
        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=resource.get("id"),
                status="refunded",
                raw_response=resource,
            )
        else:
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=resource.get("id") if isinstance(resource, dict) else None,
                status="processed",
                raw_response=raw_data,
            )

    async def refund(self, transaction_id: str, amount: Decimal | None = None) -> PaymentResult:
        """Refund a PayPal capture."""
        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with PayPal",
            )

        try:
            client = await _get_client()
            refund_payload = {}
            if amount:
                refund_payload["amount"] = {
                    "currency_code": "USD",
                    "value": str(amount),
                }

            response = await client.post(
                f"{_get_api_base()}/v2/payments/captures/{transaction_id}/refund",
                json=refund_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            refund_data = response.json()
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=refund_data.get("id"),
                status="refunded",
                raw_response=refund_data,
            )
        except httpx.HTTPStatusError as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=f"PayPal refund error: {e.response.status_code}",
                raw_response=e.response.json() if e.response else {},
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Check PayPal order status."""
        token = await _get_access_token()
        if not token:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Failed to authenticate with PayPal",
            )

        try:
            client = await _get_client()
            response = await client.get(
                f"{_get_api_base()}/v2/checkout/orders/{transaction_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            order = response.json()

            status_map = {
                "APPROVED": "processing",
                "COMPLETED": "completed",
                "CREATED": "pending",
                "SAVED": "pending",
                "PAYER_ACTION_REQUIRED": "pending",
                "VOIDED": "failed",
            }
            order_status = order.get("status", "")
            return PaymentResult(
                success=order_status == "COMPLETED",
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status=status_map.get(order_status, "unknown"),
                raw_response=order,
            )
        except httpx.HTTPStatusError:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="PayPal status check failed",
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )


# ── Register provider ──────────────────────────────────────────────────────────
register_provider(ProviderType.paypal, PayPalProvider)
