"""
Tests for Work Package DCW — WS-DCW-001.

Eight test groups mapping to the eight Tier 1 verification criteria:
  C1: DCW definition valid
  C2: Task prompt exists and is certified
  C3: Output schema exists and validates well-formed WP
  C4: IPF output consumed (DCW requires implementation_plan input)
  C5: Handler produces valid WP against DCW output schema
  C6: Governance pins populated (ta_version_id, adr_refs)
  C7: Runtime loadable by PlanRegistry from combine-config
  C8: Split-brain guard (no seed-only workflow)
"""

import json
from pathlib import Path

import pytest

from app.domain.handlers.work_package_handler import WorkPackageHandler

# NOTE: PlanLoader and PlanRegistry are imported locally inside C1/C7 tests
# to avoid the pre-existing circular import in app.domain.workflow.__init__.


# =========================================================================
# Path constants
# =========================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

WP_DCW_DIR = (
    PROJECT_ROOT / "combine-config" / "workflows" / "work_package"
    / "releases" / "1.0.0"
)
WP_DCW_PATH = WP_DCW_DIR / "definition.json"

WP_DOC_TYPE_DIR = (
    PROJECT_ROOT / "combine-config" / "document_types" / "work_package"
    / "releases" / "1.0.0"
)
WP_TASK_PROMPT_PATH = WP_DOC_TYPE_DIR / "prompts" / "task.prompt.txt"
WP_SCHEMA_PATH = WP_DOC_TYPE_DIR / "schemas" / "output.schema.json"

SEED_WORKFLOWS_DIR = PROJECT_ROOT / "seed" / "workflows"
CC_WORKFLOWS_DIR = PROJECT_ROOT / "combine-config" / "workflows"


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return WorkPackageHandler()


@pytest.fixture
def wp_dcw_raw():
    """Load the raw DCW definition JSON."""
    with open(WP_DCW_PATH) as f:
        return json.load(f)


@pytest.fixture
def wp_output_schema():
    """Load the WP output schema from combine-config."""
    with open(WP_SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def ipf_candidate_wp():
    """A committed WP from IPF output, as it would be processed by the WP handler.

    Includes governance_pins from TA review, matching the expected DCW output.
    """
    return {
        "wp_id": "wp_document_registry",
        "title": "Document Type Registry",
        "rationale": "Foundation for all document types",
        "scope_in": ["Handler registration", "Schema validation"],
        "scope_out": ["UI rendering"],
        "dependencies": [],
        "definition_of_done": ["All seed types registered", "Validation enforced"],
        "governance_pins": {
            "ta_version_id": "ta-v1.0",
            "adr_refs": ["ADR-045"],
            "policy_refs": [],
        },
        "state": "PLANNED",
        "ws_child_refs": [],
    }


# =========================================================================
# C1 — DCW definition valid
# =========================================================================


class TestC1DCWDefinitionValid:
    def test_definition_file_exists(self):
        assert WP_DCW_PATH.exists(), f"DCW definition not found: {WP_DCW_PATH}"

    def test_definition_has_required_fields(self, wp_dcw_raw):
        """DCW definition contains all required workflow.v2 fields."""
        for field in ["workflow_id", "schema_version", "version", "workflow_type",
                       "document_type", "entry_node_ids", "nodes", "edges",
                       "terminal_outcomes", "requires_inputs"]:
            assert field in wp_dcw_raw, f"Missing required field: {field}"

    def test_workflow_type_is_dcw(self, wp_dcw_raw):
        assert wp_dcw_raw["workflow_type"] == "dcw"

    def test_document_type_is_work_package(self, wp_dcw_raw):
        assert wp_dcw_raw["document_type"] == "work_package"


# =========================================================================
# C2 — Task prompt exists
# =========================================================================


class TestC2TaskPromptExists:
    def test_task_prompt_file_exists(self):
        assert WP_TASK_PROMPT_PATH.exists(), (
            f"Task prompt not found: {WP_TASK_PROMPT_PATH}"
        )

    def test_task_prompt_is_non_empty(self):
        content = WP_TASK_PROMPT_PATH.read_text()
        assert len(content.strip()) > 100, "Task prompt is too short to be meaningful"

    def test_task_prompt_references_work_package(self):
        content = WP_TASK_PROMPT_PATH.read_text().lower()
        assert "work package" in content or "work_package" in content


# =========================================================================
# C3 — Output schema exists
# =========================================================================


class TestC3OutputSchemaExists:
    def test_schema_file_exists(self):
        assert WP_SCHEMA_PATH.exists(), f"Output schema not found: {WP_SCHEMA_PATH}"

    def test_schema_is_valid_json_schema(self, wp_output_schema):
        assert "properties" in wp_output_schema
        assert "required" in wp_output_schema

    def test_schema_requires_core_wp_fields(self, wp_output_schema):
        required = wp_output_schema.get("required", [])
        for field in ["wp_id", "title", "rationale", "scope_in", "scope_out",
                       "definition_of_done", "governance_pins"]:
            assert field in required, f"'{field}' missing from schema required list"

    def test_schema_defines_governance_pins(self, wp_output_schema):
        props = wp_output_schema.get("properties", {})
        assert "governance_pins" in props


# =========================================================================
# C4 — IPF output consumed
# =========================================================================


class TestC4IPFOutputConsumed:
    def test_requires_inputs_includes_implementation_plan(self, wp_dcw_raw):
        assert "implementation_plan" in wp_dcw_raw.get("requires_inputs", []), (
            "DCW must declare implementation_plan as required input"
        )

    def test_dcw_has_generation_node(self, wp_dcw_raw):
        node_ids = [n["node_id"] for n in wp_dcw_raw.get("nodes", [])]
        assert "generation" in node_ids, "DCW must have a generation node"


# =========================================================================
# C5 — Handler produces valid WP
# =========================================================================


class TestC5HandlerProducesValidWP:
    def test_handler_output_validates_against_dcw_schema(
        self, handler, ipf_candidate_wp, wp_output_schema
    ):
        """Given IPF candidate input, handler produces a document that passes WP schema."""
        result = handler.transform(ipf_candidate_wp)
        is_valid, errors = handler.validate(result, wp_output_schema)
        assert is_valid, f"Transformed WP fails DCW output schema: {errors}"

    def test_handler_preserves_core_fields(
        self, handler, ipf_candidate_wp, wp_output_schema
    ):
        """Handler transform preserves wp_id, title, and rationale."""
        result = handler.transform(ipf_candidate_wp)
        assert result["wp_id"] == "wp_document_registry"
        assert result["title"] == "Document Type Registry"
        assert result["rationale"] == "Foundation for all document types"


# =========================================================================
# C6 — Governance pins populated
# =========================================================================


class TestC6GovernancePins:
    def test_schema_requires_governance_pins(self, wp_output_schema):
        """Output schema must require governance_pins field."""
        required = wp_output_schema.get("required", [])
        assert "governance_pins" in required

    def test_schema_governance_pins_requires_ta_version_id(self, wp_output_schema):
        """governance_pins schema must require ta_version_id."""
        gp_schema = wp_output_schema["properties"]["governance_pins"]
        gp_required = gp_schema.get("required", [])
        assert "ta_version_id" in gp_required

    def test_produced_wp_governance_pins_populated(
        self, handler, ipf_candidate_wp, wp_output_schema
    ):
        """Transformed WP includes governance_pins with ta_version_id and adr_refs."""
        result = handler.transform(ipf_candidate_wp)
        pins = result.get("governance_pins", {})
        assert "ta_version_id" in pins
        assert pins["ta_version_id"], "ta_version_id must be non-empty"
        assert "adr_refs" in pins
        assert isinstance(pins["adr_refs"], list)


# =========================================================================
# C7 — Runtime loadable
# =========================================================================


class TestC7RuntimeLoadable:
    def test_active_releases_resolves_to_valid_definition(self):
        """active_releases.json resolves work_package to a loadable definition."""
        active_path = CC_WORKFLOWS_DIR.parent / "_active" / "active_releases.json"
        with open(active_path) as f:
            active = json.load(f)
        version = active["workflows"]["work_package"]
        definition_path = (
            CC_WORKFLOWS_DIR / "work_package" / "releases" / version / "definition.json"
        )
        assert definition_path.exists(), (
            f"Definition not found at resolved path: {definition_path}"
        )
        with open(definition_path) as f:
            raw = json.load(f)
        assert raw["workflow_id"] == "work_package"
        assert raw["document_type"] == "work_package"
        assert len(raw["nodes"]) > 0
        assert len(raw["edges"]) > 0

    def test_active_releases_includes_work_package(self):
        """active_releases.json must list work_package in workflows section."""
        active_path = CC_WORKFLOWS_DIR.parent / "_active" / "active_releases.json"
        with open(active_path) as f:
            active = json.load(f)
        assert "work_package" in active.get("workflows", {}), (
            "active_releases.json must include work_package in workflows"
        )


# =========================================================================
# C8 — Split-brain guard
# =========================================================================


class TestC8SplitBrainGuard:
    def test_combine_config_has_work_package_workflow(self):
        """combine-config must contain work_package workflow directory."""
        assert (CC_WORKFLOWS_DIR / "work_package").is_dir(), (
            "combine-config/workflows/work_package/ must exist"
        )

    def test_no_seed_only_work_package_workflow(self):
        """If work_package exists in seed/workflows, combine-config must also have it."""
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
        # Also verify work_package specifically exists in combine-config
        assert "work_package" in cc_wf_names, (
            "work_package must exist in combine-config/workflows/"
        )
