"""
Tests for schema artifact seeding (ADR-031).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.domain.registry.seed_schema_artifacts import (
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


def test_initial_schemas_are_types():
    """All initial schemas are canonical types."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        assert artifact["kind"] == "type"


def test_initial_schemas_are_accepted():
    """All initial schemas have accepted status."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        assert artifact["status"] == "accepted"


def test_initial_schemas_have_governance():
    """All initial schemas reference ADR-031."""
    for artifact in INITIAL_SCHEMA_ARTIFACTS:
        assert "ADR-031" in artifact["governance_refs"]["adrs"]


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


# =============================================================================
# Test: Seed Function
# =============================================================================

@pytest.mark.asyncio
async def test_seed_creates_schemas():
    """Seed function creates schema artifacts."""
    mock_db = AsyncMock()
    
    with patch("app.domain.registry.seed_schema_artifacts.SchemaRegistryService") as MockRegistry:
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
    
    with patch("app.domain.registry.seed_schema_artifacts.SchemaRegistryService") as MockRegistry:
        mock_registry = AsyncMock()
        # First one exists, others don't
        mock_registry.get_by_id.side_effect = [MagicMock(), None, None, None]
        mock_registry.create.return_value = MagicMock()
        MockRegistry.return_value = mock_registry
        
        count = await seed_schema_artifacts(mock_db)
        
        assert count == len(INITIAL_SCHEMA_ARTIFACTS) - 1


@pytest.mark.asyncio
async def test_seed_idempotent():
    """Running seed twice doesn't duplicate."""
    mock_db = AsyncMock()
    
    with patch("app.domain.registry.seed_schema_artifacts.SchemaRegistryService") as MockRegistry:
        mock_registry = AsyncMock()
        # All exist
        mock_registry.get_by_id.return_value = MagicMock()
        MockRegistry.return_value = mock_registry
        
        count = await seed_schema_artifacts(mock_db)
        
        assert count == 0
        mock_registry.create.assert_not_called()