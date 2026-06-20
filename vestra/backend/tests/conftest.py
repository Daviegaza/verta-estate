"""
Pytest fixtures for Vestra integration tests.
Uses a test PostgreSQL database and real Redis for async integration testing.
"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Disable rate limiting during tests ────────────────────────────────────────
# Tests share the same client IP (127.0.0.1) and would be rate-limited.
# Set env vars before config is loaded, then patch the live limiter instances.
os.environ.setdefault("RATE_LIMIT_AUTH_PER_MINUTE", "99999")
os.environ.setdefault("RATE_LIMIT_GENERAL_PER_MINUTE", "99999")
os.environ.setdefault("RATE_LIMIT_ADMIN_PER_MINUTE", "99999")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # Use DB 1 for tests

from app.core.config import settings
from app.core.database import Base
from app.main import app

# ── Patch rate limiters to be effectively unlimited during tests ──────────────
import app.core.middleware as _mw
_mw.auth_limiter.max_requests = 999_999
_mw.general_limiter.max_requests = 999_999
_mw.admin_limiter.max_requests = 999_999

# ── Test Database URL ────────────────────────────────────────────────────────────
# Use a separate test database. Set TEST_DATABASE_URL env var to override.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/vestra_test",
)

# Create test engine and session factory
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test module and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session with automatic rollback."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


_FIXTURE_COUNTER = 0

@pytest.fixture
def test_user_data():
    """Sample user registration data — each call generates fresh unique data."""
    global _FIXTURE_COUNTER
    import time as _time
    _FIXTURE_COUNTER += 1
    ts = f"{int(_time.time() * 1000)}{_FIXTURE_COUNTER}"
    return {
        "email": f"testuser-{ts}@example.com",
        "phone": f"+2547{ts[-8:]}",
        "full_name": "Test User",
        "password": "StrongP@ss1",
        "role": "buyer",
    }


@pytest.fixture
def test_agent_data():
    """Sample agent registration data — each call generates fresh unique data."""
    global _FIXTURE_COUNTER
    import time as _time
    _FIXTURE_COUNTER += 1
    ts = f"{int(_time.time() * 1000)}{_FIXTURE_COUNTER}"
    return {
        "email": f"agent-{ts}@example.com",
        "phone": f"+2548{ts[-8:]}",
        "full_name": "Agent User",
        "password": "StrongP@ss1",
        "role": "agent",
    }
