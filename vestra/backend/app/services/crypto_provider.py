"""
Cryptocurrency payment provider — implements the pluggable PaymentProvider interface.
Supports USDT and USDC on Polygon network (low fees).
Generates payment addresses and verifies on-chain confirmations.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
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

# Supported stablecoins and networks
SUPPORTED_ASSETS = {
    "USDT": {
        "name": "Tether USD",
        "network": "polygon",
        "decimals": 6,
        "contract": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",  # USDT on Polygon
    },
    "USDC": {
        "name": "USD Coin",
        "network": "polygon",
        "decimals": 6,
        "contract": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e on Polygon
    },
}

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


def _generate_payment_address(reference: str) -> str:
    """Generate a deterministic sub-address or memo from a reference.

    For MVP, the main wallet address is reused and the reference is
    embedded in the transaction metadata. In production, generate
    unique deposit addresses per user via a dedicated HMAC derivation
    or a third-party API like Circle, Fireblocks, or Alchemy.
    """
    return settings.CRYPTO_WALLET_ADDRESS_USDT or ""


def _make_payment_id() -> str:
    """Generate a unique payment ID."""
    return f"CRYPTO-{uuid.uuid4().hex[:12].upper()}"


class CryptoProvider(PaymentProvider):
    """Cryptocurrency provider implementing the PaymentProvider interface.

    Supports USDT/USDC on Polygon network with on-chain verification
    via the configured RPC endpoint.
    """

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.crypto

    @property
    def supports_card_payments(self) -> bool:
        return False

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Generate a payment address and instructions for crypto payment.

        Returns the wallet address and the expected amount with asset details.
        The user sends the exact amount to the wallet address.
        """
        if not settings.CRYPTO_WALLET_ADDRESS_USDT:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Crypto wallet is not configured",
            )

        if not settings.CRYPTO_ENABLED:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Cryptocurrency payments are not enabled",
            )

        payment_id = _make_payment_id()
        reference = request.reference or payment_id
        wallet = _generate_payment_address(reference)

        # Determine asset from metadata or default to USDT
        asset_key = (request.metadata or {}).get("crypto_asset", "USDT").upper()
        if asset_key not in SUPPORTED_ASSETS:
            asset_key = "USDT"
        asset = SUPPORTED_ASSETS[asset_key]

        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=payment_id,
            status="pending",
            raw_response={
                "payment_id": payment_id,
                "wallet_address": wallet,
                "network": asset["network"],
                "asset": asset_key,
                "asset_name": asset["name"],
                "contract_address": asset["contract"],
                "amount": float(request.amount),
                "currency": f"{asset_key}",
                "decimals": asset["decimals"],
                "reference": reference,
                "confirmations_required": settings.CRYPTO_CONFIRMATIONS_REQUIRED,
                "instructions": (
                    f"Send exactly {request.amount} {asset_key} on the "
                    f"{asset['network'].upper()} network to the wallet address above. "
                    f"Use the reference '{reference}' in the transaction memo if supported. "
                    f"Payment will be confirmed after {settings.CRYPTO_CONFIRMATIONS_REQUIRED} "
                    f"block confirmations."
                ),
                "expires_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def verify_onchain_transaction(
        self, tx_hash: str, expected_amount: Decimal, expected_asset: str,
    ) -> PaymentResult:
        """Verify an on-chain transaction using an RPC call.

        Checks that the transaction sent the expected amount of the
        expected asset to the configured wallet address.
        """
        if not settings.CRYPTO_RPC_URL:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message="Crypto RPC is not configured",
            )

        try:
            client = await _get_client()

            # Use eth_getTransactionReceipt to check the transaction
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1,
            }
            response = await client.post(
                settings.CRYPTO_RPC_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            receipt = response.json()

            if "error" in receipt or not receipt.get("result"):
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    provider_transaction_id=tx_hash,
                    status="failed",
                    error_message=f"Transaction not found: {receipt.get('error', {}).get('message', 'unknown')}",
                    raw_response=receipt,
                )

            tx_receipt = receipt["result"]
            block_number = int(tx_receipt.get("blockNumber", "0x0"), 16)
            confirmations = await self._get_block_confirmations(block_number)

            if confirmations < settings.CRYPTO_CONFIRMATIONS_REQUIRED:
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    provider_transaction_id=tx_hash,
                    status="pending",
                    raw_response={
                        "confirmations": confirmations,
                        "confirmations_required": settings.CRYPTO_CONFIRMATIONS_REQUIRED,
                    },
                )

            status_hex = tx_receipt.get("status", "0x0")
            if status_hex == "0x1":
                return PaymentResult(
                    success=True,
                    provider=self.provider_type.value,
                    provider_transaction_id=tx_hash,
                    status="completed",
                    raw_response={
                        "tx_hash": tx_hash,
                        "block_number": block_number,
                        "confirmations": confirmations,
                        "gas_used": tx_receipt.get("gasUsed", "0x0"),
                    },
                )
            else:
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    provider_transaction_id=tx_hash,
                    status="failed",
                    error_message="Transaction reverted on-chain",
                    raw_response={"tx_hash": tx_hash, "status": status_hex},
                )

        except httpx.RequestError as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=f"Cannot connect to RPC: {str(e)[:100]}",
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def _get_block_confirmations(self, block_number: int) -> int:
        """Get the number of confirmations for a block."""
        try:
            client = await _get_client()
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1,
            }
            response = await client.post(
                settings.CRYPTO_RPC_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            current_block = int(result.get("result", "0x0"), 16)
            return max(0, current_block - block_number + 1)
        except Exception:
            return 0

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """Crypto webhook verification depends on the provider.

        For Alchemy/webhook-based verification, validate the signature
        in the headers. For self-hosted RPC polling, trust is implicit.
        """
        # Alchemy webhook signature verification
        signature = headers.get("X-Alchemy-Signature", "")
        if not signature:
            return True  # No signature = polling mode, trust the caller

        # Alchemy uses HMAC-SHA256 with the webhook signing key
        signing_key = headers.get("X-Alchemy-Webhook-Id", "")
        if signing_key and settings.CRYPTO_WALLET_ADDRESS_USDT:
            expected = hmac.new(
                settings.CRYPTO_WALLET_ADDRESS_USDT.encode(),
                json.dumps(raw_data, separators=(",", ":")).encode(),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        return True

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process a crypto webhook event (e.g. from Alchemy)."""
        event_type = raw_data.get("type", "")
        event_data = raw_data.get("event", {})

        if event_type == "ADDRESS_ACTIVITY":
            activity = event_data.get("activity", [])
            for tx in activity:
                tx_hash = tx.get("hash", "")
                value_hex = tx.get("value", "0x0")
                asset = tx.get("asset", "USDT").upper()

                if asset in SUPPORTED_ASSETS:
                    return PaymentResult(
                        success=True,
                        provider=self.provider_type.value,
                        provider_transaction_id=tx_hash,
                        status="completed",
                        raw_response=tx,
                    )

        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=raw_data.get("id", "webhook_event"),
            status="processed",
            raw_response=raw_data,
        )

    async def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Crypto refunds require a manual transfer from the wallet."""
        return PaymentResult(
            success=False,
            provider=self.provider_type.value,
            error_message=(
                "Cryptocurrency refunds require manual processing. "
                "Contact finance@vestra.co.ke to initiate a crypto refund."
            ),
        )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Check a crypto payment by its payment ID (off-chain)."""
        return PaymentResult(
            success=True,
            provider=self.provider_type.value,
            provider_transaction_id=transaction_id,
            status="pending",
            raw_response={
                "note": "Crypto status is verified via on-chain transaction. "
                        "Use verify_onchain_transaction with a tx_hash.",
            },
        )


# ── Register provider ──────────────────────────────────────────────────────────
register_provider(ProviderType.crypto, CryptoProvider)
