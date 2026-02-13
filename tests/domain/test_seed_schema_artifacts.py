"""
Tests for schema artifact seeding (ADR-031, ADR-033).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from seed.registry.schema_artifacts import (
    INITIAL_SCHEMA_ARTIFACTS,
    OPEN_QUESTION_V1_SCHEMA,
    RISK_V1_SCHEMA,
    seed_schema_artifacts,
)


# =============================================================================
# Test: Seed Data Validity
# =============================================================================

def test_open_question_v1_has_required_fields():
    """OpenQuestionV1 schema has all required fields."""
    schema = OPEN_QUESTION_V1_SCHEMA
    
    assert schema["$id"] == "schema:OpenQuestionV1"
    assert "required" in schema
    assert "id" in schema["required"]
    assert "text" in schema["required"]
    assert "blocking" in schema["required"]
    assert "why_it_matters" in schema["required"]


def test_open_question_v1_has_options():
    """OpenQuestionV1 supports options array."""
    schema = OPEN_QUESTION_V1_SCHEMA
    
    assert "options" in schema["properties"]
    assert schema["properties"]["options"]["type"] == "array"


def test_risk_v1_has_required_fields():
    """RiskV1 schema has required fields."""
    schema = RISK_V1_SCHEMA
    
    assert "description" in schema["required"]
    assert "impact" in schema["required"]


def test_initial_schemas_have_valid_kind():
    """All initial schemas have valid kind (type or envelope)."""
    valid_kinds = {"type", "envelope", "document"}
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        assert artifact["kind"] in valid_kinds, f"{artifact['schema_id']} has invalid kind"


def test_initial_schemas_are_accepted():
    """All initial schemas have accepted status."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        assert artifact["status"] == "accepted"


def test_initial_schemas_have_governance():
    """All initial schemas reference a governing ADR."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        adrs = artifact["governance_refs"]["adrs"]
        # Must reference at least one ADR (ADR-031 for canonical types, ADR-033 for render models)
        assert len(adrs) > 0, f"{artifact['schema_id']} has no governing ADR"
        assert any(adr.startswith("ADR-") for adr in adrs)


def test_canonical_types_reference_adr031():
    """Canonical content types (not render models) reference ADR-031."""
    content_types = ["OpenQuestionV1", "RiskV1", "ScopeListV1", "DependencyV1"]
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        if artifact["schema_id"] in content_types:
            assert "ADR-031" in artifact["governance_refs"]["adrs"]


def test_render_model_types_reference_adr033():
    """Render model types reference ADR-033."""
    render_types = ["RenderModelV1", "RenderSectionV1", "RenderBlockV1", "RenderActionV1"]
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        if artifact["schema_id"] in render_types:
            assert "ADR-033" in artifact["governance_refs"]["adrs"]


def test_schemas_are_valid_json_schema():
    """All schemas are structurally valid JSON Schema."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        schema = artifact["schema_json"]
        
        # Basic structure
        assert "type" in schema or "$ref" in schema
        
        # Has $id
        assert "$id" in schema
        assert schema["$id"].startswith("schema:")
        
        # Can serialize
        json.dumps(schema)


def test_expected_schema_count():
    """Expected number of seed schemas."""
    # 4 canonical types (ADR-031) + 4 render model types (ADR-033) + 2 document schemas (ADR-034)
    # + 2 story schemas (ADR-034-EXP3) + 3 discovery schemas (ADR-034-DISCOVERY) + 1 paragraph
    # + 1 indicator + 1 epic summary + 1 dependencies + 1 document ref + 1 story summary
    # + 1 stories container + 6 architecture schemas (arch component, quality attribute,
    # interface, workflow, data model, epic stories card)
    # + 1 ConciergeIntakeDocumentV1 (ADR-025/ADR-039)
    assert len(INITIAL_SCHEMA_ARTIFACTS) == 35


# =============================================================================
# Test: Seed Function
# =============================================================================

@pytest.mark.asyncio
async def test_seed_creates_schemas():
    """Seed function creates schema artifacts."""
    mock_db = AsyncMock()
    
    with patch("seed.registry.schema_artifacts.SchemaRegistryService") as MockRegistry:
        mock_registry = AsyncMock()
        mock_registry.get_by_id.return_value = None  # None exist
        mock_registry.create.return_value = MagicMock()
        MockRegistry.return_value = mock_registry
        
        count = await seed_schema_artifacts(mock_db)
        
        assert count == len(INITIAL_SCHEMA_ARTIFACTS)
        assert mock_registry.create.call_count == len(INITIAL_SCHEMA_ARTIFACTS)


@pytest.mark.asyncio
async def test_seed_skips_existing():
    """Seed function skips existing schemas."""
    mock_db = AsyncMock()
    
    with patch("seed.registry.schema_artifacts.SchemaRegistryService") as MockRegistry:
        mock_registry = AsyncMock()
        # First one exists, rest don't
        side_effects = [MagicMock()] + [None] * (len(INITIAL_SCHEMA_ARTIFACTS) - 1)
        mock_registry.get_by_id.side_effect = side_effects
        mock_registry.create.return_value = MagicMock()
        MockRegistry.return_value = mock_registry
        
        count = await seed_schema_artifacts(mock_db)
        
        assert count == len(INITIAL_SCHEMA_ARTIFACTS) - 1


@pytest.mark.asyncio
async def test_seed_idempotent():
    """Running seed twice doesn't duplicate."""
    mock_db = AsyncMock()
    
    with patch("seed.registry.schema_artifacts.SchemaRegistryService") as MockRegistry:
        mock_registry = AsyncMock()
        # All exist
        mock_registry.get_by_id.return_value = MagicMock()
        MockRegistry.return_value = mock_registry
        
        count = await seed_schema_artifacts(mock_db)
        
        assert count == 0
        mock_registry.create.assert_not_called()











