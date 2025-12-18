"""
Tests for document registry loader.

Tests the database-backed document type configuration system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.registry.loader import (
    get_document_config,
    list_document_types,
    list_by_category,
    list_by_scope,
    get_dependencies,
    can_build,
    get_buildable_documents,
    DocumentNotFoundError,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_project_discovery():
    """Mock project_discovery document type."""
    mock = MagicMock()
    mock.to_dict.return_value = {
        "id": "uuid-1",
        "doc_type_id": "project_discovery",
        "name": "Project Discovery",
        "description": "Early architectural discovery",
        "category": "architecture",
        "icon": "search",
        "builder_role": "architect",
        "builder_task": "preliminary",
        "handler_id": "project_discovery",
        "required_inputs": [],
        "optional_inputs": [],
        "scope": "project",
        "display_order": 10,
        "is_active": True,
    }
    return mock


@pytest.fixture
def mock_architecture_spec():
    """Mock architecture_spec document type."""
    mock = MagicMock()
    mock.to_dict.return_value = {
        "id": "uuid-2",
        "doc_type_id": "architecture_spec",
        "name": "Architecture Specification",
        "description": "Full architecture specification",
        "category": "architecture",
        "icon": "landmark",
        "builder_role": "architect",
        "builder_task": "final",
        "handler_id": "architecture_spec",
        "required_inputs": ["project_discovery"],
        "optional_inputs": [],
        "scope": "project",
        "display_order": 20,
        "is_active": True,
    }
    return mock


@pytest.fixture
def mock_epic_set():
    """Mock epic_set document type."""
    mock = MagicMock()
    mock.to_dict.return_value = {
        "id": "uuid-3",
        "doc_type_id": "epic_set",
        "name": "Epic Set",
        "description": "Project epics",
        "category": "planning",
        "icon": "layers",
        "builder_role": "pm",
        "builder_task": "epic_generation",
        "handler_id": "epic_set",
        "required_inputs": ["project_discovery"],
        "optional_inputs": ["architecture_spec"],
        "scope": "project",
        "display_order": 30,
        "is_active": True,
    }
    return mock


# =============================================================================
# TESTS: get_document_config
# =============================================================================

@pytest.mark.asyncio
async def test_get_document_config_found(mock_project_discovery):
    """Test getting a document config that exists."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_project_discovery
    db.execute.return_value = mock_result
    
    # Act
    config = await get_document_config(db, "project_discovery")
    
    # Assert
    assert config["doc_type_id"] == "project_discovery"
    assert config["name"] == "Project Discovery"
    assert config["category"] == "architecture"


@pytest.mark.asyncio
async def test_get_document_config_not_found():
    """Test getting a document config that doesn't exist."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await get_document_config(db, "nonexistent")
    
    assert exc_info.value.doc_type_id == "nonexistent"


# =============================================================================
# TESTS: list_document_types
# =============================================================================

@pytest.mark.asyncio
async def test_list_document_types(mock_project_discovery, mock_architecture_spec, mock_epic_set):
    """Test listing all document types."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_project_discovery, mock_architecture_spec, mock_epic_set]
    mock_result.scalars.return_value = mock_scalars
    db.execute.return_value = mock_result
    
    # Act
    doc_types = await list_document_types(db)
    
    # Assert
    assert len(doc_types) == 3
    assert doc_types[0]["doc_type_id"] == "project_discovery"
    assert doc_types[1]["doc_type_id"] == "architecture_spec"
    assert doc_types[2]["doc_type_id"] == "epic_set"


# =============================================================================
# TESTS: list_by_category
# =============================================================================

@pytest.mark.asyncio
async def test_list_by_category(mock_project_discovery, mock_architecture_spec):
    """Test listing document types by category."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_project_discovery, mock_architecture_spec]
    mock_result.scalars.return_value = mock_scalars
    db.execute.return_value = mock_result
    
    # Act
    doc_types = await list_by_category(db, "architecture")
    
    # Assert
    assert len(doc_types) == 2
    assert all(d["category"] == "architecture" for d in doc_types)


# =============================================================================
# TESTS: get_dependencies
# =============================================================================

@pytest.mark.asyncio
async def test_get_dependencies(mock_architecture_spec):
    """Test getting dependencies for a document type."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_architecture_spec
    db.execute.return_value = mock_result
    
    # Act
    deps = await get_dependencies(db, "architecture_spec")
    
    # Assert
    assert "required" in deps
    assert "optional" in deps
    assert "project_discovery" in deps["required"]


# =============================================================================
# TESTS: can_build
# =============================================================================

@pytest.mark.asyncio
async def test_can_build_with_deps_met(mock_architecture_spec):
    """Test can_build when dependencies are met."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_architecture_spec
    db.execute.return_value = mock_result
    
    existing = ["project_discovery"]
    
    # Act
    can, missing = await can_build(db, "architecture_spec", existing)
    
    # Assert
    assert can is True
    assert missing == []


@pytest.mark.asyncio
async def test_can_build_with_deps_missing(mock_architecture_spec):
    """Test can_build when dependencies are missing."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_architecture_spec
    db.execute.return_value = mock_result
    
    existing = []  # No documents exist yet
    
    # Act
    can, missing = await can_build(db, "architecture_spec", existing)
    
    # Assert
    assert can is False
    assert "project_discovery" in missing


@pytest.mark.asyncio
async def test_can_build_no_deps(mock_project_discovery):
    """Test can_build for document with no dependencies."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_project_discovery
    db.execute.return_value = mock_result
    
    existing = []  # No documents exist yet
    
    # Act
    can, missing = await can_build(db, "project_discovery", existing)
    
    # Assert
    assert can is True
    assert missing == []


# =============================================================================
# TESTS: Integration scenario
# =============================================================================

@pytest.mark.asyncio
async def test_document_dependency_chain():
    """
    Test the full dependency chain:
    - project_discovery has no deps (can build first)
    - architecture_spec needs project_discovery
    - epic_set needs project_discovery
    """
    # This would be an integration test with a real database
    # For now, just document the expected behavior
    
    # Phase 1: Nothing exists
    # - project_discovery: can build (no deps)
    # - architecture_spec: cannot build (missing project_discovery)
    # - epic_set: cannot build (missing project_discovery)
    
    # Phase 2: project_discovery exists
    # - architecture_spec: can build
    # - epic_set: can build
    
    # Phase 3: All exist
    # - Nothing new to build at project scope
    
    pass  # Placeholder for integration test