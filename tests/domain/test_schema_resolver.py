"""
Tests for Schema Resolver (ADR-031).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.schema_resolver import (
    SchemaResolver,
    CircularSchemaReferenceError,
    SchemaResolutionError,
)


@pytest.fixture
def mock_registry():
    """Create mock schema registry service."""
    return AsyncMock()


@pytest.fixture
def resolver(mock_registry):
    return SchemaResolver(mock_registry)


def make_artifact(schema_id: str, schema_json: dict, status: str = "accepted"):
    """Create a mock schema artifact."""
    artifact = MagicMock()
    artifact.schema_id = schema_id
    artifact.version = "1.0"
    artifact.status = status
    artifact.schema_json = schema_json
    artifact.sha256 = f"hash_{schema_id}"
    return artifact


# =============================================================================
# Test: Simple Resolution (No Refs)
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_simple_schema(resolver, mock_registry):
    """Resolve schema with no references."""
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    artifact = make_artifact("SimpleV1", schema)
    
    mock_registry.get_by_id.return_value = artifact
    
    bundle = await resolver.resolve_bundle("SimpleV1")
    
    assert bundle.root_schema_id == "SimpleV1"
    assert bundle.root_schema_version == "1.0"
    assert bundle.bundle_json["type"] == "object"
    assert len(bundle.bundle_sha256) == 64
    assert bundle.dependencies == []


# =============================================================================
# Test: Resolution with Single Ref
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_with_single_ref(resolver, mock_registry):
    """Resolve schema with one $ref."""
    root_schema = {
        "type": "object",
        "properties": {
            "question": {"$ref": "schema:OpenQuestionV1"}
        }
    }
    ref_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}}
    }
    
    root_artifact = make_artifact("DocV1", root_schema)
    ref_artifact = make_artifact("OpenQuestionV1", ref_schema)
    
    mock_registry.get_by_id.return_value = root_artifact
    mock_registry.get_accepted.return_value = ref_artifact
    
    bundle = await resolver.resolve_bundle("DocV1")
    
    # Should have $defs
    assert "$defs" in bundle.bundle_json
    assert "OpenQuestionV1" in bundle.bundle_json["$defs"]
    
    # Ref should be rewritten
    assert bundle.bundle_json["properties"]["question"]["$ref"] == "#/$defs/OpenQuestionV1"
    
    # Should track dependency
    assert len(bundle.dependencies) == 1
    assert bundle.dependencies[0].schema_id == "OpenQuestionV1"


# =============================================================================
# Test: Resolution with Nested Refs
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_with_nested_refs(resolver, mock_registry):
    """Resolve schema with nested references (A -> B -> C)."""
    schema_a = {
        "type": "object",
        "properties": {"b": {"$ref": "schema:SchemaB"}}
    }
    schema_b = {
        "type": "object",
        "properties": {"c": {"$ref": "schema:SchemaC"}}
    }
    schema_c = {
        "type": "object",
        "properties": {"value": {"type": "string"}}
    }
    
    artifact_a = make_artifact("SchemaA", schema_a)
    artifact_b = make_artifact("SchemaB", schema_b)
    artifact_c = make_artifact("SchemaC", schema_c)
    
    mock_registry.get_by_id.return_value = artifact_a
    mock_registry.get_accepted.side_effect = [artifact_b, artifact_c]
    
    bundle = await resolver.resolve_bundle("SchemaA")
    
    assert "SchemaB" in bundle.bundle_json["$defs"]
    assert "SchemaC" in bundle.bundle_json["$defs"]
    assert len(bundle.dependencies) == 2


# =============================================================================
# Test: Ref Rewriting
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_rewrites_refs(resolver, mock_registry):
    """All schema: refs are rewritten to #/$defs/."""
    schema = {
        "type": "array",
        "items": {"$ref": "schema:ItemV1"}
    }
    item_schema = {"type": "string"}
    
    root = make_artifact("ListV1", schema)
    item = make_artifact("ItemV1", item_schema)
    
    mock_registry.get_by_id.return_value = root
    mock_registry.get_accepted.return_value = item
    
    bundle = await resolver.resolve_bundle("ListV1")
    
    assert bundle.bundle_json["items"]["$ref"] == "#/$defs/ItemV1"


# =============================================================================
# Test: Bundle Hash
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_computes_bundle_hash(resolver, mock_registry):
    """Bundle has computed hash."""
    schema = {"type": "object"}
    artifact = make_artifact("SimpleV1", schema)
    mock_registry.get_by_id.return_value = artifact
    
    bundle = await resolver.resolve_bundle("SimpleV1")
    
    assert bundle.bundle_sha256 is not None
    assert len(bundle.bundle_sha256) == 64


# =============================================================================
# Test: Dependency Tracking
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_tracks_dependencies(resolver, mock_registry):
    """Dependencies include schema_id, version, and hash."""
    root_schema = {"items": {"$ref": "schema:TypeA"}}
    type_schema = {"type": "string"}
    
    root = make_artifact("RootV1", root_schema)
    type_a = make_artifact("TypeA", type_schema)
    type_a.version = "2.0"
    type_a.sha256 = "abc123"
    
    mock_registry.get_by_id.return_value = root
    mock_registry.get_accepted.return_value = type_a
    
    bundle = await resolver.resolve_bundle("RootV1")
    
    assert len(bundle.dependencies) == 1
    dep = bundle.dependencies[0]
    assert dep.schema_id == "TypeA"
    assert dep.version == "2.0"
    assert dep.sha256 == "abc123"


# =============================================================================
# Test: Circular Reference Detection
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_rejects_circular_ref(resolver, mock_registry):
    """Direct circular ref (A -> A) is rejected."""
    schema = {"items": {"$ref": "schema:CircularV1"}}
    artifact = make_artifact("CircularV1", schema)
    
    mock_registry.get_by_id.return_value = artifact
    mock_registry.get_accepted.return_value = artifact  # Points to self
    
    with pytest.raises(CircularSchemaReferenceError):
        await resolver.resolve_bundle("CircularV1")


@pytest.mark.asyncio
async def test_resolve_rejects_indirect_circular_ref(resolver, mock_registry):
    """Indirect circular ref (A -> B -> C -> A) is rejected."""
    schema_a = {"ref": {"$ref": "schema:B"}}
    schema_b = {"ref": {"$ref": "schema:C"}}
    schema_c = {"ref": {"$ref": "schema:A"}}  # Back to A
    
    artifact_a = make_artifact("A", schema_a)
    artifact_b = make_artifact("B", schema_b)
    artifact_c = make_artifact("C", schema_c)
    
    mock_registry.get_by_id.return_value = artifact_a
    mock_registry.get_accepted.side_effect = [artifact_b, artifact_c, artifact_a]
    
    with pytest.raises(CircularSchemaReferenceError):
        await resolver.resolve_bundle("A")


# =============================================================================
# Test: Only Accepted Schemas
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_only_accepted_root(resolver, mock_registry):
    """Draft root schema is rejected."""
    artifact = make_artifact("DraftV1", {"type": "object"}, status="draft")
    mock_registry.get_by_id.return_value = artifact
    
    with pytest.raises(SchemaResolutionError) as exc:
        await resolver.resolve_bundle("DraftV1")
    
    assert "draft" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_resolve_only_accepted_refs(resolver, mock_registry):
    """Missing referenced schema fails."""
    root_schema = {"ref": {"$ref": "schema:MissingV1"}}
    artifact = make_artifact("RootV1", root_schema)
    
    mock_registry.get_by_id.return_value = artifact
    mock_registry.get_accepted.return_value = None  # Not found
    
    with pytest.raises(SchemaResolutionError) as exc:
        await resolver.resolve_bundle("RootV1")
    
    assert "MissingV1" in str(exc.value)


# =============================================================================
# Test: Schema Not Found
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_root_not_found(resolver, mock_registry):
    """Missing root schema fails."""
    mock_registry.get_by_id.return_value = None
    
    with pytest.raises(SchemaResolutionError) as exc:
        await resolver.resolve_bundle("NonExistent")
    
    assert "not found" in str(exc.value).lower()