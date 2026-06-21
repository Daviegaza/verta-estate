"""
Bank Transfer payment provider — implements the pluggable PaymentProvider interface.
Generates virtual payment references for bank deposits with manual confirmation flow.
Supports Kenyan banks: KCB, Equity, Co-op, NCBA, Absa.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.core.config import settings
from app.services.payment_providers import (
    PaymentProvider, PaymentRequest, PaymentResult, ProviderType,
    register_provider,
)

logger = logging.getLogger("vestra")

# Known Kenyan bank codes for reference
KENYAN_BANKS = {
    "KCB": {"code": "16", "name": "KCB Bank Kenya"},
    "Equity": {"code": "12", "name": "Equity Bank Kenya"},
    "Co-op": {"code": "11", "name": "Co-operative Bank of Kenya"},
    "NCBA": {"code": "07", "name": "NCBA Bank Kenya"},
    "Absa": {"code": "03", "name": "Absa Bank Kenya"},
}


def _get_bank_account_number(bank_code: str) -> str:
    """Get the configured account number for a given bank."""
    mapping = {
        "KCB": settings.BANK_ACCOUNT_NUMBER_KCB,
        "Equity": settings.BANK_ACCOUNT_NUMBER_EQUITY,
        "Co-op": settings.BANK_ACCOUNT_NUMBER_COOP,
        "NCBA": settings.BANK_ACCOUNT_NUMBER_NCBA,
        "Absa": settings.BANK_ACCOUNT_NUMBER_ABSA,
    }
    return mapping.get(bank_code, settings.BANK_ACCOUNT_NUMBER_EQUITY or "")


class BankTransferProvider(PaymentProvider):
    """Bank transfer provider implementing the PaymentProvider interface."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.bank_transfer

    @property
    def supports_bank_transfer(self) -> bool:
        return True

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Generate a virtual payment reference for a bank deposit.

        Creates a unique payment reference that the user must include
        when making a bank transfer. The admin will manually confirm
        the deposit once it reflects in the bank account.
        """
        # Generate a unique virtual payment reference
        reference = request.reference or f"VST-{uuid.uuid4().hex[:10].upper()}"
        virtual_ref = f"VPAY-{hashlib.md5(reference.encode()).hexdigest()[:8].upper()}-{datetime.now(timezone.utc).strftime('%y%m%d')}"

        bank_accounts = []
        for bank_code, info in KENYAN_BANKS.items():
            account_number = _get_bank_account_number(bank_code)
            if account_number:
                bank_accounts.append({
                    "bank": info["name"],
                    "bank_code": bank_code,
                    "account_name": settings.BANK_ACCOUNT_NAME,
                    "account_number": account_number,
                })

        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=virtual_ref,
            status="pending",
            raw_response={
                "virtual_reference": virtual_ref,
                "payment_reference": reference,
                "bank_accounts": bank_accounts,
                "instructions": (
                    f"Make a bank transfer of KES {request.amount} to any of the "
                    f"accounts listed below. Include the reference '{virtual_ref}' "
                    f"in your transaction description. Payment will be confirmed "
                    f"manually within 1-2 business hours during business hours."
                ),
                "amount": float(request.amount),
                "currency": request.currency,
            },
        )

    async def confirm_payment(
        self, virtual_reference: str, transaction_ref: str,
        amount: Decimal, bank_code: str,
    ) -> PaymentResult:
        """Manually confirm a bank transfer deposit (admin action).

        Called by an admin or automated reconciliation script after
        the bank deposit has been verified in the bank statement.
        """
        logger.info(
            '{"event":"bank_transfer_confirmed","ref":"%s","bank":"%s","amount":%f}',
            virtual_reference, bank_code, float(amount),
        )
        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=virtual_reference,
            provider_receipt=transaction_ref,
            status="completed",
            raw_response={
                "virtual_reference": virtual_reference,
                "bank_code": bank_code,
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def reject_payment(self, virtual_reference: str, reason: str) -> PaymentResult:
        """Reject a bank transfer deposit (admin action)."""
        logger.info(
            '{"event":"bank_transfer_rejected","ref":"%s","reason":"%s"}',
            virtual_reference, reason,
        )
        return PaymentResult(
            success=False,
            provider=self.provider_type.value,
            provider_transaction_id=virtual_reference,
            status="failed",
            error_message=reason,
            raw_response={
                "virtual_reference": virtual_reference,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Bank transfers have no automated callback; verification is manual."""
        return True

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Bank transfers have no automated callback; use confirm_payment."""
        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=raw_data.get("virtual_reference", "unknown"),
            status="pending",
            raw_response=raw_data,
        )

    async def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Bank transfer refunds require manual bank transfer."""
        return PaymentResult(
            success=False,
            provider=self.provider_type.value,
            error_message=(
                "Bank transfer refunds require manual processing. "
                "Contact finance@vestra.co.ke to initiate a bank transfer refund."
            ),
        )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Bank transfer status is not auto-pollable; always pending."""
        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=transaction_id,
            status="pending",
            raw_response={
                "note": "Bank transfer status must be confirmed manually by an admin."
            },
        )


# ── Register provider ──────────────────────────────────────────────────────────
register_provider(ProviderType.bank_transfer, BankTransferProvider)
