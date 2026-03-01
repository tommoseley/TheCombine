"""
Tests for Schema Registry Service (ADR-031).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.schema_registry_service import (
    SchemaRegistryService,
    SchemaNotFoundError,
    InvalidStatusTransitionError,
)


@pytest.fixture
def mock_db():
    """Create mock async session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def registry(mock_db):
    return SchemaRegistryService(mock_db)


# =============================================================================
# Test: Hash Computation
# =============================================================================

def test_compute_hash_deterministic():
    """Same JSON produces same hash."""
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    
    hash1 = SchemaRegistryService.compute_hash(schema)
    hash2 = SchemaRegistryService.compute_hash(schema)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_compute_hash_key_order_independent():
    """Hash is independent of key order."""
    schema1 = {"type": "object", "a": 1, "b": 2}
    schema2 = {"b": 2, "a": 1, "type": "object"}
    
    assert SchemaRegistryService.compute_hash(schema1) == SchemaRegistryService.compute_hash(schema2)


def test_compute_hash_different_content():
    """Different content produces different hash."""
    schema1 = {"type": "object"}
    schema2 = {"type": "array"}
    
    assert SchemaRegistryService.compute_hash(schema1) != SchemaRegistryService.compute_hash(schema2)


# =============================================================================
# Test: Create
# =============================================================================

@pytest.mark.asyncio
async def test_create_schema_artifact(registry, mock_db):
    """Create stores artifact with computed hash."""
    schema_json = {"type": "object", "required": ["id"]}
    
    # Mock refresh to set values
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    await registry.create(
        schema_id="TestSchemaV1",
        kind="type",
        schema_json=schema_json,
        version="1.0",
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    added = mock_db.add.call_args[0][0]
    assert added.schema_id == "TestSchemaV1"
    assert added.kind == "type"
    assert added.version == "1.0"
    assert added.status == "draft"
    assert len(added.sha256) == 64


@pytest.mark.asyncio
async def test_create_with_governance_refs(registry, mock_db):
    """Create stores governance references."""
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    await registry.create(
        schema_id="TestSchemaV1",
        kind="type",
        schema_json={"type": "object"},
        governance_refs={"adrs": ["ADR-031"]},
    )
    
    added = mock_db.add.call_args[0][0]
    assert added.governance_refs == {"adrs": ["ADR-031"]}


# =============================================================================
# Test: Get By ID
# =============================================================================

@pytest.mark.asyncio
async def test_get_by_id_with_version(registry, mock_db):
    """Get by ID with specific version."""
    mock_artifact = MagicMock()
    mock_artifact.schema_id = "TestV1"
    mock_artifact.version = "1.0"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_by_id("TestV1", "1.0")
    
    assert result == mock_artifact


@pytest.mark.asyncio
async def test_get_by_id_latest_accepted(registry, mock_db):
    """Get by ID without version returns latest accepted."""
    mock_artifact = MagicMock()
    mock_artifact.status = "accepted"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_by_id("TestV1")  # No version
    
    assert result == mock_artifact


@pytest.mark.asyncio
async def test_get_by_id_not_found(registry, mock_db):
    """Get returns None if not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_by_id("NonExistent", "1.0")
    
    assert result is None


# =============================================================================
# Test: Status Transitions
# =============================================================================

@pytest.mark.asyncio
async def test_set_status_draft_to_accepted(registry, mock_db):
    """Valid transition: draft -> accepted."""
    mock_artifact = MagicMock()
    mock_artifact.status = "draft"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    await registry.set_status("TestV1", "1.0", "accepted")
    
    assert mock_artifact.status == "accepted"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_set_status_accepted_to_deprecated(registry, mock_db):
    """Valid transition: accepted -> deprecated."""
    mock_artifact = MagicMock()
    mock_artifact.status = "accepted"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    await registry.set_status("TestV1", "1.0", "deprecated")
    
    assert mock_artifact.status == "deprecated"


@pytest.mark.asyncio
async def test_set_status_invalid_transition(registry, mock_db):
    """Invalid transition raises error."""
    mock_artifact = MagicMock()
    mock_artifact.status = "deprecated"  # Terminal state
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    with pytest.raises(InvalidStatusTransitionError):
        await registry.set_status("TestV1", "1.0", "accepted")


@pytest.mark.asyncio
async def test_set_status_not_found(registry, mock_db):
    """Set status on missing schema raises error."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    with pytest.raises(SchemaNotFoundError):
        await registry.set_status("NonExistent", "1.0", "accepted")


# =============================================================================
# Test: List By Kind
# =============================================================================

@pytest.mark.asyncio
async def test_list_by_kind(registry, mock_db):
    """List filters by kind."""
    mock_artifacts = [MagicMock(), MagicMock()]
    
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_artifacts
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    result = await registry.list_by_kind("type")
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_by_kind_with_status(registry, mock_db):
    """List filters by kind and status."""
    mock_artifacts = [MagicMock()]
    
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_artifacts
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    result = await registry.list_by_kind("type", status="accepted")
    
    assert len(result) == 1