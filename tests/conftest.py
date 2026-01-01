"""
Shared pytest fixtures for all tests.

Provides database isolation and common test fixtures.
"""

import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typing import Generator
from uuid import UUID, uuid4
import pytest_asyncio
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
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
    from app.api.models import Project, Document, DocumentRelation, Role, RoleTask
    
    # Import Domain models (LLM execution logging)
    from app.domain.models import (
        LLMContent, LLMRun, LLMRunInputRef,
        LLMRunOutputRef, LLMRunError, LLMRunToolCall
    )
    
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
    from sqlalchemy.orm import sessionmaker
    
    AsyncSessionLocal = sessionmaker(
        async_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()