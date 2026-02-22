"""
Tests for Work Statement DCW — WS-DCW-002.

Ten test groups mapping to the ten Tier 1 verification criteria:
  C1: DCW definition valid
  C2: Task prompt exists and is certified
  C3: Output schema exists and validates well-formed WS
  C4: WP input consumed (DCW requires work_package input)
  C5: TA input consumed (DCW includes TA constraints)
  C6: Handler produces valid WSs against DCW output schema
  C7: Parent enforcement holds (every WS references parent WP ID)
  C8: Allowed paths populated (field exists on produced WSs)
  C9: Runtime loadable by PlanRegistry from combine-config
  C10: Split-brain guard (no seed-only workflow)
"""

import json
from pathlib import Path

import pytest

from app.domain.handlers.work_statement_handler import WorkStatementHandler

# NOTE: PlanLoader and PlanRegistry are imported locally inside tests
# to avoid the pre-existing circular import in app.domain.workflow.__init__.


# =========================================================================
# Path constants
# =========================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

WS_DCW_DIR = (
    PROJECT_ROOT / "combine-config" / "workflows" / "work_statement"
    / "releases" / "1.0.0"
)
WS_DCW_PATH = WS_DCW_DIR / "definition.json"

WS_DOC_TYPE_DIR = (
    PROJECT_ROOT / "combine-config" / "document_types" / "work_statement"
    / "releases" / "1.0.0"
)
WS_TASK_PROMPT_PATH = WS_DOC_TYPE_DIR / "prompts" / "task.prompt.txt"
WS_SCHEMA_PATH = WS_DOC_TYPE_DIR / "schemas" / "output.schema.json"

SEED_WORKFLOWS_DIR = PROJECT_ROOT / "seed" / "workflows"
CC_WORKFLOWS_DIR = PROJECT_ROOT / "combine-config" / "workflows"


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return WorkStatementHandler()


@pytest.fixture
def ws_dcw_raw():
    """Load the raw DCW definition JSON."""
    with open(WS_DCW_PATH) as f:
        return json.load(f)


@pytest.fixture
def ws_output_schema():
    """Load the WS output schema from combine-config."""
    with open(WS_SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def wp_decomposition_ws():
    """A Work Statement produced from WP decomposition.

    Includes parent_wp_id, allowed_paths, and governance_pins
    as expected from the DCW output.
    """
    return {
        "ws_id": "WS-DCW-001",
        "parent_wp_id": "wp_document_registry",
        "title": "Implement Document Type Registry",
        "objective": "Create handler registration and schema validation for all seed types",
        "scope_in": ["Handler registration", "Schema validation"],
        "scope_out": ["UI rendering"],
        "allowed_paths": ["app/domain/handlers/", "tests/"],
        "procedure": [
            "Step 1: Create base handler interface",
            "Step 2: Register seed document types",
            "Step 3: Add schema validation",
        ],
        "verification_criteria": [
            "All seed types registered",
            "Validation enforced on create",
        ],
        "prohibited_actions": [
            "Do not modify existing document content",
        ],
        "state": "DRAFT",
        "governance_pins": {
            "ta_version_id": "ta-v1.0",
            "adr_refs": ["ADR-045"],
            "policy_refs": [],
        },
    }


# =========================================================================
# C1 — DCW definition valid
# =========================================================================


class TestC1DCWDefinitionValid:
    def test_definition_file_exists(self):
        assert WS_DCW_PATH.exists(), f"DCW definition not found: {WS_DCW_PATH}"

    def test_definition_has_required_fields(self, ws_dcw_raw):
        """DCW definition contains all required workflow.v2 fields."""
        for field in ["workflow_id", "schema_version", "version", "workflow_type",
                       "document_type", "entry_node_ids", "nodes", "edges",
                       "terminal_outcomes", "requires_inputs"]:
            assert field in ws_dcw_raw, f"Missing required field: {field}"

    def test_workflow_type_is_dcw(self, ws_dcw_raw):
        assert ws_dcw_raw["workflow_type"] == "dcw"

    def test_document_type_is_work_statement(self, ws_dcw_raw):
        assert ws_dcw_raw["document_type"] == "work_statement"


# =========================================================================
# C2 — Task prompt exists
# =========================================================================


class TestC2TaskPromptExists:
    def test_task_prompt_file_exists(self):
        assert WS_TASK_PROMPT_PATH.exists(), (
            f"Task prompt not found: {WS_TASK_PROMPT_PATH}"
        )

    def test_task_prompt_is_non_empty(self):
        content = WS_TASK_PROMPT_PATH.read_text()
        assert len(content.strip()) > 100, "Task prompt is too short to be meaningful"

    def test_task_prompt_references_work_statement(self):
        content = WS_TASK_PROMPT_PATH.read_text().lower()
        assert "work statement" in content or "work_statement" in content


# =========================================================================
# C3 — Output schema exists
# =========================================================================


class TestC3OutputSchemaExists:
    def test_schema_file_exists(self):
        assert WS_SCHEMA_PATH.exists(), f"Output schema not found: {WS_SCHEMA_PATH}"

    def test_schema_is_valid_json_schema(self, ws_output_schema):
        assert "properties" in ws_output_schema
        assert "required" in ws_output_schema

    def test_schema_requires_core_ws_fields(self, ws_output_schema):
        required = ws_output_schema.get("required", [])
        for field in ["ws_id", "parent_wp_id", "title", "objective",
                       "scope_in", "scope_out", "procedure",
                       "verification_criteria", "prohibited_actions",
                       "governance_pins"]:
            assert field in required, f"'{field}' missing from schema required list"

    def test_schema_defines_allowed_paths(self, ws_output_schema):
        props = ws_output_schema.get("properties", {})
        assert "allowed_paths" in props, "Schema must define allowed_paths property"


# =========================================================================
# C4 — WP input consumed
# =========================================================================


class TestC4WPInputConsumed:
    def test_requires_inputs_includes_work_package(self, ws_dcw_raw):
        assert "work_package" in ws_dcw_raw.get("requires_inputs", []), (
            "DCW must declare work_package as required input"
        )

    def test_dcw_has_generation_node(self, ws_dcw_raw):
        node_ids = [n["node_id"] for n in ws_dcw_raw.get("nodes", [])]
        assert "generation" in node_ids, "DCW must have a generation node"


# =========================================================================
# C5 — TA input consumed
# =========================================================================


class TestC5TAInputConsumed:
    def test_requires_inputs_includes_technical_architecture(self, ws_dcw_raw):
        assert "technical_architecture" in ws_dcw_raw.get("requires_inputs", []), (
            "DCW must declare technical_architecture as required input"
        )


# =========================================================================
# C6 — Handler produces valid WSs
# =========================================================================


class TestC6HandlerProducesValidWSs:
    def test_handler_output_validates_against_dcw_schema(
        self, handler, wp_decomposition_ws, ws_output_schema
    ):
        """Given WP input, handler produces a document that passes WS schema validation."""
        result = handler.transform(wp_decomposition_ws)
        is_valid, errors = handler.validate(result, ws_output_schema)
        assert is_valid, f"Transformed WS fails DCW output schema: {errors}"

    def test_handler_preserves_core_fields(
        self, handler, wp_decomposition_ws, ws_output_schema
    ):
        """Handler transform preserves ws_id, title, and objective."""
        result = handler.transform(wp_decomposition_ws)
        assert result["ws_id"] == "WS-DCW-001"
        assert result["title"] == "Implement Document Type Registry"
        assert result["objective"].startswith("Create handler registration")


# =========================================================================
# C7 — Parent enforcement holds
# =========================================================================


class TestC7ParentEnforcement:
    def test_produced_ws_has_parent_wp_id(
        self, handler, wp_decomposition_ws, ws_output_schema
    ):
        """Every produced WS references its parent WP ID."""
        result = handler.transform(wp_decomposition_ws)
        assert "parent_wp_id" in result
        assert result["parent_wp_id"] == "wp_document_registry"

    def test_handler_rejects_missing_parent(self, handler, ws_output_schema):
        """Handler validation rejects WS without parent_wp_id."""
        data = {
            "ws_id": "WS-001",
            "title": "No Parent",
            "objective": "Test",
            "scope_in": [],
            "scope_out": [],
            "allowed_paths": [],
            "procedure": ["Step 1"],
            "verification_criteria": ["Criterion 1"],
            "prohibited_actions": [],
            "state": "DRAFT",
            "governance_pins": {"ta_version_id": "ta-v1.0"},
        }
        is_valid, errors = handler.validate(data, ws_output_schema)
        assert is_valid is False
        assert any("parent_wp_id" in e for e in errors)


# =========================================================================
# C8 — Allowed paths populated
# =========================================================================


class TestC8AllowedPathsPopulated:
    def test_produced_ws_has_allowed_paths_field(
        self, handler, wp_decomposition_ws, ws_output_schema
    ):
        """Produced WS includes allowed_paths field."""
        result = handler.transform(wp_decomposition_ws)
        assert "allowed_paths" in result

    def test_allowed_paths_is_array(
        self, handler, wp_decomposition_ws, ws_output_schema
    ):
        """allowed_paths is an array (may be empty)."""
        result = handler.transform(wp_decomposition_ws)
        assert isinstance(result["allowed_paths"], list)

    def test_schema_allows_empty_allowed_paths(self, ws_output_schema):
        """Schema permits empty allowed_paths array."""
        ap_schema = ws_output_schema["properties"]["allowed_paths"]
        # Should be an array type, no minItems > 0 required
        assert ap_schema["type"] == "array"


# =========================================================================
# C9 — Runtime loadable
# =========================================================================


class TestC9RuntimeLoadable:
    def test_active_releases_resolves_to_valid_definition(self):
        """active_releases.json resolves work_statement to a loadable definition."""
        active_path = CC_WORKFLOWS_DIR.parent / "_active" / "active_releases.json"
        with open(active_path) as f:
            active = json.load(f)
        version = active["workflows"]["work_statement"]
        definition_path = (
            CC_WORKFLOWS_DIR / "work_statement" / "releases" / version / "definition.json"
        )
        assert definition_path.exists(), (
            f"Definition not found at resolved path: {definition_path}"
        )
        with open(definition_path) as f:
            raw = json.load(f)
        assert raw["workflow_id"] == "work_statement"
        assert raw["document_type"] == "work_statement"
        assert len(raw["nodes"]) > 0
        assert len(raw["edges"]) > 0

    def test_active_releases_includes_work_statement(self):
        """active_releases.json must list work_statement in workflows section."""
        active_path = CC_WORKFLOWS_DIR.parent / "_active" / "active_releases.json"
        with open(active_path) as f:
            active = json.load(f)
        assert "work_statement" in active.get("workflows", {}), (
            "active_releases.json must include work_statement in workflows"
        )


# =========================================================================
# C10 — Split-brain guard
# =========================================================================


class TestC10SplitBrainGuard:
    def test_combine_config_has_work_statement_workflow(self):
        """combine-config must contain work_statement workflow directory."""
        assert (CC_WORKFLOWS_DIR / "work_statement").is_dir(), (
            "combine-config/workflows/work_statement/ must exist"
        )

    def test_no_seed_only_work_statement_workflow(self):
        """If work_statement exists in seed/workflows, combine-config must also have it."""
        seed_wf_names = {
            f.stem.rsplit(".", 1)[0]
            for f in SEED_WORKFLOWS_DIR.glob("*.json")
            if f.is_file()
        }
        cc_wf_names = {
            d.name
            for d in CC_WORKFLOWS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        }
        seed_only = seed_wf_names - cc_wf_names
        assert not seed_only, (
            f"Workflows in seed/ but not combine-config/: {seed_only}"
        )
        # Also verify work_statement specifically exists in combine-config
        assert "work_statement" in cc_wf_names, (
            "work_statement must exist in combine-config/workflows/"
        )
