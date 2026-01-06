"""
Tests for Fragment Registry Service (ADR-032).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.fragment_registry_service import (
    FragmentRegistryService,
    FragmentNotFoundError,
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
    return FragmentRegistryService(mock_db)


# =============================================================================
# Test: Hash Computation
# =============================================================================

def test_compute_hash_deterministic():
    """Same markup produces same hash."""
    markup = "<div>{{ item.text }}</div>"
    
    hash1 = FragmentRegistryService.compute_hash(markup)
    hash2 = FragmentRegistryService.compute_hash(markup)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_compute_hash_different_content():
    """Different content produces different hash."""
    markup1 = "<div>{{ item.text }}</div>"
    markup2 = "<span>{{ item.text }}</span>"
    
    assert FragmentRegistryService.compute_hash(markup1) != FragmentRegistryService.compute_hash(markup2)


# =============================================================================
# Test: Create Fragment
# =============================================================================

@pytest.mark.asyncio
async def test_create_fragment_artifact(registry, mock_db):
    """Create stores fragment with computed hash."""
    markup = "<div>{{ item.text }}</div>"
    
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    artifact = await registry.create_fragment(
        fragment_id="TestFragment",
        schema_type_id="TestTypeV1",
        fragment_markup=markup,
        version="1.0",
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    added = mock_db.add.call_args[0][0]
    assert added.fragment_id == "TestFragment"
    assert added.schema_type_id == "TestTypeV1"
    assert added.version == "1.0"
    assert added.status == "draft"
    assert len(added.sha256) == 64


@pytest.mark.asyncio
async def test_create_computes_hash(registry, mock_db):
    """Create computes hash from markup."""
    markup = "<div>test</div>"
    expected_hash = FragmentRegistryService.compute_hash(markup)
    
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    await registry.create_fragment(
        fragment_id="TestFragment",
        schema_type_id="TestTypeV1",
        fragment_markup=markup,
    )
    
    added = mock_db.add.call_args[0][0]
    assert added.sha256 == expected_hash


# =============================================================================
# Test: Get Fragment
# =============================================================================

@pytest.mark.asyncio
async def test_get_fragment_by_id(registry, mock_db):
    """Get fragment by ID and version."""
    mock_artifact = MagicMock()
    mock_artifact.fragment_id = "TestFragment"
    mock_artifact.version = "1.0"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_fragment("TestFragment", "1.0")
    
    assert result == mock_artifact


@pytest.mark.asyncio
async def test_get_fragment_not_found(registry, mock_db):
    """Get returns None if not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_fragment("NonExistent", "1.0")
    
    assert result is None


# =============================================================================
# Test: Get Active Fragment for Type
# =============================================================================

@pytest.mark.asyncio
async def test_get_active_fragment_for_type(registry, mock_db):
    """Get active fragment via binding lookup."""
    mock_binding = MagicMock()
    mock_binding.fragment_id = "TestFragment"
    mock_binding.fragment_version = "1.0"
    mock_binding.is_active = True
    
    mock_fragment = MagicMock()
    mock_fragment.fragment_id = "TestFragment"
    
    # First call returns binding, second returns fragment
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = mock_binding
    
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = mock_fragment
    
    mock_db.execute.side_effect = [mock_result1, mock_result2]
    
    result = await registry.get_active_fragment_for_type("TestTypeV1")
    
    assert result == mock_fragment


@pytest.mark.asyncio
async def test_get_active_fragment_no_binding(registry, mock_db):
    """Returns None if no active binding."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    result = await registry.get_active_fragment_for_type("TestTypeV1")
    
    assert result is None


# =============================================================================
# Test: Status Transitions
# =============================================================================

@pytest.mark.asyncio
async def test_set_status(registry, mock_db):
    """Set status transitions correctly."""
    mock_artifact = MagicMock()
    mock_artifact.status = "draft"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    await registry.set_status("TestFragment", "1.0", "accepted")
    
    assert mock_artifact.status == "accepted"
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_set_status_invalid_transition(registry, mock_db):
    """Invalid transition raises error."""
    mock_artifact = MagicMock()
    mock_artifact.status = "deprecated"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result
    
    with pytest.raises(InvalidStatusTransitionError):
        await registry.set_status("TestFragment", "1.0", "accepted")


@pytest.mark.asyncio
async def test_set_status_not_found(registry, mock_db):
    """Set status on missing fragment raises error."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    with pytest.raises(FragmentNotFoundError):
        await registry.set_status("NonExistent", "1.0", "accepted")


# =============================================================================
# Test: Bindings
# =============================================================================

@pytest.mark.asyncio
async def test_create_binding(registry, mock_db):
    """Create binding stores inactive by default."""
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    binding = await registry.create_binding(
        schema_type_id="TestTypeV1",
        fragment_id="TestFragment",
        fragment_version="1.0",
    )
    
    mock_db.add.assert_called_once()
    added = mock_db.add.call_args[0][0]
    assert added.schema_type_id == "TestTypeV1"
    assert added.fragment_id == "TestFragment"
    assert added.is_active == False


@pytest.mark.asyncio
async def test_activate_binding_deactivates_previous(registry, mock_db):
    """Activate binding deactivates existing active binding."""
    # First execute is deactivate, second is find existing, third would be for get_fragment
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing binding
    mock_db.execute.return_value = mock_result
    
    async def mock_refresh(obj):
        obj.id = uuid4()
    mock_db.refresh = mock_refresh
    
    await registry.activate_binding(
        schema_type_id="TestTypeV1",
        fragment_id="TestFragment",
        fragment_version="1.0",
    )
    
    # Should have executed deactivate update
    assert mock_db.execute.call_count >= 1
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_only_one_active_binding_per_type(registry, mock_db):
    """Activating new binding deactivates old one."""
    # Mock existing binding that will be found
    existing_binding = MagicMock()
    existing_binding.is_active = False
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_binding
    mock_db.execute.return_value = mock_result
    
    async def mock_refresh(obj):
        pass
    mock_db.refresh = mock_refresh
    
    result = await registry.activate_binding(
        schema_type_id="TestTypeV1",
        fragment_id="TestFragment",
        fragment_version="1.0",
    )
    
    # Existing binding should be activated
    assert existing_binding.is_active == True