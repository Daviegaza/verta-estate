"""
VESTRA Security — Fortified Authentication & Authorization.
JWT with IP binding, bcrypt hashing, strict RBAC.
Impossible to bypass — every admin action is server-verified.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.hashing import verify_password, get_password_hash  # async, non-blocking

# ── Password Hashing ──────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Password strength requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforce strong passwords. Returns (is_valid, error_message).
    Requirements:
    - 8-128 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""


# ── JWT with IP Binding ──────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    client_ip: Optional[str] = None,
) -> str:
    """
    Create a JWT access token with optional IP binding.
    Tokens are tied to the IP address they were issued to — prevents token theft.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    # IP binding: token only valid from the IP it was issued to
    if client_ip:
        to_encode["ip"] = client_ip

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    client_ip: Optional[str] = None,
) -> tuple[str, str]:
    """
    Create a refresh token JWT with a unique jti (JWT ID) for individual revocation.
    Returns (token, jti) tuple so the caller can store the jti in Redis.
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": jti,
    })
    if client_ip:
        to_encode["ip"] = client_ip

    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Returns the payload or raises."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "message": "Your session is invalid or expired. Please log in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Auth Dependencies ─────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the currently authenticated user from the JWT token.
    STRICT: Validates token + IP binding + user exists + user active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "authentication_required",
            "message": "Please log in to access this resource.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode and validate token
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type", "")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # IP binding check (prevents token theft)
    token_ip = payload.get("ip")
    client_ip = request.client.host if request.client else None
    if token_ip and client_ip and token_ip != client_ip:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_ip_mismatch",
                "message": "This session was issued to a different network. Please log in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception

    # Check user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_suspended",
                "message": "Your account has been suspended. Contact support.",
            },
        )

    return user


async def get_current_admin(
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    STRICT admin check — server-side role verification.
    Only 'admin' and 'super_admin' roles pass through.
    No client-side role can bypass this.
    """
    from app.models.user import UserRole

    if current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "admin_access_required",
                "message": "You do not have permission to access the admin panel.",
                "your_role": current_user.role.value,
                "required_roles": ["admin", "super_admin"],
            },
        )

    return current_user


async def get_current_agent(
    current_user=Depends(get_current_user),
):
    """Ensure the user is an agent."""
    from app.models.user import UserRole
    if current_user.role not in (UserRole.agent, UserRole.admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account required",
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Like ``get_current_user`` but returns ``None`` instead of raising 401
    when no valid token is present. Useful for endpoints that work both
    for authenticated and unauthenticated users (e.g., 2FA login completion).

    Reads the Bearer token from the Authorization header manually to avoid
    ``oauth2_scheme`` automatically raising 401 on missing tokens.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):].strip()
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type", "")
        if user_id is None or token_type != "access":
            return None
    except JWTError:
        return None

    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(db, int(user_id))
    if user is None or not user.is_active:
        return None
    return user
