"""
WS-WB-001: Schema Evolution + Versioning Model — Verification Tests.

Validates:
- All three schemas validate against JSON Schema draft-07 meta-schema
- active_releases.json references correct versions
- No $id collisions with existing schemas
- WP schema disallows ws_index entries when ta_version_id is "pending"
- WS schema contains NO WP-level fields
- WPC schema enforces additionalProperties: false
"""

import json
import pytest
from pathlib import Path

import jsonschema

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "combine-config"
ACTIVE_RELEASES_PATH = CONFIG_PATH / "_active" / "active_releases.json"

WP_SCHEMA_PATH = (
    CONFIG_PATH
    / "document_types"
    / "work_package"
    / "releases"
    / "1.1.0"
    / "schemas"
    / "output.schema.json"
)
WS_SCHEMA_PATH = (
    CONFIG_PATH
    / "document_types"
    / "work_statement"
    / "releases"
    / "1.1.0"
    / "schemas"
    / "output.schema.json"
)
WPC_SCHEMA_PATH = (
    CONFIG_PATH
    / "document_types"
    / "work_package_candidate"
    / "releases"
    / "1.0.0"
    / "schemas"
    / "output.schema.json"
)

# v1.0.0 schemas for collision checking
WP_V100_SCHEMA_PATH = (
    CONFIG_PATH
    / "document_types"
    / "work_package"
    / "releases"
    / "1.0.0"
    / "schemas"
    / "output.schema.json"
)
WS_V100_SCHEMA_PATH = (
    CONFIG_PATH
    / "document_types"
    / "work_statement"
    / "releases"
    / "1.0.0"
    / "schemas"
    / "output.schema.json"
)


@pytest.fixture
def wp_schema():
    with open(WP_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ws_schema():
    with open(WS_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def wpc_schema():
    with open(WPC_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def active_releases():
    with open(ACTIVE_RELEASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================================
# 1. Schema files exist and parse as valid JSON
# =========================================================================


class TestSchemaFilesExist:
    def test_wp_v110_schema_exists(self):
        assert WP_SCHEMA_PATH.exists()

    def test_ws_v110_schema_exists(self):
        assert WS_SCHEMA_PATH.exists()

    def test_wpc_v100_schema_exists(self):
        assert WPC_SCHEMA_PATH.exists()

    def test_wp_v110_parses_as_json(self, wp_schema):
        assert isinstance(wp_schema, dict)

    def test_ws_v110_parses_as_json(self, ws_schema):
        assert isinstance(ws_schema, dict)

    def test_wpc_v100_parses_as_json(self, wpc_schema):
        assert isinstance(wpc_schema, dict)


# =========================================================================
# 2. Schemas validate against JSON Schema draft-07 meta-schema
# =========================================================================


class TestSchemaMetaValidation:
    def test_wp_v110_valid_draft07(self, wp_schema):
        jsonschema.Draft7Validator.check_schema(wp_schema)

    def test_ws_v110_valid_draft07(self, ws_schema):
        jsonschema.Draft7Validator.check_schema(ws_schema)

    def test_wpc_v100_valid_draft07(self, wpc_schema):
        jsonschema.Draft7Validator.check_schema(wpc_schema)


# =========================================================================
# 3. active_releases.json references correct versions
# =========================================================================


class TestActiveReleasesVersions:
    def test_document_types_wp_version(self, active_releases):
        assert active_releases["document_types"]["work_package"] == "1.1.0"

    def test_document_types_ws_version(self, active_releases):
        assert active_releases["document_types"]["work_statement"] == "1.1.0"

    def test_document_types_wpc_version(self, active_releases):
        assert (
            active_releases["document_types"]["work_package_candidate"]
            == "1.0.0"
        )

    def test_schemas_wp_version(self, active_releases):
        assert active_releases["schemas"]["work_package"] == "1.1.0"

    def test_schemas_ws_version(self, active_releases):
        assert active_releases["schemas"]["work_statement"] == "1.1.0"

    def test_schemas_wpc_version(self, active_releases):
        assert (
            active_releases["schemas"]["work_package_candidate"] == "1.0.0"
        )


# =========================================================================
# 4. No $id collisions between new and existing schemas
# =========================================================================


class TestNoIdCollisions:
    def test_wp_v110_id_differs_from_v100(self, wp_schema):
        with open(WP_V100_SCHEMA_PATH, "r", encoding="utf-8") as f:
            v100 = json.load(f)
        assert wp_schema["$id"] != v100["$id"]

    def test_ws_v110_id_differs_from_v100(self, ws_schema):
        with open(WS_V100_SCHEMA_PATH, "r", encoding="utf-8") as f:
            v100 = json.load(f)
        assert ws_schema["$id"] != v100["$id"]

    def test_all_new_ids_unique(self, wp_schema, ws_schema, wpc_schema):
        ids = [wp_schema["$id"], ws_schema["$id"], wpc_schema["$id"]]
        assert len(ids) == len(set(ids)), f"Duplicate $id values: {ids}"


# =========================================================================
# 5. WP schema: ws_index/ta_version_id invariant enforcement
# =========================================================================


class TestWpInvariant:
    """WP schema disallows ws_index entries when ta_version_id is 'pending'."""

    def test_ws_index_allowed_when_ta_not_pending(self, wp_schema):
        """ws_index with entries is valid when ta_version_id != 'pending'."""
        doc = {
            "wp_id": "test_wp",
            "title": "Test",
            "rationale": "Test",
            "scope_in": ["item"],
            "scope_out": [],
            "dependencies": [],
            "definition_of_done": ["done"],
            "governance_pins": {"ta_version_id": "v1.0.0"},
            "ws_index": [
                {"ws_id": "WS-TEST-001", "order_key": "a0"},
            ],
        }
        jsonschema.validate(doc, wp_schema)

    def test_ws_index_rejected_when_ta_pending(self, wp_schema):
        """ws_index with entries is invalid when ta_version_id == 'pending'."""
        doc = {
            "wp_id": "test_wp",
            "title": "Test",
            "rationale": "Test",
            "scope_in": ["item"],
            "scope_out": [],
            "dependencies": [],
            "definition_of_done": ["done"],
            "governance_pins": {"ta_version_id": "pending"},
            "ws_index": [
                {"ws_id": "WS-TEST-001", "order_key": "a0"},
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, wp_schema)

    def test_empty_ws_index_ok_when_ta_pending(self, wp_schema):
        """Empty ws_index is valid even when ta_version_id == 'pending'."""
        doc = {
            "wp_id": "test_wp",
            "title": "Test",
            "rationale": "Test",
            "scope_in": ["item"],
            "scope_out": [],
            "dependencies": [],
            "definition_of_done": ["done"],
            "governance_pins": {"ta_version_id": "pending"},
            "ws_index": [],
        }
        jsonschema.validate(doc, wp_schema)


# =========================================================================
# 6. WP schema: new fields present (ws_index, revision, change_summary)
# =========================================================================


class TestWpNewFields:
    def test_ws_index_in_properties(self, wp_schema):
        assert "ws_index" in wp_schema["properties"]

    def test_revision_in_properties(self, wp_schema):
        assert "revision" in wp_schema["properties"]

    def test_change_summary_in_properties(self, wp_schema):
        assert "change_summary" in wp_schema["properties"]

    def test_ws_child_refs_retained(self, wp_schema):
        """Legacy field retained for backward compat."""
        assert "ws_child_refs" in wp_schema["properties"]


# =========================================================================
# 7. WS schema: new fields present, no WP-level fields
# =========================================================================


WP_ONLY_FIELDS = {
    "ws_index",
    "change_summary",
    "ws_child_refs",
    "ws_total",
    "ws_done",
    "mode_b_count",
    "source_candidate_ids",
    "transformation",
    "transformation_notes",
    "definition_of_done",
    "dependencies",
}


class TestWsSchema:
    def test_order_key_in_properties(self, ws_schema):
        assert "order_key" in ws_schema["properties"]

    def test_revision_in_properties(self, ws_schema):
        assert "revision" in ws_schema["properties"]

    def test_no_wp_level_fields(self, ws_schema):
        ws_props = set(ws_schema["properties"].keys())
        overlap = ws_props & WP_ONLY_FIELDS
        assert not overlap, f"WS schema contains WP-level fields: {overlap}"


# =========================================================================
# 8. WPC schema: additionalProperties false, all required fields
# =========================================================================


class TestWpcSchema:
    def test_additional_properties_false(self, wpc_schema):
        assert wpc_schema.get("additionalProperties") is False

    def test_required_fields(self, wpc_schema):
        expected = {
            "wpc_id",
            "title",
            "rationale",
            "scope_summary",
            "source_ip_id",
            "source_ip_version",
            "frozen_at",
            "frozen_by",
        }
        assert set(wpc_schema["required"]) == expected

    def test_valid_candidate_passes(self, wpc_schema):
        doc = {
            "wpc_id": "WPC-001",
            "title": "Test Candidate",
            "rationale": "Test",
            "scope_summary": ["item one"],
            "source_ip_id": "ip-123",
            "source_ip_version": "1.0.0",
            "frozen_at": "2026-03-01T00:00:00Z",
            "frozen_by": "system",
        }
        jsonschema.validate(doc, wpc_schema)

    def test_extra_field_rejected(self, wpc_schema):
        doc = {
            "wpc_id": "WPC-001",
            "title": "Test Candidate",
            "rationale": "Test",
            "scope_summary": ["item one"],
            "source_ip_id": "ip-123",
            "source_ip_version": "1.0.0",
            "frozen_at": "2026-03-01T00:00:00Z",
            "frozen_by": "system",
            "sneaky_field": "should fail",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, wpc_schema)

    def test_invalid_wpc_id_rejected(self, wpc_schema):
        doc = {
            "wpc_id": "bad-id",
            "title": "Test",
            "rationale": "Test",
            "scope_summary": ["item"],
            "source_ip_id": "ip-123",
            "source_ip_version": "1.0.0",
            "frozen_at": "2026-03-01T00:00:00Z",
            "frozen_by": "system",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, wpc_schema)


# =========================================================================
# 9. Backward compatibility: v1.0.0 documents validate against v1.1.0
# =========================================================================


class TestBackwardCompatibility:
    def test_v100_wp_validates_against_v110(self, wp_schema):
        """A minimal v1.0.0 WP doc should still validate against v1.1.0."""
        doc = {
            "wp_id": "test_wp",
            "title": "Test WP",
            "rationale": "Testing",
            "scope_in": ["item"],
            "scope_out": [],
            "dependencies": [],
            "definition_of_done": ["done"],
            "governance_pins": {"ta_version_id": "v1.0.0"},
            "state": "PLANNED",
            "ws_child_refs": ["ws-1"],
            "ws_total": 1,
            "ws_done": 0,
        }
        jsonschema.validate(doc, wp_schema)

    def test_v100_ws_validates_against_v110(self, ws_schema):
        """A minimal v1.0.0 WS doc should still validate against v1.1.0."""
        doc = {
            "ws_id": "WS-TEST-001",
            "parent_wp_id": "test_wp",
            "title": "Test WS",
            "objective": "Test objective",
            "scope_in": ["item"],
            "scope_out": [],
            "procedure": ["step 1"],
            "verification_criteria": ["criterion 1"],
            "prohibited_actions": [],
            "governance_pins": {"ta_version_id": "v1.0.0"},
            "state": "DRAFT",
        }
        jsonschema.validate(doc, ws_schema)


# =========================================================================
# 10. Package.yaml files exist for all three doc types
# =========================================================================


class TestPackageYamlFiles:
    def test_wp_v110_package_yaml_exists(self):
        path = (
            CONFIG_PATH
            / "document_types"
            / "work_package"
            / "releases"
            / "1.1.0"
            / "package.yaml"
        )
        assert path.exists()

    def test_ws_v110_package_yaml_exists(self):
        path = (
            CONFIG_PATH
            / "document_types"
            / "work_statement"
            / "releases"
            / "1.1.0"
            / "package.yaml"
        )
        assert path.exists()

    def test_wpc_v100_package_yaml_exists(self):
        path = (
            CONFIG_PATH
            / "document_types"
            / "work_package_candidate"
            / "releases"
            / "1.0.0"
            / "package.yaml"
        )
        assert path.exists()
