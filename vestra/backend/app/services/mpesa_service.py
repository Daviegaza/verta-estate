import httpx
import base64
import logging
import asyncio
from datetime import datetime, timezone
from app.core.config import settings

logger = logging.getLogger("vestra")

# ── Token Cache ──────────────────────────────────────────────────────────
# Cached access token with expiry. M-Pesa tokens are valid for 1 hour (3599s).
# We refresh 60s early to avoid edge cases.
_token_cache: dict = {"token": None, "expires_at": 0}
_token_lock = asyncio.Lock()

# ── Shared HTTPX Client (connection pooling) ─────────────────────────────
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> httpx.AsyncClient:
    """Get or create a shared httpx.AsyncClient with connection pooling."""
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                )
    return _client


async def close_mpesa_client():
    """Close the shared M-Pesa HTTP client."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _get_mpesa_base_url() -> str:
    if settings.MPESA_ENV == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


async def get_mpesa_access_token() -> str:
    """
    Get OAuth access token from Safaricom with caching.
    Token is valid for 1 hour; we cache for 59 minutes to be safe.
    """
    now = datetime.now(timezone.utc).timestamp()

    # Return cached token if still valid
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    async with _token_lock:
        # Double-check after acquiring lock
        if _token_cache["token"] and now < _token_cache["expires_at"]:
            return _token_cache["token"]

        credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()

        client = await _get_client()
        response = await client.get(
            f"{_get_mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {encoded}"},
        )
        response.raise_for_status()
        token = response.json()["access_token"]

        # Cache with 59-minute TTL (token lives 60 min)
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + 3540  # 59 minutes
        logger.debug('{"event":"mpesa_token_refreshed"}')
        return token


def _generate_password() -> tuple[str, str]:
    """Generate M-Pesa STK Push password and timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


async def initiate_stk_push(
    phone_number: str,
    amount: float,
    account_reference: str,
    transaction_desc: str,
) -> dict:
    """
    Initiate M-Pesa STK Push payment.
    phone_number: format 2547XXXXXXXX (no +)
    amount: KES amount (minimum 1)
    """
    # Normalize phone number
    phone = phone_number.replace("+", "").replace(" ", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not phone.startswith("254"):
        phone = "254" + phone

    access_token = await get_mpesa_access_token()
    password, timestamp = _generate_password()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference[:12],
        "TransactionDesc": transaction_desc[:13],
    }

    client = await _get_client()
    response = await client.post(
        f"{_get_mpesa_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


async def query_stk_status(checkout_request_id: str) -> dict:
    """Query the status of an STK Push transaction."""
    access_token = await get_mpesa_access_token()
    password, timestamp = _generate_password()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    client = await _get_client()
    response = await client.post(
        f"{_get_mpesa_base_url()}/mpesa/stkpushquery/v1/query",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


# ── Pluggable Provider Adapter ──────────────────────────────────────────────

from decimal import Decimal
from app.services.payment_providers import (
    PaymentProvider, PaymentRequest, PaymentResult, ProviderType,
)


class MpesaKEProvider(PaymentProvider):
    """Safaricom M-Pesa Kenya provider implementing the PaymentProvider interface."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.mpesa_ke

    @property
    def supports_mobile_money(self) -> bool:
        return True

    async def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Initiate M-Pesa STK Push for Kenya."""
        try:
            response = await initiate_stk_push(
                phone_number=request.phone_number or "",
                amount=float(request.amount),
                account_reference=request.reference[:12],
                transaction_desc=request.description[:13],
            )
            if response.get("ResponseCode") == "0":
                return PaymentResult(
                    success=True,
                    provider=self.provider_type.value,
                    provider_transaction_id=response.get("CheckoutRequestID"),
                    status="processing",
                    raw_response=response,
                )
            else:
                return PaymentResult(
                    success=False,
                    provider=self.provider_type.value,
                    error_message=response.get("errorMessage", "STK Push failed"),
                    raw_response=response,
                )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )

    async def verify_callback(self, raw_data: dict, headers: dict) -> bool:
        """M-Pesa callback verification is handled at the route level (IP + HMAC)."""
        return True

    async def handle_callback(self, raw_data: dict) -> PaymentResult:
        """Process a callback from M-Pesa."""
        parsed = parse_mpesa_callback(raw_data)
        checkout_id = parsed.get("checkout_request_id")

        return PaymentResult(
            success=parsed.get("success", False),
            provider=self.provider_type.value,
            provider_transaction_id=checkout_id,
            provider_receipt=parsed.get("mpesa_receipt_number"),
            status="completed" if parsed.get("success") else "failed",
            raw_response=parsed,
            error_message=None if parsed.get("success") else parsed.get("result_desc"),
        )

    async def check_status(self, transaction_id: str) -> PaymentResult:
        """Query M-Pesa transaction status."""
        try:
            response = await query_stk_status(transaction_id)
            return PaymentResult(
                success=True,
                provider=self.provider_type.value,
                provider_transaction_id=transaction_id,
                status="completed",
                raw_response=response,
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                provider=self.provider_type.value,
                error_message=str(e),
            )


# Register as a payment provider
from app.services.payment_providers import register_provider, ProviderType
register_provider(ProviderType.mpesa_ke, MpesaKEProvider)


def parse_mpesa_callback(callback_data: dict) -> dict:
    """Parse M-Pesa STK Push callback response."""
    try:
        stk_callback = callback_data["Body"]["stkCallback"]
        result_code = stk_callback.get("ResultCode", -1)
        result_desc = stk_callback.get("ResultDesc", "")
        checkout_request_id = stk_callback.get("CheckoutRequestID", "")
        merchant_request_id = stk_callback.get("MerchantRequestID", "")

        if result_code == 0:
            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta_dict = {item["Name"]: item.get("Value") for item in metadata}
            return {
                "success": True,
                "result_code": result_code,
                "result_desc": result_desc,
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "amount": meta_dict.get("Amount"),
                "mpesa_receipt_number": meta_dict.get("MpesaReceiptNumber"),
                "transaction_date": meta_dict.get("TransactionDate"),
                "phone_number": str(meta_dict.get("PhoneNumber", "")),
            }
        else:
            return {
                "success": False,
                "result_code": result_code,
                "result_desc": result_desc,
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
            }
    except (KeyError, TypeError) as e:
        return {"success": False, "result_desc": f"Parse error: {str(e)}"}
