"""
Shared pytest fixtures for all tests.

Provides database isolation and common test fixtures.
"""

import pytest
from uuid import uuid4
from app.auth.models import User
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# =============================================================================
# ENABLE FOREIGN KEY CONSTRAINTS IN SQLITE
# =============================================================================

def enable_sqlite_foreign_keys(dbapi_conn, connection_record):
    """Enable foreign key constraints in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# =============================================================================
# DATABASE FIXTURES (SYNC - for legacy tests)
# =============================================================================

# =============================================================================
# ASYNC DATABASE FIXTURES (for ADR-010 tests)
# =============================================================================

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_test_engine():
    """
    Async database engine for testing async code.
    
    Creates all tables including ADR-010 logging tables.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Import Base
    from app.core.database import Base
    
    # Import API models (core business entities)
    
    # Import Domain models (LLM execution logging)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db_session(async_test_engine):
    """
    Async database session for testing async code.
    
    Use this for ADR-010 LLMExecutionLogger tests.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    
    AsyncSessionLocal = sessionmaker(
        async_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()

# =============================================================================
# MOCK ADMIN USER FOR UI TESTS
# =============================================================================

@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user for testing."""
    return User(
        user_id=str(uuid4()),
        email="admin@test.com",
        name="Test Admin",
        is_active=True,
        email_verified=True,
        is_admin=True,
    )


def override_require_admin(mock_admin_user: User):
    """Create a dependency override for require_admin."""
    async def mock_require_admin():
        return mock_admin_user
    return mock_require_admin
