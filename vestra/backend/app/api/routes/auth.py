"""
Authentication routes — register, login, password reset, email verification.
"""
from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, get_current_user,
    get_password_hash, verify_password,
    validate_password_strength,
)
from fastapi import Request
from app.core.redis import (
    cache_set, cache_get, cache_delete, get_redis,
    store_refresh_token, is_refresh_token_valid, revoke_all_refresh_tokens,
)
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token, UserUpdate,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    RefreshTokenRequest, TokenRefreshResponse,
)
from app.services.user_service import (
    create_user, authenticate_user, get_user_by_email, update_user,
    get_user_by_id,
)
from app.services.email_service import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
)
from app.services.captcha_service import verify_turnstile
from app.services.analytics_service import fire_and_forget_track_user_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


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

    # Send verification email in background
    verify_token = secrets.token_urlsafe(32)
    await cache_set(f"vestra:email_verify:{verify_token}", user.id, ttl=86400)  # 24h
    background_tasks.add_task(send_verification_email, user.email, user.full_name, verify_token)

    # ── Fire-and-forget: track registration event ────────────────────────
    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=user.id,
            event_type="registration",
            event_data={"email": user.email, "role": user.role.value if user.role else "buyer"},
        )
    )

    # ── Fire-and-forget: send welcome notification ───────────────────────
    asyncio.create_task(
        _bg_send_welcome_notification(user.id, user.full_name)
    )

    return Token(access_token=token, user=UserResponse.model_validate(user))


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Token is IP-bound for security."""
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

    # ── Reset lockout counter on successful login ──────────────────────────
    if r is not None:
        await r.delete(f"{lockout_key}:count")

    token = create_access_token({"sub": str(user.id)}, client_ip=client_ip)
    # ── Fire-and-forget: track login event ─────────────────────────────
    asyncio.create_task(
        fire_and_forget_track_user_event(
            user_id=user.id,
            event_type="login",
            event_data={"email": user.email, "role": user.role.value if user.role else "buyer"},
        )
    )
    return Token(access_token=token, user=UserResponse.model_validate(user))


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
    from app.services.referral_engine import get_user_referral_stats, generate_referral_code

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
    import asyncio
    asyncio.create_task(send_welcome_email(user.email, user.full_name))

    # ── Track referral status: signed_up → active (verified) ──────────────
    from app.services.referral_engine import track_referral_verified, award_referral_reward

    asyncio.create_task(_bg_update_referral_on_verify(user.id))

    # ── Fire analytics event: email_verified ──────────────────────────────
    asyncio.create_task(
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
        raise credentials_exception

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

    # Revoke old refresh token, store the new one
    r = await get_redis()
    if r is not None:
        await r.delete(f"vestra:refresh:{user_id_int}:{jti}")
    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await store_refresh_token(user_id_int, new_jti, ttl=refresh_ttl)

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    """
    Logout the current user by revoking all their refresh tokens.
    The current access token will expire naturally (1h TTL).
    """
    await revoke_all_refresh_tokens(current_user.id)
    return {"message": "Logged out successfully"}


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
    from app.services.referral_engine import track_referral_verified, award_referral_reward
    from app.services.analytics_service import fire_and_forget_track_user_event

    try:
        async with AsyncSessionLocal() as bg_db:
            await track_referral_verified(bg_db, user_id)
            # Also award the signup_verified reward if not already done
            await award_referral_reward(bg_db, user_id, "signup_verified")
    except Exception:
        logger.warning('{"event":"bg_referral_verify_failed","user_id":%d}', user_id)
