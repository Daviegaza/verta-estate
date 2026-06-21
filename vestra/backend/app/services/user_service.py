import contextlib
import logging
from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import get_password_hash, verify_password
from app.models.property import AgentProfile
from app.models.user import User, UserRole
from app.schemas.user import AgentProfileCreate, UserCreate, UserUpdate

logger = logging.getLogger("vestra")


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    user_data: UserCreate,
    referral_code: str | None = None,
) -> User:
    hashed_password = await get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # ── Generate user's own referral code ──────────────────────────────────────
    from app.services.referral_engine import generate_referral_code

    await generate_referral_code(db, user.id)

    # ── Referral flow (if user was referred by someone) ─────────────────────────
    if referral_code:
        from app.services.referral_engine import award_referral_reward, track_referral_signup

        track_result = await track_referral_signup(db, user.id, referral_code)
        if track_result:
            logger.info(
                '{"event":"referral_flow_triggered","user_id":%d,"referrer_id":%d,"action":"signup_verified"}',
                user.id, track_result["referrer_id"],
            )
            # Award signup reward to referrer
            await award_referral_reward(db, user.id, "signup_verified")
        else:
            logger.warning(
                '{"event":"referral_code_invalid","user_id":%d,"code":"%s"}',
                user.id, referral_code,
            )

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user or not await verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(db: AsyncSession, user: User, update_data: UserUpdate) -> User:
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_agent_profile(
    db: AsyncSession, user_id: int, data: AgentProfileCreate | None = None
) -> AgentProfile:
    result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = AgentProfile(
            user_id=user_id,
            agency_name=data.agency_name if data else None,
            license_number=data.license_number if data else None,
            years_experience=data.years_experience if data else 0,
            specialization=data.specialization if data else [],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def count_agents(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.agent)
    )
    return result.scalar_one()


async def get_all_users(
    db: AsyncSession, skip: int = 0, limit: int = 50,
    role: str | None = None, search: str | None = None,
):
    query = select(User).order_by(User.created_at.desc())
    if role:
        with contextlib.suppress(ValueError):
            query = query.where(User.role == UserRole(role))
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def count_users(db: AsyncSession, role: str | None = None) -> int:
    query = select(func.count(User.id))
    if role:
        with contextlib.suppress(ValueError):
            query = query.where(User.role == UserRole(role))
    result = await db.execute(query)
    return result.scalar_one()


async def update_user_role(db: AsyncSession, user: User, new_role: UserRole) -> User:
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user


async def toggle_user_active(db: AsyncSession, user: User) -> User:
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_role_distribution(db: AsyncSession) -> list:
    result = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    rows = result.all()
    color_map = {
        UserRole.buyer: "#10b981",
        UserRole.seller: "#3b82f6",
        UserRole.agent: "#8b5cf6",
        UserRole.landlord: "#f59e0b",
        UserRole.admin: "#ef4444",
        UserRole.super_admin: "#6b7280",
    }
    return [
        {"name": role.value.replace("_", " ").title(), "value": count, "color": color_map.get(role, "#6b7280")}
        for role, count in rows
    ]


async def get_monthly_user_growth(db: AsyncSession) -> list:
    """Return monthly user signups for the last 6 months."""
    from datetime import datetime

    months = []
    now = datetime.now(UTC)
    result = await db.execute(
        select(
            func.date_trunc('month', User.created_at).label('month'),
            func.count(User.id).label('count')
        ).where(
            User.created_at >= func.date_trunc('month', func.now()) - func.make_interval(0, 6)
        ).group_by('month').order_by('month')
    )
    data = {row.month.strftime('%b'): row.count for row in result.all()}
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Fill in last 6 months
    for i in range(5, -1, -1):
        m_idx = (now.month - 1 - i) % 12
        label = month_names[m_idx]
        months.append({"month": label, "users": data.get(label, 0) if label in data else 0})
    return months
