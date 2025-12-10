"""Test fixtures for API tests."""
import os
from pathlib import Path

# ============================================================================
# CRITICAL: Set environment variables BEFORE any other imports
# ============================================================================

# Point to actual canon file
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up from tests/test_orchestrator_api/
CANON_PATH = PROJECT_ROOT / "workforce" / "canon" / "pipeline_flow.md"

# Set all test environment variables at module import time
os.environ["API_KEYS"] = "test-key,test-key-2"
os.environ["ALLOW_RESET_IN_CRITICAL_PHASES"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["COMBINE_CANON_PATH"] = str(CANON_PATH)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.orchestrator_api.main import app
from database import init_database, Base, engine, close_database
from workforce.orchestrator import Orchestrator
from workforce.canon_version_manager import CanonVersionManager
from app.orchestrator_api.dependencies import set_orchestrator, set_startup_time
from datetime import datetime, timezone



# Set API keys for tests BEFORE any imports
os.environ["API_KEYS"] = "test-key,test-key-2"
os.environ["ALLOW_RESET_IN_CRITICAL_PHASES"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Ensure API keys are set
    os.environ["API_KEYS"] = "test-key,test-key-2"
    os.environ["ALLOW_RESET_IN_CRITICAL_PHASES"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    yield
    
    # Cleanup
    if "API_KEYS" in os.environ:
        del os.environ["API_KEYS"]


@pytest.fixture(scope="function")
def setup_orchestrator():
    """Initialize orchestrator for tests that need it (not autouse for PIPELINE-175A tests)."""
    # Initialize database
    init_database()
    
    # Initialize orchestrator
    canon_manager = CanonVersionManager()
    orchestrator = Orchestrator(canon_manager=canon_manager)
    orchestrator.initialize()
    
    # Set global orchestrator
    set_orchestrator(orchestrator)
    set_startup_time(datetime.now(timezone.utc))
    
    yield
    
    # Cleanup
    close_database()


@pytest.fixture
def test_db():
    """Create test database for PIPELINE-175A tests."""
    # Create all tables fresh
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Drop all tables for clean slate
    Base.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Provide authentication headers for tests."""
    return {"X-API-Key": "test-key"}


class PipelineStub:
    """Stub object that mimics Pipeline model but isn't attached to a session."""
    def __init__(self, pipeline_id, epic_id, current_phase, state):
        self.pipeline_id = pipeline_id
        self.epic_id = epic_id
        self.current_phase = current_phase
        self.state = state


class RolePromptStub:
    """Stub object for RolePrompt."""
    def __init__(self, prompt_id, role_name, version):
        self.id = prompt_id
        self.role_name = role_name
        self.version = version


@pytest.fixture
def sample_pipeline(test_db):
    """Create sample pipeline for testing using direct SQL to ensure visibility."""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Use direct SQL with text() construct
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO pipelines (pipeline_id, epic_id, state, current_phase, canon_version, created_at, updated_at)
                    VALUES (:pid, :eid, :state, :phase, :canon, :created, :updated)"""),
            {
                "pid": "pip_test_123",
                "eid": "TEST-001",
                "state": "active",
                "phase": "pm_phase",
                "canon": "1.0",
                "created": now,
                "updated": now
            }
        )
    
    # Return stub
    return PipelineStub("pip_test_123", "TEST-001", "pm_phase", "active")


@pytest.fixture  
def sample_pipeline_2(test_db):
    """Create second sample pipeline for testing."""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Use direct SQL with text() construct
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO pipelines (pipeline_id, epic_id, state, current_phase, canon_version, created_at, updated_at)
                    VALUES (:pid, :eid, :state, :phase, :canon, :created, :updated)"""),
            {
                "pid": "pip_test_456",
                "eid": "TEST-002",
                "state": "active",
                "phase": "arch_phase",
                "canon": "1.0",
                "created": now,
                "updated": now
            }
        )
    
    return PipelineStub("pip_test_456", "TEST-002", "arch_phase", "active")


@pytest.fixture
def sample_role_prompt(test_db):
    """Create sample role prompt for testing."""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Use direct SQL with text() construct
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO role_prompts (id, role_name, version, bootstrapper, instructions, is_active, created_at, updated_at)
                    VALUES (:id, :role, :ver, :boot, :inst, :active, :created, :updated)"""),
            {
                "id": "rp_test_123",
                "role": "test_role",
                "ver": "1.0",
                "boot": "Test bootstrapper",
                "inst": "Test instructions",
                "active": 1,
                "created": now,
                "updated": now
            }
        )
    
    return RolePromptStub("rp_test_123", "test_role", "1.0")


@pytest.fixture
def db_session(test_db):
    """Database session fixture for PIPELINE-175A tests."""
    from sqlalchemy.orm import Session
    session = Session(bind=engine)
    yield session
    session.close()