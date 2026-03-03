"""Tests for WS-WB-021: WP Schema Drift — ws_index[] declaration and additionalProperties.

Validates the work_package v1.1.0 schema at:
  combine-config/schemas/work_package/releases/1.1.0/schema.json

Confirms:
- ws_index[] is declared and validates correct entries
- ws_index[] items with invalid shape are rejected
- ws_index[] is optional (documents without it validate)
- additionalProperties: false is enforced at top level
- All code-written fields are declared in the schema

No runtime, no DB, no LLM.
"""

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / "combine-config"
    / "schemas"
    / "work_package"
    / "releases"
    / "1.1.0"
    / "schema.json"
)
DOC_TYPE_SCHEMA_PATH = (
    REPO_ROOT
    / "combine-config"
    / "document_types"
    / "work_package"
    / "releases"
    / "1.1.0"
    / "schemas"
    / "output.schema.json"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _minimal_wp(**overrides) -> dict:
    """Build a minimal valid WP document with all required fields."""
    base = {
        "wp_id": "wp_wb_001",
        "title": "Test Work Package",
        "rationale": "Testing schema validation",
        "scope_in": ["Item 1"],
        "scope_out": ["Item 2"],
        "dependencies": [],
        "definition_of_done": ["All tests pass"],
        "governance_pins": {
            "ta_version_id": "v1",
        },
    }
    base.update(overrides)
    return base


def _validate(instance: dict, schema: dict | None = None):
    """Validate instance against the WP schema. Raises on failure."""
    if schema is None:
        schema = _load_schema()
    jsonschema.validate(instance, schema)


# ===================================================================
# 1. Schema file sanity
# ===================================================================


class TestSchemaFile:
    """Schema files exist and are valid JSON."""

    def test_global_schema_exists(self):
        assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"

    def test_doc_type_schema_exists(self):
        assert DOC_TYPE_SCHEMA_PATH.exists(), f"Schema not found at {DOC_TYPE_SCHEMA_PATH}"

    def test_schemas_are_identical(self):
        """Global and document_type schemas must be in sync."""
        global_schema = json.loads(SCHEMA_PATH.read_text())
        doc_type_schema = json.loads(DOC_TYPE_SCHEMA_PATH.read_text())
        assert global_schema == doc_type_schema


# ===================================================================
# 2. ws_index declaration and validation
# ===================================================================


class TestWsIndex:
    """ws_index[] is declared and validates correct entries."""

    def test_ws_index_declared_in_schema(self):
        """ws_index must be a declared property."""
        schema = _load_schema()
        assert "ws_index" in schema["properties"]

    def test_ws_index_is_array(self):
        """ws_index must be an array type."""
        schema = _load_schema()
        assert schema["properties"]["ws_index"]["type"] == "array"

    def test_ws_index_items_require_ws_id_and_order_key(self):
        """ws_index items must require ws_id and order_key."""
        schema = _load_schema()
        items = schema["properties"]["ws_index"]["items"]
        assert "ws_id" in items["required"]
        assert "order_key" in items["required"]

    def test_ws_index_items_have_additionalProperties_false(self):
        """ws_index items must reject unknown fields."""
        schema = _load_schema()
        items = schema["properties"]["ws_index"]["items"]
        assert items["additionalProperties"] is False

    def test_valid_ws_index_passes(self):
        """WP with valid ws_index entries validates successfully."""
        wp = _minimal_wp(ws_index=[
            {"ws_id": "WS-WB-001", "order_key": "a0"},
            {"ws_id": "WS-WB-002", "order_key": "a1"},
        ])
        _validate(wp)

    def test_empty_ws_index_passes(self):
        """WP with empty ws_index validates (new WP has no WSs yet)."""
        wp = _minimal_wp(ws_index=[])
        _validate(wp)

    def test_ws_index_missing_ws_id_fails(self):
        """ws_index entry without ws_id must fail validation."""
        wp = _minimal_wp(ws_index=[
            {"order_key": "a0"},
        ])
        with pytest.raises(jsonschema.ValidationError):
            _validate(wp)

    def test_ws_index_missing_order_key_fails(self):
        """ws_index entry without order_key must fail validation."""
        wp = _minimal_wp(ws_index=[
            {"ws_id": "WS-WB-001"},
        ])
        with pytest.raises(jsonschema.ValidationError):
            _validate(wp)

    def test_ws_index_extra_field_fails(self):
        """ws_index entry with extra field must fail (additionalProperties: false)."""
        wp = _minimal_wp(ws_index=[
            {"ws_id": "WS-WB-001", "order_key": "a0", "extra_field": "bad"},
        ])
        with pytest.raises(jsonschema.ValidationError):
            _validate(wp)

    def test_ws_index_item_wrong_type_fails(self):
        """ws_index containing non-object items must fail."""
        wp = _minimal_wp(ws_index=["not-an-object"])
        with pytest.raises(jsonschema.ValidationError):
            _validate(wp)


# ===================================================================
# 3. ws_index is optional
# ===================================================================


class TestWsIndexOptional:
    """ws_index is not required -- documents without it must validate."""

    def test_wp_without_ws_index_validates(self):
        """Minimal WP without ws_index must validate successfully."""
        wp = _minimal_wp()
        assert "ws_index" not in wp
        _validate(wp)

    def test_ws_index_not_in_required(self):
        """ws_index must NOT be in the required list."""
        schema = _load_schema()
        assert "ws_index" not in schema["required"]


# ===================================================================
# 4. additionalProperties: false at top level
# ===================================================================


class TestAdditionalPropertiesFalse:
    """Top-level additionalProperties: false must reject undeclared fields."""

    def test_schema_has_additionalProperties_false(self):
        """Schema must have additionalProperties: false at top level."""
        schema = _load_schema()
        assert schema["additionalProperties"] is False

    def test_unknown_top_level_field_fails(self):
        """WP with an unknown top-level field must fail validation."""
        wp = _minimal_wp(phantom_field="should not exist")
        with pytest.raises(jsonschema.ValidationError, match="phantom_field"):
            _validate(wp)

    def test_all_declared_properties_accepted(self):
        """WP with all declared optional properties must validate."""
        wp = _minimal_wp(
            state="PLANNED",
            ws_index=[{"ws_id": "WS-WB-001", "order_key": "a0"}],
            revision={"edition": 1, "updated_at": "2026-03-01T00:00:00+00:00", "updated_by": "system"},
            change_summary=["ws_index: added WS-WB-001"],
            ws_child_refs=["WS-WB-001"],
            ws_total=1,
            ws_done=0,
            mode_b_count=0,
            source_candidate_ids=["WPC-001"],
            transformation="kept",
            transformation_notes="Kept as-is",
            _lineage={
                "parent_document_type": "work_package_candidate",
                "parent_execution_id": None,
                "source_candidate_ids": ["WPC-001"],
                "transformation": "kept",
                "transformation_notes": "Kept as-is",
            },
        )
        _validate(wp)


# ===================================================================
# 5. Code-written fields are all declared
# ===================================================================


class TestCodeWrittenFields:
    """All fields written by promotion and edition services are in the schema."""

    def test_promoted_wp_fields_are_declared(self):
        """Fields output by build_promoted_wp must all be schema-declared."""
        schema = _load_schema()
        declared = set(schema["properties"].keys())

        # Fields written by wp_promotion_service.build_promoted_wp
        promotion_fields = {
            "wp_id", "title", "rationale", "scope_in", "scope_out",
            "dependencies", "definition_of_done", "governance_pins",
            "state", "ws_index", "revision", "source_candidate_ids",
            "transformation", "transformation_notes", "_lineage",
        }

        undeclared = promotion_fields - declared
        assert not undeclared, f"Undeclared fields written by promotion: {undeclared}"

    def test_edition_service_fields_are_declared(self):
        """Fields output by apply_edition_bump must all be schema-declared."""
        schema = _load_schema()
        declared = set(schema["properties"].keys())

        # Fields written by wp_edition_service.apply_edition_bump
        edition_fields = {"revision", "change_summary"}

        undeclared = edition_fields - declared
        assert not undeclared, f"Undeclared fields written by edition service: {undeclared}"

    def test_ws_crud_fields_are_declared(self):
        """Fields written by ws_crud_service to WP content must all be schema-declared."""
        schema = _load_schema()
        declared = set(schema["properties"].keys())

        # Field written by add_ws_to_wp_index
        crud_fields = {"ws_index"}

        undeclared = crud_fields - declared
        assert not undeclared, f"Undeclared fields written by WS CRUD: {undeclared}"


# ===================================================================
# 6. Conditional rule: pending ta_version_id blocks ws_index entries
# ===================================================================


class TestConditionalRule:
    """When ta_version_id is 'pending', ws_index must be empty."""

    def test_pending_ta_version_empty_ws_index_passes(self):
        """Pending governance_pins with empty ws_index must validate."""
        wp = _minimal_wp(
            governance_pins={"ta_version_id": "pending"},
            ws_index=[],
        )
        _validate(wp)

    def test_pending_ta_version_nonempty_ws_index_fails(self):
        """Pending governance_pins with ws_index entries must fail."""
        wp = _minimal_wp(
            governance_pins={"ta_version_id": "pending"},
            ws_index=[{"ws_id": "WS-WB-001", "order_key": "a0"}],
        )
        with pytest.raises(jsonschema.ValidationError):
            _validate(wp)

    def test_non_pending_ta_version_with_ws_index_passes(self):
        """Non-pending governance_pins allows ws_index entries."""
        wp = _minimal_wp(
            governance_pins={"ta_version_id": "v1.0.0"},
            ws_index=[{"ws_id": "WS-WB-001", "order_key": "a0"}],
        )
        _validate(wp)
