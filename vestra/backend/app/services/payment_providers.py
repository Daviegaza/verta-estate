"""
Pluggable payment provider architecture.
Add new payment providers without changing core payment logic.
Currently supported: M-Pesa (Kenya + Tanzania), Stripe.
Coming: MTN Mobile Money, Airtel Money, Flutterwave.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from enum import Enum


class ProviderType(str, Enum):
    mpesa_ke = "mpesa_ke"
    mpesa_tz = "mpesa_tz"
    stripe = "stripe"
    flutterwave = "flutterwave"
    mtn_momo = "mtn_momo"
    airtel_money = "airtel_money"
    bank_transfer = "bank_transfer"


@dataclass
class PaymentRequest:
    """Standardised payment request across all providers."""
    amount: Decimal
    currency: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    reference: str = ""
    description: str = ""
    callback_url: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PaymentResult:
    """Standardised payment result across all providers."""
    success: bool
    provider: str
    provider_transaction_id: Optional[str] = None
    provider_receipt: Optional[str] = None
    status: str = "pending"       # pending, processing, completed, failed
    raw_response: dict = None
    error_message: Optional[str] = None
    redirect_url: Optional[str] = None  # For web-based payment flows

    def __post_init__(self):
        if self.raw_response is None:
            self.raw_response = {}


class PaymentProvider(ABC):
    """Base class for all payment providers."""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        ...

    @property
    def supports_mobile_money(self) -> bool:
        return False

    @property
    def supports_card_payments(self) -> bool:
        return False

    @property
    def supports_bank_transfer(self) -> bool:
        return False

    @abstractmethod
    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Start a payment. For mobile money, send push notification.
        For card payments, return a checkout URL."""
        ...

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Verify a callback/webhook is authentic. Override per provider."""
        return True

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process a callback/webhook from the provider."""
        raise NotImplementedError

    async def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Refund a payment. Not all providers support this."""
        return PaymentResult(
            success=False,
            provider=self.provider_type.value,
            error_message=f"Refunds not supported by {self.provider_type.value}",
        )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Poll for payment status."""
        raise NotImplementedError


# ── Provider Registry ──────────────────────────────────────────────────────────

_provider_registry: dict[ProviderType, type[PaymentProvider]] = {}


def register_provider(provider_type: ProviderType, provider_cls: type[PaymentProvider]):
    """Register a payment provider implementation."""
    _provider_registry[provider_type] = provider_cls


def get_provider(provider_type: ProviderType) -> Optional[PaymentProvider]:
    """Instantiate a registered payment provider."""
    cls = _provider_registry.get(provider_type)
    if cls is None:
        return None
    return cls()


def get_provider_for_country(country_code: str, method: str = "mobile_money") -> Optional[PaymentProvider]:
    """Get the default payment provider for a country."""
    country_providers = {
        "KE": ProviderType.mpesa_ke if method == "mobile_money" else ProviderType.stripe,
        "TZ": ProviderType.mpesa_tz if method == "mobile_money" else ProviderType.stripe,
        "UG": ProviderType.mtn_momo if method == "mobile_money" else ProviderType.flutterwave,
        "NG": ProviderType.flutterwave,
        "GH": ProviderType.mtn_momo if method == "mobile_money" else ProviderType.flutterwave,
        "ZA": ProviderType.stripe,
        "RW": ProviderType.mtn_momo if method == "mobile_money" else ProviderType.flutterwave,
    }
    pt = country_providers.get(country_code.upper(), ProviderType.stripe)
    return get_provider(pt)


def list_available_providers() -> list[dict]:
    """List all registered payment providers with capabilities."""
    return [
        {
            "type": pt.value,
            "supports_mobile_money": cls().supports_mobile_money if cls else False,
            "supports_card_payments": cls().supports_card_payments if cls else False,
            "supports_bank_transfer": cls().supports_bank_transfer if cls else False,
        }
        for pt, cls in _provider_registry.items()
    ]


# ── Built-in providers are registered in their respective service files ───────
# See: mpesa_service.py (MpesaKEProvider), stripe_provider.py (StripeProvider)
