"""
Fernet-based encryption for sensitive fields at rest.

Provides deterministic encrypt/decrypt wrappers around the cryptography
library's Fernet (AES-128-CBC with HMAC-SHA256). The encryption key is
loaded from settings.ENCRYPTION_KEY; if empty at startup, a new key is
generated and logged (development only).

Usage:
    from app.core.encryption import encrypt_field, decrypt_field

    ciphertext = encrypt_field("+254712345678")
    plaintext  = decrypt_field(ciphertext)
"""
from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger("vestra")

# ── Key loading ─────────────────────────────────────────────────────────────

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return the Fernet cipher, initialising it on first call."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key_str = settings.ENCRYPTION_KEY
    if not key_str:
        # Auto-generate a key in development for convenience.
        raw_key = Fernet.generate_key()
        key_str = raw_key.decode()
        if settings.ENVIRONMENT == "development":
            logger.warning(
                '{"event":"encryption_key_auto_generated","warning":"ENCRYPTION_KEY '
                'not set — generated ephemeral key. Data encrypted with this key '
                'will be unreadable after restart."}'
            )
        else:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. Set a valid Fernet key in .env or "
                "generate one with: python -c \"from cryptography.fernet import "
                "Fernet; print(Fernet.generate_key().decode())\""
            )

    try:
        _fernet = Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
    except Exception as exc:
        raise ValueError(
            f"Invalid ENCRYPTION_KEY: {exc}. Generate a valid key with: "
            f"python -c \"from cryptography.fernet import Fernet; "
            f"print(Fernet.generate_key().decode())\""
        ) from exc

    return _fernet


# ── Public API ──────────────────────────────────────────────────────────────


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None when given None."""
    if plaintext is None:
        return None
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string. Returns None when given None."""
    if ciphertext is None:
        return None
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error('{"event":"decryption_failed","error":"invalid_token"}')
        return None
    except Exception as exc:
        logger.error('{"event":"decryption_failed","error":"%s"}', exc)
        return None
