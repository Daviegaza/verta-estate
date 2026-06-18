"""
Phone OTP Authentication — simple, Kenya-friendly auth.
Flow: Enter phone → get OTP via WhatsApp → verify → done.
No email, no password required. Browse first, upgrade role later.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.schemas.user import UserResponse
from app.services.otp_service import send_otp, verify_otp, get_or_create_user_by_phone

router = APIRouter(prefix="/auth", tags=["Phone Auth"])


class PhoneRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, description="Phone in 254XXXXXXXXX format")

class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    code: str = Field(..., min_length=4, max_length=10)
    full_name: str | None = Field(None, max_length=255, description="Name for new users")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    is_new: bool = False


@router.post("/send-otp")
async def send_otp_endpoint(data: PhoneRequest):
    """Send OTP code to phone number via WhatsApp."""
    result = await send_otp(data.phone)
    if not result["success"]:
        raise HTTPException(status_code=429, detail=result["message"])
    return {"message": result["message"]}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(
    data: OTPVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP and log in (or create account)."""
    result = await verify_otp(data.phone, data.code)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Get or create user
    user, is_new = await get_or_create_user_by_phone(
        db, data.phone, data.full_name
    )

    # Create JWT token
    client_ip = request.client.host if request.client else None
    token = create_access_token({"sub": str(user.id)}, client_ip=client_ip)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user).model_dump(),
        is_new=is_new,
    )


@router.post("/upgrade-role")
async def upgrade_role(
    role: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upgrade account from basic buyer to seller/agent/landlord.
    Called when user wants to start listing properties.
    """
    from app.models.user import UserRole

    allowed = {"seller", "agent", "landlord"}
    if role not in allowed:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(allowed)}")

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    current_user.role = new_role
    await db.commit()
    await db.refresh(current_user)

    # If upgrading to agent, create agent profile
    if role == "agent":
        from app.models.property import AgentProfile
        from sqlalchemy import select
        result = await db.execute(
            select(AgentProfile).where(AgentProfile.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            profile = AgentProfile(
                user_id=current_user.id,
                subscription_tier="free",
            )
            db.add(profile)
            await db.commit()

    return {
        "message": f"Account upgraded to {role}",
        "role": role,
        "user": UserResponse.model_validate(current_user).model_dump(),
    }
