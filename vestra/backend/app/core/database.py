from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Use structured logging instead
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_timeout=30,
    connect_args={
        "server_settings": {
            "application_name": "vestra_api",
            "timezone": "Africa/Nairobi",
        }
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Expunge all objects before close so FastAPI can serialize
            # them after the session ends (prevents MissingGreenlet errors)
            session.expunge_all()
            await session.close()


async def create_tables():
    """Auto-create tables only in development.

    In production and staging, schema is managed via Alembic migrations.
    Run `alembic upgrade head` before starting the app in production.
    """
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            from app.models import (  # noqa: F401
                audit_log,
                document,
                payment,
                property,
                referral,
                rental,
                subscription,
                title_chain,
                user,
            )
            await conn.run_sync(Base.metadata.create_all)
    else:
        logger = __import__("logging").getLogger("vestra")
        logger.info(
            '{"event":"create_tables","skipped":true,"reason":"migrations manage schema in %s"}',
            settings.ENVIRONMENT,
        )
