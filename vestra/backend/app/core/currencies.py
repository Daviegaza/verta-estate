"""
Multi-currency support for Vestra's global expansion.
Configurable per country, with exchange rate management.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Currency(StrEnum):
    """Supported currencies across Africa and globally."""
    KES = "KES"  # Kenya Shilling (primary)
    TZS = "TZS"  # Tanzania Shilling
    UGX = "UGX"  # Uganda Shilling
    NGN = "NGN"  # Nigeria Naira
    GHS = "GHS"  # Ghana Cedi
    ZAR = "ZAR"  # South Africa Rand
    RWF = "RWF"  # Rwanda Franc
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound


# ── Currency Metadata ────────────────────────────────────────────────────────

@dataclass
class CurrencyInfo:
    code: str
    name: str
    symbol: str
    locale: str          # For toLocaleString formatting
    decimals: int         # Number of decimal places
    countries: list[str]  # Countries where this currency is primary


CURRENCY_METADATA: dict[str, CurrencyInfo] = {
    "KES": CurrencyInfo("KES", "Kenya Shilling", "KES", "en-KE", 2, ["Kenya"]),
    "TZS": CurrencyInfo("TZS", "Tanzania Shilling", "TZS", "sw-TZ", 2, ["Tanzania"]),
    "UGX": CurrencyInfo("UGX", "Uganda Shilling", "UGX", "en-UG", 0, ["Uganda"]),
    "NGN": CurrencyInfo("NGN", "Nigeria Naira", "₦", "en-NG", 2, ["Nigeria"]),
    "GHS": CurrencyInfo("GHS", "Ghana Cedi", "GH₵", "en-GH", 2, ["Ghana"]),
    "ZAR": CurrencyInfo("ZAR", "South Africa Rand", "R", "en-ZA", 2, ["South Africa"]),
    "RWF": CurrencyInfo("RWF", "Rwanda Franc", "RWF", "rw-RW", 0, ["Rwanda"]),
    "USD": CurrencyInfo("USD", "US Dollar", "$", "en-US", 2, ["USA", "International"]),
    "EUR": CurrencyInfo("EUR", "Euro", "€", "en-DE", 2, ["Eurozone"]),
    "GBP": CurrencyInfo("GBP", "British Pound", "£", "en-GB", 2, ["United Kingdom"]),
}


# ── Exchange Rates (KES as base, updated daily via admin or cron) ────────────

# Default rates (KES = 1.0). In production, fetch from an API or update via admin.
DEFAULT_EXCHANGE_RATES: dict[str, Decimal] = {
    "KES": Decimal("1.0"),
    "TZS": Decimal("24.0"),     # 1 KES ≈ 24 TZS
    "UGX": Decimal("28.0"),     # 1 KES ≈ 28 UGX
    "NGN": Decimal("11.5"),     # 1 KES ≈ 11.5 NGN
    "GHS": Decimal("0.08"),     # 1 KES ≈ 0.08 GHS
    "ZAR": Decimal("0.14"),     # 1 KES ≈ 0.14 ZAR
    "RWF": Decimal("10.0"),     # 1 KES ≈ 10 RWF
    "USD": Decimal("0.0078"),   # 1 KES ≈ 0.0078 USD
    "EUR": Decimal("0.0072"),   # 1 KES ≈ 0.0072 EUR
    "GBP": Decimal("0.0062"),   # 1 KES ≈ 0.0062 GBP
}


def convert_currency(
    amount: Decimal | float,
    from_currency: str,
    to_currency: str,
    rates: dict[str, Decimal] | None = None,
) -> Decimal:
    """
    Convert between currencies using exchange rates.
    All conversions go through KES as base currency.
    """
    if from_currency == to_currency:
        return Decimal(str(amount))

    r = rates or DEFAULT_EXCHANGE_RATES

    amount_dec = Decimal(str(amount))
    from_rate = r.get(from_currency)
    to_rate = r.get(to_currency)

    if not from_rate or not to_rate:
        raise ValueError(f"Unknown currency: {from_currency if not from_rate else to_currency}")

    # Convert to KES first, then to target
    kes_amount = amount_dec / from_rate if from_rate != Decimal("0") else amount_dec
    target_amount = kes_amount * to_rate

    decimals = CURRENCY_METADATA.get(to_currency, CURRENCY_METADATA["KES"]).decimals
    return target_amount.quantize(Decimal(10) ** -decimals)


def format_price(amount: Decimal | float, currency: str) -> str:
    """Human-readable price string with currency symbol."""
    info = CURRENCY_METADATA.get(currency, CURRENCY_METADATA["KES"])
    amt = Decimal(str(amount))
    if info.decimals == 0:
        return f"{info.symbol} {int(amt):,}"
    return f"{info.symbol} {amt:,.{info.decimals}f}"


# ── Country Configurations ────────────────────────────────────────────────────

@dataclass
class CountryConfig:
    country_code: str       # ISO 3166-1 alpha-2
    country_name: str
    default_currency: str
    phone_prefix: str       # e.g., "+254"
    phone_format: str       # Regex for validation
    required_documents: dict[str, list[str]]  # Per listing type
    price_bands: dict       # City-level price bands (or use Kenya's as default)
    languages: list[str]    # Official languages
    mpesa_available: bool
    stripe_available: bool


COUNTRY_CONFIGS: dict[str, CountryConfig] = {
    "KE": CountryConfig(
        country_code="KE",
        country_name="Kenya",
        default_currency="KES",
        phone_prefix="+254",
        phone_format=r"^\+254\d{9}$",
        required_documents={
            "sale": ["title_deed", "sale_agreement", "kra_pin", "national_id", "land_search", "rates_clearance"],
            "rent": ["lease_agreement", "national_id"],
            "lease": ["lease_agreement", "kra_pin", "national_id"],
        },
        price_bands={},  # Uses KENYA_PRICE_BANDS from engine.py
        languages=["en", "sw"],
        mpesa_available=True,
        stripe_available=True,
    ),
    "TZ": CountryConfig(
        country_code="TZ",
        country_name="Tanzania",
        default_currency="TZS",
        phone_prefix="+255",
        phone_format=r"^\+255\d{9}$",
        required_documents={
            "sale": ["title_deed", "sale_agreement", "national_id", "land_search"],
            "rent": ["lease_agreement", "national_id"],
            "lease": ["lease_agreement", "national_id"],
        },
        price_bands={},
        languages=["sw", "en"],
        mpesa_available=True,   # M-Pesa Tanzania
        stripe_available=False,
    ),
    "UG": CountryConfig(
        country_code="UG",
        country_name="Uganda",
        default_currency="UGX",
        phone_prefix="+256",
        phone_format=r"^\+256\d{9}$",
        required_documents={
            "sale": ["title_deed", "sale_agreement", "national_id", "land_search"],
            "rent": ["lease_agreement", "national_id"],
            "lease": ["lease_agreement", "national_id"],
        },
        price_bands={},
        languages=["en", "sw", "lg"],
        mpesa_available=False,  # MTN Mobile Money instead
        stripe_available=False,
    ),
}


def get_country_config(country_code: str = "KE") -> CountryConfig:
    """Get configuration for a country. Falls back to Kenya."""
    return COUNTRY_CONFIGS.get(country_code.upper(), COUNTRY_CONFIGS["KE"])


def get_currency_for_country(country_code: str) -> str:
    """Get default currency for a country."""
    config = get_country_config(country_code)
    return config.default_currency


# ── Auto-detection from IP / Location ─────────────────────────────────────────

def detect_country_from_phone(phone: str) -> str | None:
    """Detect country code from phone number prefix."""
    if not phone:
        return None
    normalized = phone.replace("+", "").replace(" ", "").strip()
    if normalized.startswith("254"):
        return "KE"
    if normalized.startswith("255"):
        return "TZ"
    if normalized.startswith("256"):
        return "UG"
    if normalized.startswith("234"):
        return "NG"
    if normalized.startswith("233"):
        return "GH"
    if normalized.startswith("27"):
        return "ZA"
    if normalized.startswith("250"):
        return "RW"
    return None


# Simple IP-to-country mapping for common African IP ranges
# In production, use a proper GeoIP database (MaxMind, IP2Location)
_IP_COUNTRY_MAP = {
    # Kenya
    "41.": "KE", "102.": "KE", "105.": "KE", "154.": "KE", "196.": "KE", "197.": "KE",
    # Tanzania
    "41.59.": "TZ", "41.93.": "TZ", "196.41.": "TZ",
    # Uganda
    "41.75.": "UG", "41.190.": "UG", "154.72.": "UG",
    # Nigeria
    "41.58.": "NG", "102.89.": "NG", "105.112.": "NG",
    # Ghana
    "41.66.": "GH", "102.176.": "GH",
    # South Africa
    "41.0.": "ZA", "41.185.": "ZA", "102.0.": "ZA", "105.0.": "ZA",
}


def detect_country_from_ip(ip_address: str) -> str:
    """
    Detect country from IP address using simple prefix matching.
    Falls back to KE (Kenya) when unknown.
    For production, integrate with MaxMind GeoIP or Cloudflare CF-IPCountry header.
    """
    # Check Cloudflare country header (if behind Cloudflare proxy)
    # This would be passed from the request middleware

    # Simple IP prefix matching
    for prefix, country in sorted(_IP_COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
        if ip_address.startswith(prefix):
            return country
    return "KE"  # Default to Kenya


def auto_detect_user_config(
    ip_address: str = "41.0.0.0",
    phone: str | None = None,
    explicit_country: str | None = None,
) -> dict:
    """
    Auto-detect user configuration based on available signals.
    Priority: explicit > phone prefix > IP geo > Kenya default.

    Returns the full configuration a user needs — no manual setup required.
    """
    # 1. Explicit country selection
    if explicit_country and explicit_country.upper() in COUNTRY_CONFIGS:
        country = explicit_country.upper()
    # 2. Phone number prefix
    elif phone and detect_country_from_phone(phone):
        country = detect_country_from_phone(phone)
    # 3. IP-based detection
    else:
        country = detect_country_from_ip(ip_address)

    config = get_country_config(country)
    currency_info = CURRENCY_METADATA.get(config.default_currency, CURRENCY_METADATA["KES"])

    return {
        "country": config.country_name,
        "country_code": config.country_code,
        "currency": config.default_currency,
        "currency_symbol": currency_info.symbol,
        "currency_name": currency_info.name,
        "locale": currency_info.locale,
        "phone_prefix": config.phone_prefix,
        "languages": config.languages,
        "mpesa_available": config.mpesa_available,
        "stripe_available": config.stripe_available,
        "auto_detected": not bool(explicit_country),
        "detection_method": "explicit" if explicit_country else (
            "phone" if phone else "ip" if ip_address else "default"
        ),
    }
