"""
Stripe payment provider — implements the pluggable PaymentProvider interface.
Handles card payments, webhook verification, and refunds.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

import stripe

from app.core.config import settings
from app.services.payment_providers import (
    PaymentProvider, PaymentRequest, PaymentResult, ProviderType,
    register_provider,
)

logger = logging.getLogger("vestra")


class StripeProvider(PaymentProvider):
    """Stripe provider implementing the PaymentProvider interface."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.stripe

    @property
    def supports_card_payments(self) -> bool:
        return True

    def __init__(self):
        if settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Create a Stripe PaymentIntent."""
        if not settings.STRIPE_SECRET_KEY:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Stripe is not configured",
            )

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(request.amount * 100),  # Convert to cents
                currency=request.currency.lower(),
                description=request.description,
                metadata={
                    "reference": request.reference,
                    **(request.metadata or {}),
                },
            )
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=intent.id,
                status="processing",
                raw_response={"client_secret": intent.client_secret},
            )
        except stripe.StripeError as e:
            logger.error('{"event":"stripe_error","error":"%s"}', str(e))
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Verify Stripe webhook signature."""
        if not settings.STRIPE_WEBHOOK_SECRET:
            logger.warning('{"event":"stripe_webhook","warning":"no_webhook_secret"}')
            return True  # If not configured, skip verification in dev

        try:
            payload = raw_data.get("_raw_body", "")
            sig_header = headers.get("stripe-signature", "")
            stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
            )
            return True
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning('{"event":"stripe_webhook_blocked","reason":"%s"}', str(e))
            return False

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process a Stripe webhook event."""
        event_type = raw_data.get("type", "")
        event_obj = raw_data.get("data", {}).get("object", {})

        if event_type == "payment_intent.succeeded":
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=event_obj.get("id"),
                provider_receipt=event_obj.get("id"),
                status="completed",
                raw_response=event_obj,
            )
        elif event_type == "payment_intent.payment_failed":
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                provider_transaction_id=event_obj.get("id"),
                status="failed",
                error_message=event_obj.get("last_payment_error", {}).get("message", "Payment failed"),
                raw_response=event_obj,
            )
        elif event_type == "charge.refunded":
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=event_obj.get("payment_intent"),
                status="refunded",
                raw_response=event_obj,
            )
        else:
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=event_obj.get("id") if isinstance(event_obj, dict) else None,
                status="processed",
                raw_response=raw_data,
            )

    async def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Refund a Stripe payment."""
        if not settings.STRIPE_SECRET_KEY:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Stripe is not configured",
            )

        try:
            refund_args = {"payment_intent": transaction_id}
            if amount:
                refund_args["amount"] = int(amount * 100)

            refund_obj = stripe.Refund.create(**refund_args)
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=refund_obj.id,
                status="refunded",
                raw_response={"refund_id": refund_obj.id},
            )
        except stripe.StripeError as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Check Stripe payment status."""
        try:
            intent = stripe.PaymentIntent.retrieve(transaction_id)
            status_map = {
                "succeeded": "completed",
                "requires_payment_method": "pending",
                "requires_action": "pending",
                "processing": "processing",
                "canceled": "failed",
            }
            return PaymentResult(
                success=intent.status == "succeeded",
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status=status_map.get(intent.status, intent.status),
                raw_response={"status": intent.status},
            )
        except stripe.StripeError as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )


# ── Register provider ──────────────────────────────────────────────────────────

register_provider(ProviderType.stripe, StripeProvider)
