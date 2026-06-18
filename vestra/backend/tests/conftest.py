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

from app.core.config import settings
from app.core.database import Base
from app.main import app

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


@pytest.fixture
def test_user_data():
    """Sample user registration data."""
    return {
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "StrongP@ss1",
        "role": "buyer",
    }


@pytest.fixture
def test_agent_data():
    """Sample agent registration data."""
    return {
        "email": "agent@example.com",
        "full_name": "Agent User",
        "password": "StrongP@ss1",
        "role": "agent",
    }
