import asyncio
from typing import AsyncGenerator

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Use test database
TEST_DATABASE_URL = settings.DATABASE_URL + "_test" if not settings.DATABASE_URL.endswith("_test") else settings.DATABASE_URL


def ensure_test_database() -> None:
    """Create the PostgreSQL test database if it does not already exist."""
    db_url = make_url(settings.DATABASE_URL)
    test_db_name = db_url.database + "_test" if not db_url.database.endswith("_test") else db_url.database

    conn = psycopg2.connect(
        dbname="postgres",
        user=db_url.username,
        password=db_url.password,
        host=db_url.host,
        port=db_url.port,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_db_name,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f'CREATE DATABASE "{test_db_name}"')
    conn.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_db():
    ensure_test_database()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with a fresh schema for the test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client():
    """Create a test client with a fresh session per request."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async def create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

        async def drop_schema() -> None:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

        asyncio.run(drop_schema())


@pytest.fixture
def organization_headers():
    """Standard organization headers."""
    return {
        "X-Organization": "ABC Construction",
    }


@pytest.fixture
def abc_headers():
    """ABC Construction headers."""
    return {
        "X-Organization": "ABC Construction",
    }


@pytest.fixture
def xyz_headers():
    """XYZ Builders headers."""
    return {
        "X-Organization": "XYZ Builders",
    }


@pytest.fixture
def owner_headers(abc_headers):
    """Owner headers - in evaluation, owner is the organization."""
    headers = abc_headers.copy()
    headers["Authorization"] = "Bearer owner-token"
    return headers


@pytest.fixture
def skill_payload():
    """Valid skill creation payload."""
    return {
        "name": "Test Skill",
        "description": "This is a test skill",
        "owner_id": "test-owner",
        "requested_tools": ["analyze_data", "generate_report"],
    }


@pytest.fixture
def version_payload():
    """Valid version creation payload."""
    return {
        "name": "Test Skill v2",
        "description": "Updated version",
        "configuration": {"timeout": 30, "retry_count": 3},
        "requested_tools": ["analyze_data", "generate_report", "send_email"],
        "created_by": "test-owner",
    }


@pytest.fixture
def activation_payload():
    """Activation payload."""
    return {
        "activated_by": "test-owner",
    }
