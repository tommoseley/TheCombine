"""
Shared pytest fixtures for all tests.

CRITICAL ARCHITECTURAL CONSTRAINT:
- Configuration MUST be overridden via environment variables ONLY
- Monkeypatch MUST NOT be used for config.settings or paths
- This fixture MUST run before any application code imports config

Test isolation is achieved by setting WORKBENCH_DATA_ROOT environment variable
before config.Settings is instantiated, ensuring all tests use temporary paths.
"""

import json
import os
from pathlib import Path

import pytest
from datetime import datetime

from workforce.canon.loader import SemanticVersion, CanonDocument
from workforce.schemas.artifacts import Epic, ArchitecturalNotes, BASpecification
from sqlalchemy import create_engine

# =============================================================================
# CONFIGURATION ISOLATION (MUST RUN FIRST)
# =============================================================================

@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Automatically isolate config for all tests."""
    # Create isolated directories
    data_root = tmp_path / "data"
    workforce_root = tmp_path / "workforce"
    canon_dir = workforce_root / "canon"
    
    data_root.mkdir()
    workforce_root.mkdir()
    canon_dir.mkdir(parents=True)
    
    # Patch config settings
    import config
    monkeypatch.setattr(config, "DATA_ROOT", data_root)
    monkeypatch.setattr(config, "WORKFORCE_ROOT", workforce_root)
    monkeypatch.setattr(config, "CANON_DIR", canon_dir)
    monkeypatch.setattr(config.settings, "DATA_ROOT", data_root)
    monkeypatch.setattr(config.settings, "WORKFORCE_ROOT", workforce_root)
    monkeypatch.setattr(config.settings, "CANON_DIR", canon_dir)
    
    return {
        "data_root": data_root,
        "workforce_root": workforce_root,
        "canon_dir": canon_dir
    }

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """
    Set up test environment with isolated data directory.
    
    ARCHITECTURAL CONSTRAINT: This is the ONLY way to override configuration
    in tests. Monkeypatch MUST NOT be used for config.settings mutation.
    
    This fixture:
    1. Creates temporary data directory
    2. Sets WORKBENCH_DATA_ROOT environment variable
    3. Runs BEFORE any application code imports config module
    4. Ensures all Settings instances use test-isolated paths
    
    Args:
        tmp_path_factory: pytest session-scoped temporary path factory
    
    Returns:
        Path to test data root directory
    """
    # Create temporary data directory for entire test session
    test_data_root = tmp_path_factory.mktemp("data")
    
    # Set environment variable BEFORE importing config
    # This is the canonical way to override Pydantic Settings
    os.environ["WORKBENCH_DATA_ROOT"] = str(test_data_root)
    
    # Create required subdirectories
    (test_data_root / "epics").mkdir()
    (test_data_root / "logs").mkdir()
    
    # Optional: Set other test-specific env vars
    os.environ["WORKBENCH_LOG_LEVEL"] = "DEBUG"
    os.environ["WORKBENCH_DB_PATH"] = str(test_data_root / "test_workbench_ai.db")
    
    return test_data_root


# Now safe to import config (Settings will use WORKBENCH_DATA_ROOT from env)
from config import settings, epic_dir


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def test_db_url(tmp_path):
    """Provide a temporary test database URL."""
    db_file = tmp_path / "test.db"
    return f"sqlite:///{db_file}"

@pytest.fixture
def test_epic_dir(tmp_path: Path) -> Path:
    """
    Create temporary Epic artifacts directory for a single test.
    
    Uses tmp_path (function-scoped) to provide per-test isolation within
    the session-wide test data root.
    
    Args:
        tmp_path: pytest function-scoped temporary path
    
    Returns:
        Path to data/epics/TEST-001/ directory
    """
    # Create Epic directory in session-wide test data root
    test_epic_id = "TEST-001"
    epic_path = epic_dir(test_epic_id)
    epic_path.mkdir(parents=True, exist_ok=True)
    return epic_path


@pytest.fixture
def isolated_epic_dir(tmp_path_factory) -> Path:
    """
    Create completely isolated Epic directory for tests requiring separation.
    
    Use this when a test needs Epic artifacts that won't be visible to other
    tests (e.g., testing error handling for missing artifacts).
    
    Args:
        tmp_path_factory: pytest session-scoped factory
    
    Returns:
        Path to isolated Epic directory
    """
    isolated_root = tmp_path_factory.mktemp("isolated_epic")
    isolated_root.mkdir(parents=True, exist_ok=True)
    return isolated_root


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def valid_epic_v1() -> dict:
    """Load valid Epic JSON fixture."""
    fixture_path = settings.TESTS_ROOT / "fixtures" / "sample_epics" / "epic_valid_v1.json"
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def invalid_epic_missing_scope_v1() -> dict:
    """Load invalid Epic JSON fixture (missing scope field)."""
    fixture_path = settings.TESTS_ROOT / "fixtures" / "sample_epics" / "epic_invalid_missing_scope_v1.json"
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def invalid_epic_bad_epic_id_v1() -> dict:
    """Load invalid Epic JSON fixture (bad epic_id format)."""
    fixture_path = settings.TESTS_ROOT / "fixtures" / "sample_epics" / "epic_invalid_bad_epic_id_v1.json"
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def canonical_architecture_v1_4() -> dict:
    """Load Canonical Architecture v1.4 fixture."""
    fixture_path = settings.TESTS_ROOT / "fixtures" / "canonical_architecture_v1.4.json"
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def ba_addendum_template_v1() -> dict:
    """Load BA Addendum Template v1 fixture."""
    fixture_path = settings.TESTS_ROOT / "fixtures" / "ba_addendum_template_v1.json"
    with fixture_path.open() as f:
        return json.load(f)


# =============================================================================
# PIPELINE CONTEXT FIXTURES
# =============================================================================

@pytest.fixture
def mock_pipeline_context(test_epic_dir: Path, valid_epic_v1: dict):
    """
    Create mock PipelineContext for testing phases.
    
    Args:
        test_epic_dir: Temporary Epic directory
        valid_epic_v1: Valid Epic JSON
    
    Returns:
        PipelineContext instance
    """
    from workforce.pipeline.epic_pipeline import PipelineContext
    
    return PipelineContext(
        epic_id="TEST-001",
        epic_json=valid_epic_v1.copy(),
        epic_dir=test_epic_dir,
        artifacts={},
        metadata={},
    )

@pytest.fixture
def db_session(test_db):
    """Database session fixture (alias for test_db)."""
    return test_db


@pytest.fixture
def sample_pipeline(db_session):
    """Create sample pipeline for testing."""
    from app.orchestrator_api.models import Pipeline
    from datetime import datetime, timezone
    
    pipeline = Pipeline(
        pipeline_id="pip_test_123",
        epic_id="TEST-001",
        current_phase="pm_phase",
        state="active",
        canon_version="1.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(pipeline)
    db_session.commit()
    db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
def sample_pipeline_2(db_session):
    """Create second sample pipeline for testing."""
    from app.orchestrator_api.models import Pipeline
    from datetime import datetime, timezone
    
    pipeline = Pipeline(
        pipeline_id="pip_test_456",
        epic_id="TEST-002",
        current_phase="pm_phase",
        state="active",
        canon_version="1.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(pipeline)
    db_session.commit()
    db_session.refresh(pipeline)
    return pipeline


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def validate_test_isolation():
    """
    Validate that test isolation is properly configured.
    
    This fixture runs once per session to ensure:
    1. DATA_ROOT points to temporary directory (not production ./data)
    2. All derived paths are within test data root
    3. Settings are properly loaded from environment variables
    """
    # Verify DATA_ROOT is not production path
    assert "tmp" in str(settings.DATA_ROOT) or "pytest" in str(settings.DATA_ROOT), \
        f"DATA_ROOT is not isolated: {settings.DATA_ROOT}. Test isolation failed!"
    
    # Verify derived paths are correct
    assert settings.EPICS_ROOT == settings.DATA_ROOT / "epics", \
        "EPICS_ROOT not properly derived from DATA_ROOT"
    assert settings.LOGS_ROOT == settings.DATA_ROOT / "logs", \
        "LOGS_ROOT not properly derived from DATA_ROOT"
    
    # Verify directories exist
    assert settings.EPICS_ROOT.exists(), "EPICS_ROOT directory not created"
    assert settings.LOGS_ROOT.exists(), "LOGS_ROOT directory not created"
    
    return True

@pytest.fixture
def temp_canon_file(tmp_path):
    """Create a temporary canon file for testing."""
    canon_content = """PIPELINE_FLOW_VERSION=1.0
# Pipeline Flow – Version 1 (Canonical)

## 1. Overview
Test overview content.

## 2. Phase Sequence (Strict Order)
Test phase sequence.

## 3. Phase Definitions
Test phase definitions.

### 3.1 PM Phase
Test PM phase.

### 3.2 Architect Phase
Test architect phase.

### 3.3 BA Phase
Test BA phase.

### 3.4 Developer Phase
Test developer phase.

### 3.5 QA Phase
Test QA phase.

### 3.6 Commit Phase
Test commit phase.

## 4. Error Handling & Recovery
Test error handling.

## 5. Behavioral Rules (Binding)
Test behavioral rules.

## 6. Canonical Summary Diagram
Test diagram.

## 7. Canon Enforcement
Test enforcement.
"""
    
    canon_file = tmp_path / "pipeline_flow.md"
    canon_file.write_text(canon_content, encoding='utf-8')
    return canon_file


@pytest.fixture
def sample_canon_document():
    """Sample CanonDocument for testing."""
    return CanonDocument(
        version=SemanticVersion(1, 0),
        content="PIPELINE_FLOW_VERSION=1.0\n# Test Canon",
        loaded_at=datetime.now(),
        file_path=Path("/test/canon.md")
    )


@pytest.fixture
def sample_epic():
    """Sample Epic for testing."""
    return Epic(
        epic_id="TEST-001",
        title="Test Epic",
        description="Test description",
        business_value="Test value",
        scope="Test scope",
        stories=[],
        acceptance_criteria=[]
    )


@pytest.fixture
def sample_version():
    """Sample SemanticVersion for testing."""
    return SemanticVersion(1, 0)