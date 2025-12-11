"""
Test fixtures for The Combine API tests.

Updated for PIPELINE-175A/B: PostgreSQL, Artifacts, RolePrompts, no Canon.
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.api.main import app
from database import Base

# ============================================================================
# Test Environment Configuration
# ============================================================================

# Use test database (separate from dev database)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://combine_user:Gamecocks1!@localhost:5432/combine_test"
)

# Test API keys
os.environ["API_KEYS"] = "test-key,test-key-2"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ============================================================================
# Session-level Fixtures (Setup/Teardown)
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Create all tables in test database at start of test session.
    
    This runs once for the entire test suite.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    # Optional: Drop all tables after tests
    # Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["API_KEYS"] = "test-key,test-key-2"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    
    yield
    
    # Cleanup
    if "API_KEYS" in os.environ:
        del os.environ["API_KEYS"]


# ============================================================================
# Function-level Fixtures (Per Test)
# ============================================================================

@pytest.fixture(scope="function")
def db_session():
    """
    Provide a clean database session for each test.
    
    Automatically rolls back changes after test completes.
    """
    session = TestSessionLocal()
    
    yield session
    
    # Rollback any changes made during test
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def clean_db(db_session):
    """
    Clean test data from database before each test.
    
    Use this when you need a completely clean slate.
    """
    # Clean all test data
    tables_to_clean = [
        'workflows',
        'artifact_versions', 
        'artifacts',
        'projects',
        'breadcrumb_files',
        'files'
    ]
    
    for table in tables_to_clean:
        db_session.execute(text(f"DELETE FROM {table} WHERE project_id LIKE 'TEST%'"))
    
    db_session.commit()
    
    yield db_session


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def client():
    """
    Provide async HTTP client for API testing.
    
    Use this to test FastAPI endpoints.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """
    Provide authentication headers for API requests.
    
    Use this with client: client.get("/endpoint", headers=auth_headers)
    """
    return {"X-API-Key": "test-key"}


# ============================================================================
# Sample Data Fixtures (New Architecture)
# ============================================================================

@pytest.fixture
def sample_role_prompt(db_session):
    """
    Create a sample RolePrompt for testing.
    
    Uses actual RolePrompt schema (instructions, expected_schema).
    """
    from app.combine.models import RolePrompt
    from datetime import datetime, timezone
    
    prompt = RolePrompt(
        id="test-pm-v1",
        role_name="test_pm",
        version="1.0",
        instructions="You are a test PM. Create an epic from the user request.",
        expected_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db_session.add(prompt)
    db_session.commit()
    db_session.refresh(prompt)
    
    yield prompt
    
    # Cleanup
    db_session.delete(prompt)
    db_session.commit()


@pytest.fixture
def sample_artifact(db_session):
    """
    Create a sample Artifact for testing.
    
    Uses RSP-1 path structure (TEST/E001).
    """
    from app.combine.models import Artifact
    from datetime import datetime, timezone
    import uuid
    
    artifact = Artifact(
        id=uuid.uuid4(),
        artifact_path="TEST/E001",
        artifact_type="epic",
        project_id="TEST",
        epic_id="E001",
        title="Test Epic",
        content={
            "description": "Test epic content",
            "stories": []
        },
        breadcrumbs={},
        status="active",
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)
    
    yield artifact
    
    # Cleanup
    db_session.delete(artifact)
    db_session.commit()


@pytest.fixture
def sample_project(db_session):
    """
    Create a sample Project for testing.
    """
    from app.combine.models import Project
    from datetime import datetime, timezone
    
    project = Project(
        project_id="TEST",
        name="Test Project",
        description="Project for testing",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    
    yield project
    
    # Cleanup
    db_session.delete(project)
    db_session.commit()


@pytest.fixture
def sample_workflow(db_session):
    """
    Create a sample Workflow for testing.
    """
    from app.combine.models import Workflow
    from datetime import datetime, timezone
    
    workflow = Workflow(
        workflow_id="test-wf-001",
        artifact_path="TEST/E001",
        workflow_type="pm_analysis",
        status="running",
        started_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    
    yield workflow
    
    # Cleanup
    db_session.delete(workflow)
    db_session.commit()


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_artifact(db_session, artifact_path, artifact_type, title, content=None):
    """
    Helper function to quickly create test artifacts.
    
    Example:
        artifact = create_test_artifact(
            db_session, 
            "TEST/E002", 
            "epic", 
            "Another Test"
        )
    """
    from app.combine.models import Artifact
    from datetime import datetime, timezone
    import uuid
    
    path_parts = artifact_path.split('/')
    
    artifact = Artifact(
        id=uuid.uuid4(),
        artifact_path=artifact_path,
        artifact_type=artifact_type,
        project_id=path_parts[0],
        epic_id=path_parts[1] if len(path_parts) > 1 else None,
        feature_id=path_parts[2] if len(path_parts) > 2 else None,
        story_id=path_parts[3] if len(path_parts) > 3 else None,
        title=title,
        content=content or {},
        breadcrumbs={},
        status="active",
        version=1,
        parent_path='/'.join(path_parts[:-1]) if len(path_parts) > 1 else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)
    
    return artifact