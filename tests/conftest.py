"""
Shared pytest fixtures for all tests.

Provides database isolation and common test fixtures.
"""

import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """
    Create a test database engine using SQLite in-memory.
    
    Uses StaticPool to allow the same connection across threads,
    which is necessary for in-memory SQLite.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Import Base and create all tables
    from app.api.models.artifact import Base
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test.
    
    Rolls back all changes after each test for isolation.
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def test_db(db_session):
    """Alias for db_session - for backward compatibility."""
    return db_session


# =============================================================================
# CONFIGURATION FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """
    Automatically isolate config for all tests.
    
    Sets up temporary directories and patches config settings.
    """
    # Create isolated directories
    data_root = tmp_path / "data"
    data_root.mkdir()
    
    # Set environment variables for config isolation
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    
    return {"data_root": data_root}


# =============================================================================
# MODEL FIXTURES
# =============================================================================

@pytest.fixture
def sample_project(db_session):
    """Create a sample project for testing."""
    from app.api.models import Project
    
    project = Project(
        id="test-uuid-1234",
        project_id="TEST",
        name="Test Project",
        description="A test project",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_artifact(db_session, sample_project):
    """Create a sample artifact for testing."""
    from app.api.models import Artifact
    
    artifact = Artifact(
        artifact_path=f"{sample_project.project_id}/E001",
        artifact_type="epic",
        project_id=sample_project.project_id,
        title="Test Epic",
        content={"description": "Test epic description"},
        status="draft",
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)
    return artifact


@pytest.fixture
def sample_role_prompt(db_session):
    """Create a sample role prompt for testing."""
    from app.api.models import RolePrompt
    
    prompt = RolePrompt(
        id="pm-v1",
        role_name="pm",
        version="1",
        instructions="You are a PM mentor...",
        expected_schema={"type": "object"},
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(prompt)
    db_session.commit()
    db_session.refresh(prompt)
    return prompt


# =============================================================================
# ASYNC DATABASE FIXTURES (if using async)
# =============================================================================

@pytest.fixture
async def async_db_session():
    """
    Async database session for testing async code.
    
    Only use this if your tests require async database operations.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create tables
    from app.api.models.artifact import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


# =============================================================================
# MOCK/STUB FIXTURES
# =============================================================================

@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response for testing without API calls."""
    return {
        "content": [
            {
                "type": "text",
                "text": '{"epic_id": "TEST-001", "title": "Test Epic", "description": "Generated test epic"}'
            }
        ],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        },
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn"
    }


@pytest.fixture
def mock_llm_caller(monkeypatch, mock_anthropic_response):
    """
    Mock LLM caller to avoid actual API calls in tests.
    
    Use this fixture when testing code that calls the Anthropic API.
    """
    class MockLLMCaller:
        def call(self, *args, **kwargs):
            return mock_anthropic_response
        
        async def call_async(self, *args, **kwargs):
            return mock_anthropic_response
    
    return MockLLMCaller()