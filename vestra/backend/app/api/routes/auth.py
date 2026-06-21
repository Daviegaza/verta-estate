"""
Authentication routes — register, login, password reset, email verification,
TOTP 2FA, session management, and GDPR compliance.
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pyotp
import qrcode
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.security import (
    OAuth2PasswordRequestForm,  # noqa: TC002 — used at runtime as FastAPI Depends()
)
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_db
from app.core.hashing import get_password_hash, verify_password
from app.core.redis import (
    cache_delete,
    cache_get,
    cache_set,
    get_redis,
    is_refresh_token_valid,
    revoke_all_refresh_tokens,
    store_refresh_token,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_optional,
    validate_password_strength,
)
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
    TokenRefreshResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.analytics_service import fire_and_forget_track_user_event
from app.services.captcha_service import verify_turnstile
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Module-level set to hold references to fire-and-forget tasks so they
# are not garbage-collected mid-execution.
_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> asyncio.Task:
    """Schedule *coro* and keep a reference to prevent GC (RUF006)."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


# ── Register ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and send verification email."""
    # ── CAPTCHA verification (Cloudflare Turnstile) ────────────────────────
    if settings.ENVIRONMENT == "production" or settings.TURNSTILE_SECRET_KEY:
        captcha_ok = await verify_turnstile(user_data.turnstile_token or "")
        if not captcha_ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPTCHA verification failed. Please complete the CAPTCHA challenge.",
            )

    # Validate password strength
    is_valid, pw_error = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_error)

    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await create_user(db, user_data, referral_code=user_data.referral_code)
    client_ip = request.client.host if request.client else None
    token = create_access_token({"sub": str(user.id)}, client_ip=client_ip)
    refresh_token_str, refresh_jti = create_refresh_token({"sub": str(user.id)}, client_ip=client_ip)

    # Store refresh token in Redis
    _fire_and_forget(
        store_refresh_token(user.id, refresh_jti, ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    )

    # Store session metadata
    _fire_and_forget(
        _store_session_metadata(
            user_id=user.id,
            jti=refresh_jti,
            request=request,
            client_ip=client_ip,
        )
    )

    # Send verification email in background
    verify_token = secrets.token_urlsafe(32)
    await cache_set(f"vestra:email_verify:{verify_token}", user.id, ttl=86400)  # 24h
    background_tasks.add_task(send_verification_email, user.email, user.full_name, verify_token)

    # ── Fire-and-forget: track registration event ────────────────────────
    _fire_and_forget(
        fire_and_forget_track_user_event(
            user_id=user.id,
            event_type="registration",
            event_data={"email": user.email, "role": user.role.value if user.role else "buyer"},
        )
    )

    # ── Fire-and-forget: send welcome notification ───────────────────────
    _fire_and_forget(
        _bg_send_welcome_notification(user.id, user.full_name)
    )

    return Token(
        access_token=token,
        refresh_token=refresh_token_str,
        user=UserResponse.model_validate(user),
    )


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Token is IP-bound for security.

    If the user has two-factor authentication enabled, this endpoint returns
    a partial login response with ``{"2fa_required": true}`` and the caller
    must complete authentication via ``POST /auth/2fa/verify`` with the
    ``temp_token`` and the TOTP code.
    """
    client_ip = request.client.host if request.client else "unknown"
    lockout_key = f"vestra:lockout:{form_data.email}:{client_ip}"

    # ── Account lockout check (Redis-backed, fails open if Redis down) ─────
    r = await get_redis()
    if r is not None:
        lockout_count_str = await r.get(f"{lockout_key}:count")
        lockout_count = int(lockout_count_str) if lockout_count_str else 0

        if lockout_count >= settings.ACCOUNT_LOCKOUT_MAX_ATTEMPTS:
            ttl = await r.ttl(f"{lockout_key}:count")
            retry_after = max(ttl, 0)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "account_locked",
                    "message": f"Too many failed login attempts. Please try again in {retry_after // 60 + 1} minutes.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        # ── Increment failure counter (only if Redis available) ──────────
        if r is not None:
            lockout_duration = settings.ACCOUNT_LOCKOUT_DURATION_MINUTES * 60
            await r.incr(f"{lockout_key}:count")
            await r.expire(f"{lockout_key}:count", lockout_duration)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "message": "Incorrect email or password.",
            },
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support.",
        )
    if not user.is_verified:
        # In development, auto-verify users to avoid email setup requirement
        if settings.ENVIRONMENT == "development":
            user.is_verified = True
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in. Check your inbox.",
            )

    # ── Two-factor authentication check ───────────────────────────────────
    if user.two_factor_enabled:
        # Generate a short-lived temporary token to prove password check passed
        temp_token = secrets.token_urlsafe(32)
        temp_ttl = 300  # 5 minutes
        await cache_set(
            f"vestra:2fa_temp:{temp_token}",
            {"user_id": user.id, "client_ip": client_ip},
            ttl=temp_ttl,
        )
        return {
            "2fa_required": True,
            "temp_token": temp_token,
            "message": "Two-factor authentication is enabled. Please provide your TOTP code.",
            "expires_in": temp_ttl,
        }

    # ── Reset lockout counter on successful login ──────────────────────────
    if r is not None:
        await r.delete(f"{lockout_key}:count")

    token = create_access_token({"sub": str(user.id)}, client_ip=client_ip)
    refresh_token_str, refresh_jti = create_refresh_token({"sub": str(user.id)}, client_ip=client_ip)

    # Store refresh token in Redis
    _fire_and_forget(
        store_refresh_token(user.id, refresh_jti, ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    )

    # Store session metadata
    _fire_and_forget(
        _store_session_metadata(
            user_id=user.id,
            jti=refresh_jti,
            request=request,
            client_ip=client_ip,
        )
    )

    # Enforce max concurrent sessions
    _fire_and_forget(
        _enforce_max_sessions(user.id)
    )

    # ── Fire-and-forget: track login event ─────────────────────────────
    _fire_and_forget(
        fire_and_forget_track_user_event(
            user_id=user.id,
            event_type="login",
            event_data={"email": user.email, "role": user.role.value if user.role else "buyer"},
        )
    )
    return Token(
        access_token=token,
        refresh_token=refresh_token_str,
        user=UserResponse.model_validate(user),
    )


# ── OAuth2 form login (for Swagger UI) ─────────────────────────────────────────

@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 password flow — used by Swagger UI /api/docs."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account suspended")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserResponse.model_validate(user))


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    updated = await update_user(db, current_user, update_data)
    return updated


# ── Change Password ────────────────────────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    if not await verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = await get_password_hash(data.new_password)
    await db.commit()

    # Invalidate all existing sessions
    await cache_delete(f"vestra:refresh:{current_user.id}:*")

    return {"message": "Password changed successfully. Please log in again."}


# ── Forgot / Reset Password ────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a password reset email if the account exists."""
    user = await get_user_by_email(db, data.email)

    # Always return success to prevent email enumeration
    if user and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        # Store token → user_id mapping (30 min TTL)
        await cache_set(f"vestra:pw_reset:{reset_token}", user.id, ttl=1800)
        background_tasks.add_task(
            send_password_reset_email, user.email, user.full_name, reset_token
        )

    return {
        "message": "If an account exists with that email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid reset token."""
    user_id = await cache_get(f"vestra:pw_reset:{data.token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new one.",
        )

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = await get_password_hash(data.new_password)
    await db.commit()

    # Invalidate the token and all existing sessions
    await cache_delete(f"vestra:pw_reset:{data.token}")
    await cache_delete(f"vestra:refresh:{user.id}:*")

    return {"message": "Password has been reset. You can now log in."}


# ── Referral Code ──────────────────────────────────────────────────────────────


@router.get("/referral-code")
async def get_auth_referral_code(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's referral code, stats, and share link."""
    from app.services.referral_engine import generate_referral_code, get_user_referral_stats

    # Ensure code exists
    if not current_user.referral_code:
        await generate_referral_code(db, current_user.id)

    stats = await get_user_referral_stats(db, current_user.id)
    return stats


# ── Email Verification ─────────────────────────────────────────────────────────

@router.post("/verify-email")
async def verify_email(token: str = "", db: AsyncSession = Depends(get_db)):
    """Verify user email with the token sent during registration."""
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")

    user_id = await cache_get(f"vestra:email_verify:{token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token. Please register again.",
        )

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()

    # Clean up token
    await cache_delete(f"vestra:email_verify:{token}")

    # Send welcome email
    _fire_and_forget(send_welcome_email(user.email, user.full_name))

    # ── Track referral status: signed_up → active (verified) ──────────────

    _fire_and_forget(_bg_update_referral_on_verify(user.id))

    # ── Fire analytics event: email_verified ──────────────────────────────
    _fire_and_forget(
        fire_and_forget_track_user_event(
            user_id=user.id,
            event_type="email_verified",
            event_data={"email": user.email},
        )
    )

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
async def resend_verification(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resend verification email."""
    user = await get_user_by_email(db, email)
    if not user:
        # Don't reveal whether email exists
        return {"message": "If that email is registered, a verification link has been sent."}

    if user.is_verified:
        return {"message": "Email is already verified."}

    verify_token = secrets.token_urlsafe(32)
    await cache_set(f"vestra:email_verify:{verify_token}", user.id, ttl=86400)
    background_tasks.add_task(send_verification_email, user.email, user.full_name, verify_token)

    return {"message": "Verification email sent. Check your inbox."}


# ── Refresh Token ──────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
):
    """
    Rotate refresh tokens.
    1. Validates the refresh token JWT
    2. Checks it hasn't been revoked (Redis lookup)
    3. Issues a new access token AND a new refresh token
    4. Revokes the old refresh token, stores the new one
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "invalid_refresh_token",
            "message": "Your session has expired. Please log in again.",
        },
    )

    try:
        payload = jwt.decode(
            data.refresh_token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")
        jti = payload.get("jti")

        if user_id is None or token_type != "refresh" or jti is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    # Check token is not revoked in Redis
    user_id_int = int(user_id)
    valid = await is_refresh_token_valid(user_id_int, jti)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "refresh_token_revoked",
                "message": "This session has been revoked. Please log in again.",
            },
        )

    # Issue new tokens (rotate)
    client_ip = request.client.host if request.client else None
    new_access_token = create_access_token({"sub": str(user_id_int)}, client_ip=client_ip)
    new_refresh_token, new_jti = create_refresh_token({"sub": str(user_id_int)}, client_ip=client_ip)

    # Revoke old refresh token + session metadata, store the new one
    r = await get_redis()
    if r is not None:
        await r.delete(f"vestra:refresh:{user_id_int}:{jti}")
        await r.delete(f"vestra:session:{user_id_int}:{jti}")
    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await store_refresh_token(user_id_int, new_jti, ttl=refresh_ttl)

    # Store new session metadata
    _fire_and_forget(
        _store_session_metadata(
            user_id=user_id_int,
            jti=new_jti,
            request=request,
            client_ip=client_ip,
        )
    )

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    """
    Logout the current user by revoking all their refresh tokens
    and removing session metadata.
    The current access token will expire naturally (1h TTL).
    """
    await revoke_all_refresh_tokens(current_user.id)
    await cache_delete(f"vestra:session:{current_user.id}:*")
    return {"message": "Logged out successfully"}


# ── 2FA ────────────────────────────────────────────────────────────────────────


@router.post("/2fa/setup")
async def setup_2fa(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and return a provisioning URI + QR code data URL.

    The user should scan the QR code into their authenticator app (Google
    Authenticator, Authy, etc.) and then call ``/2fa/verify`` to confirm.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled. Disable it first to re-setup.",
        )

    # Generate a new TOTP secret
    totp_secret = pyotp.random_base32()
    issuer = settings.APP_NAME
    provisioning_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=current_user.email,
        issuer_name=issuer,
    )

    # Generate QR code as a base64 data URL
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

    # Persist the secret so the next /2fa/verify call can validate
    current_user.totp_secret = totp_secret
    await db.commit()

    return {
        "secret": totp_secret,
        "provisioning_uri": provisioning_uri,
        "qr_code": qr_data_url,
        "message": "Scan the QR code with your authenticator app, then call /auth/2fa/verify to confirm.",
    }


@router.post("/2fa/verify")
async def verify_2fa(
    totp_code: str = Query(..., description="6-digit TOTP code from authenticator app"),
    temp_token: str = Query(None, description="Temp token from login when 2fa_required=true"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Verify a TOTP code to enable 2FA, or to complete a 2FA login step.

    Two modes:
      1. **Authenticated setup** — The user is already logged in and wants
         to enable 2FA. Pass only ``totp_code``.
      2. **Login completion** — The user has ``2fa_required`` from ``/login``
         and must pass both ``totp_code`` and the ``temp_token`` from the
         login response to receive their JWT tokens.
    """
    if temp_token:
        # ── Login completion mode ──────────────────────────────────────────
        temp_data = await cache_get(f"vestra:2fa_temp:{temp_token}")
        if not temp_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "temp_token_expired",
                    "message": "The temporary login token has expired. Please log in again.",
                },
            )

        user_id = temp_data.get("user_id")
        client_ip = temp_data.get("client_ip", "unknown")

        # Fetch the user fresh from DB to get the TOTP secret
        user = await get_user_by_id(db, user_id)
        if not user or not user.two_factor_enabled or not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Two-factor authentication is not configured for this account.",
            )

        # Verify TOTP code
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_totp",
                    "message": "Invalid TOTP code. Please try again.",
                },
            )

        # Consume the temp token so it cannot be replayed
        await cache_delete(f"vestra:2fa_temp:{temp_token}")

        # Issue real tokens
        token = create_access_token({"sub": str(user.id)}, client_ip=client_ip)
        refresh_token_str, refresh_jti = create_refresh_token({"sub": str(user.id)}, client_ip=client_ip)

        _fire_and_forget(
            store_refresh_token(user.id, refresh_jti, ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
        )
        _fire_and_forget(
            _store_session_metadata(
                user_id=user.id, jti=refresh_jti, request=request, client_ip=client_ip,
            )
        )

        return Token(
            access_token=token,
            refresh_token=refresh_token_str,
            user=UserResponse.model_validate(user),
        )

    # ── Setup completion mode (user must be authenticated) ─────────────────
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": "You must be logged in to enable two-factor authentication. "
                           "Or provide a temp_token to complete a 2FA login step.",
            },
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP secret found. Call /auth/2fa/setup first.",
        )

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please try again.",
        )

    current_user.two_factor_enabled = True
    await db.commit()

    return {
        "message": "Two-factor authentication has been enabled successfully.",
        "two_factor_enabled": True,
    }


@router.post("/2fa/disable")
async def disable_2fa(
    password: str = Query(..., description="Current password to confirm identity"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable two-factor authentication. Requires the current password."""
    if not await verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Please try again.",
        )

    current_user.totp_secret = None
    current_user.two_factor_enabled = False
    await db.commit()

    return {
        "message": "Two-factor authentication has been disabled.",
        "two_factor_enabled": False,
    }


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    current_user=Depends(get_current_user),
):
    """List all active sessions for the current user."""
    r = await get_redis()
    if r is None:
        return {"sessions": [], "message": "Session store unavailable."}

    cursor = 0
    sessions = []
    while True:
        cursor, keys = await r.scan(cursor, match=f"vestra:session:{current_user.id}:*", count=100)
        for key in keys:
            data = await r.hgetall(key)
            if data:
                session_id = key.split(":")[-1]
                sessions.append({
                    "id": session_id,
                    "device": data.get("device", "Unknown"),
                    "ip": data.get("ip", ""),
                    "user_agent": data.get("user_agent", ""),
                    "created_at": data.get("created_at", ""),
                    "current": False,  # Will be marked below
                })
        if cursor == 0:
            break

    # Mark the current session (based on the current JWT's jti — we can't
    # extract it from the access token, so we leave it to the client to
    # identify or simply sort by recency)
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Revoke a specific session by its ID (JTI from the refresh token)."""
    r = await get_redis()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store unavailable.",
        )

    # Remove the refresh token and session metadata
    refresh_key = f"vestra:refresh:{current_user.id}:{session_id}"
    session_key = f"vestra:session:{current_user.id}:{session_id}"

    deleted = await r.delete(refresh_key)
    await r.delete(session_key)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    return {"message": "Session revoked successfully."}


# ── GDPR Compliance ───────────────────────────────────────────────────────────

@router.get("/user/export")
async def export_user_data(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all personal data for the current user (GDPR Article 15)."""
    from app.models.payment import Payment
    from app.models.property import Property

    # Gather user data
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,  # Auto-decrypted via property
        "full_name": current_user.full_name,
        "role": current_user.role.value if current_user.role else None,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "is_kyc_verified": current_user.is_kyc_verified,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "location": current_user.location,
        "national_id": current_user.national_id,  # Auto-decrypted via property
        "referral_code": current_user.referral_code,
        "two_factor_enabled": current_user.two_factor_enabled,
        "consent_marketing": current_user.consent_marketing,
        "consent_data_processing": current_user.consent_data_processing,
        "consent_date": str(current_user.consent_date) if current_user.consent_date else None,
        "created_at": str(current_user.created_at),
        "updated_at": str(current_user.updated_at),
    }

    # Gather related data
    properties_result = await db.execute(
        __import__("sqlalchemy").select(Property).where(Property.owner_id == current_user.id)
    )
    properties = properties_result.scalars().all()
    user_data["properties"] = [
        {
            "id": p.id,
            "title": p.title,
            "price": float(p.price) if p.price else None,
            "status": p.status.value if p.status else None,
            "created_at": str(p.created_at),
        }
        for p in properties
    ]

    payments_result = await db.execute(
        __import__("sqlalchemy").select(Payment).where(Payment.user_id == current_user.id)
    )
    payments = payments_result.scalars().all()
    user_data["payments"] = [
        {
            "id": p.id,
            "amount": float(p.amount) if p.amount else None,
            "status": p.status.value if p.status else None,
            "method": p.method.value if p.method else None,
            "created_at": str(p.created_at),
        }
        for p in payments
    ]

    return {
        "export_date": datetime.now(UTC).isoformat(),
        "data": user_data,
    }


@router.delete("/user/data")
async def delete_user_data(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anonymize user data (GDPR Right to be Forgotten — Article 17).

    This does NOT delete the user record (which would break referential
    integrity with properties, payments, etc.). Instead, it replaces all
    personally identifiable information with anonymised placeholders.
    """
    from app.models.user import UserRole

    if current_user.role == UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin accounts cannot be anonymized through this endpoint.",
        )

    anon_suffix = f"-deleted-{secrets.token_hex(4)}"

    # Scrub PII fields
    current_user.full_name = f"Deleted User {anon_suffix}"
    current_user.email = f"deleted{anon_suffix}@vestra.co.ke"
    current_user._phone = None  # Direct column access to avoid encryption
    current_user._national_id = None
    current_user.avatar_url = None
    current_user.bio = None
    current_user.location = None
    current_user.is_active = False
    current_user.is_verified = False
    current_user.referral_code = None
    current_user.totp_secret = None
    current_user.two_factor_enabled = False
    current_user.consent_marketing = False
    current_user.consent_data_processing = False

    await db.commit()

    # Revoke all sessions
    await revoke_all_refresh_tokens(current_user.id)
    await cache_delete(f"vestra:session:{current_user.id}:*")

    return {
        "message": "Your personal data has been anonymized. You can no longer log in with this account.",
        "anonymized": True,
    }


# ── Session helpers & background tasks ────────────────────────────────────────


async def _store_session_metadata(
    user_id: int,
    jti: str,
    request: Request,
    client_ip: str | None,
) -> None:
    """Store session metadata in Redis for a newly-created token."""
    r = await get_redis()
    if r is None:
        return

    user_agent = request.headers.get("user-agent", "") if request else ""
    # Derive a simple device label from the user-agent
    device = _derive_device(user_agent)

    session_key = f"vestra:session:{user_id}:{jti}"
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    try:
        await r.hset(session_key, mapping={
            "device": device,
            "ip": client_ip or "",
            "user_agent": user_agent[:500],
            "created_at": datetime.now(UTC).isoformat(),
        })
        await r.expire(session_key, ttl)
    except Exception:
        logger.warning('{"event":"store_session_failed","user_id":%d}', user_id)


async def _enforce_max_sessions(user_id: int) -> None:
    """If the user exceeds MAX_CONCURRENT_SESSIONS, evict the oldest session."""
    r = await get_redis()
    if r is None:
        return

    max_sessions = settings.MAX_CONCURRENT_SESSIONS

    cursor = 0
    session_keys = []
    while True:
        cursor, keys = await r.scan(cursor, match=f"vestra:session:{user_id}:*", count=100)
        session_keys.extend(keys)
        if cursor == 0:
            break

    if len(session_keys) <= max_sessions:
        return

    # Sort by created_at (oldest first) and remove excess
    sessions = []
    for key in session_keys:
        data = await r.hgetall(key)
        created = data.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created)
            except ValueError:
                dt = datetime.min.replace(tzinfo=UTC)
        else:
            dt = datetime.min.replace(tzinfo=UTC)
        sessions.append((dt, key))

    sessions.sort(key=lambda x: x[0])
    # Evict oldest sessions beyond the limit
    to_evict = sessions[:len(sessions) - max_sessions]
    for _, key in to_evict:
        jti = key.split(":")[-1]
        await r.delete(f"vestra:refresh:{user_id}:{jti}")
        await r.delete(key)


def _derive_device(user_agent: str) -> str:
    """Derive a friendly device name from the User-Agent string."""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua or "ipad" in ua:
        if "android" in ua:
            return "Android"
        if "iphone" in ua or "ipad" in ua:
            return "iOS"
        return "Mobile"
    if "windows" in ua:
        return "Windows"
    if "mac" in ua:
        return "macOS"
    if "linux" in ua:
        return "Linux"
    if "postman" in ua:
        return "Postman"
    if "curl" in ua:
        return "CLI"
    return "Unknown"


# ── Background helpers ─────────────────────────────────────────────────────────


async def _bg_send_welcome_notification(user_id: int, full_name: str) -> None:
    """Fire-and-forget: send welcome notification after registration."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import send_welcome_notification

    try:
        async with AsyncSessionLocal() as bg_db:
            await send_welcome_notification(bg_db, user_id, full_name)
    except Exception:
        logger.warning('{"event":"bg_welcome_notification_failed","user_id":%d}', user_id)


async def _bg_update_referral_on_verify(user_id: int) -> None:
    """Fire-and-forget: update referral to active on email verification."""
    from app.core.database import AsyncSessionLocal
    from app.services.referral_engine import award_referral_reward, track_referral_verified

    try:
        async with AsyncSessionLocal() as bg_db:
            await track_referral_verified(bg_db, user_id)
            # Also award the signup_verified reward if not already done
            await award_referral_reward(bg_db, user_id, "signup_verified")
    except Exception:
        logger.warning('{"event":"bg_referral_verify_failed","user_id":%d}', user_id)
