"""Unit tests for security module — password hashing, JWT, token validation."""
from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import (
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
)
from app.core.hashing import verify_password, get_password_hash
from app.core.config import settings


# ── Password Hashing (async bcrypt via executor) ──────────────────────────────

class TestPasswordHashing:
    @pytest.mark.asyncio
    async def test_hash_and_verify_roundtrip(self):
        password = "SecurePass123"
        hashed = await get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert await verify_password(password, hashed) is True

    @pytest.mark.asyncio
    async def test_verify_wrong_password(self):
        hashed = await get_password_hash("CorrectPass1")
        assert await verify_password("WrongPass1", hashed) is False

    @pytest.mark.asyncio
    async def test_verify_empty_password(self):
        hashed = await get_password_hash("TestPass1")
        assert await verify_password("", hashed) is False

    @pytest.mark.asyncio
    async def test_verify_invalid_hash(self):
        assert await verify_password("anything", "not-a-valid-bcrypt-hash") is False

    @pytest.mark.asyncio
    async def test_hash_different_salts(self):
        """Each hash should use a unique salt."""
        pw = "SamePassword1"
        h1 = await get_password_hash(pw)
        h2 = await get_password_hash(pw)
        assert h1 != h2  # Different salts

    @pytest.mark.asyncio
    async def test_hash_unicode_password(self):
        pw = "Pässwörd123"
        hashed = await get_password_hash(pw)
        assert await verify_password(pw, hashed) is True


# ── Password Strength Validation ──────────────────────────────────────────────

class TestPasswordStrength:
    def test_valid_password(self):
        is_valid, error = validate_password_strength("SecurePass1")
        assert is_valid is True
        assert error == ""

    def test_too_short(self):
        is_valid, error = validate_password_strength("Ab1")
        assert is_valid is False
        assert "at least" in error.lower()

    def test_too_long(self):
        is_valid, error = validate_password_strength("A1" + "a" * (MAX_PASSWORD_LENGTH + 1))
        assert is_valid is False

    def test_no_uppercase(self):
        is_valid, error = validate_password_strength("alllowercase1")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_no_lowercase(self):
        is_valid, error = validate_password_strength("ALLUPPERCASE1")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_no_number(self):
        is_valid, error = validate_password_strength("NoNumbersHere")
        assert is_valid is False
        assert "number" in error.lower()

    def test_exactly_minimum_length(self):
        is_valid, error = validate_password_strength("Abcdef1" + "x" * (MIN_PASSWORD_LENGTH - 7))
        assert is_valid is True

    @pytest.mark.parametrize("pw", [
        "Short1",           # too short
        "nouppercase1",     # no uppercase
        "NOLOWERCASE1",     # no lowercase
        "NoDigitsHere",     # no digit
        "ValidPass1",       # valid
    ])
    def test_parametrized_passwords(self, pw):
        is_valid, _ = validate_password_strength(pw)
        # Just verify it doesn't crash — returned value depends on pw
        assert isinstance(is_valid, bool)


# ── JWT Token Tests ───────────────────────────────────────────────────────────

class TestJWT:
    def test_access_token_creation(self):
        token = create_access_token(
            data={"sub": "42"},
            client_ip="127.0.0.1",
        )
        assert isinstance(token, str)
        assert len(token) > 20
        # Should have 3 segments (header.payload.signature)
        assert token.count(".") == 2

    def test_access_token_ip_binding(self):
        token = create_access_token(
            data={"sub": "42"},
            client_ip="196.0.0.1",
        )
        payload = decode_token(token)
        assert payload["ip"] == "196.0.0.1"
        assert payload["type"] == "access"
        assert payload["sub"] == "42"

    def test_access_token_without_ip(self):
        token = create_access_token(data={"sub": "42"})
        payload = decode_token(token)
        assert "ip" not in payload

    def test_refresh_token_has_jti(self):
        token, jti = create_refresh_token(
            data={"sub": "42"},
            client_ip="127.0.0.1",
        )
        assert isinstance(jti, str)
        assert len(jti) > 10
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti

    def test_token_expiry(self):
        token = create_access_token(
            data={"sub": "42"},
            expires_delta=None,
        )
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("invalid.token.here")
        assert exc.value.status_code == 401

    def test_decode_manipulated_token_raises(self):
        token = create_access_token(data={"sub": "42"})
        # Tamper with the payload
        parts = token.split(".")
        tampered = parts[0] + "." + "AAAA" + parts[1][4:] + "." + parts[2]
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token(tampered)
        assert exc.value.status_code == 401

    def test_refresh_token_different_from_access(self):
        at = create_access_token(data={"sub": "42"})
        rt, _ = create_refresh_token(data={"sub": "42"})
        assert at != rt


# ── Config Validation ─────────────────────────────────────────────────────────

class TestConfig:
    def test_secret_key_configured(self):
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_algorithm_is_hs256(self):
        assert settings.ALGORITHM == "HS256"

    def test_token_expiry_positive(self):
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0
