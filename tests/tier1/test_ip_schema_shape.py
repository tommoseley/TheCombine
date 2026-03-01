"""Tests for WS-IAV-002: IP Document Output Shape vs Schema Authority.

Validates that the implementation_plan task prompt and handler emit
document JSON conforming to the governing schema at:
  combine-config/schemas/implementation_plan/releases/1.0.0/schema.json

All structural contracts verified by reading source files and fixtures.
No runtime, no DB, no LLM.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / "combine-config"
    / "schemas"
    / "implementation_plan"
    / "releases"
    / "1.0.0"
    / "schema.json"
)
PROMPT_PATH = (
    REPO_ROOT
    / "combine-config"
    / "prompts"
    / "tasks"
    / "implementation_plan"
    / "releases"
    / "1.0.0"
    / "task.prompt.txt"
)
HANDLER_PATH = (
    REPO_ROOT
    / "app"
    / "domain"
    / "handlers"
    / "implementation_plan_handler.py"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _read(path: Path) -> str:
    return path.read_text()


# ===================================================================
# 1. Top-level field compliance
# ===================================================================


class TestTopLevelFields:
    """Prompt must instruct LLM to emit schema-declared top-level fields only."""

    def test_prompt_uses_work_package_candidates(self):
        """Prompt instructs output field 'work_package_candidates', not 'work_packages'."""
        prompt = _read(PROMPT_PATH)
        schema = _load_schema()
        # Schema requires work_package_candidates
        assert "work_package_candidates" in schema["required"]
        # Prompt must reference work_package_candidates as the output field
        assert "work_package_candidates" in prompt

    def test_prompt_does_not_instruct_work_packages_output(self):
        """Prompt must not instruct LLM to emit top-level 'work_packages[]' as output field."""
        prompt = _read(PROMPT_PATH)
        # Check the Output Structure section — must use work_package_candidates, not work_packages
        output_section = ""
        if "## Output Structure" in prompt:
            output_section = prompt.split("## Output Structure")[1].split("## Failure Conditions")[0]
        assert "work_package_candidates" in output_section
        assert "work_packages" not in output_section.replace("work_package_candidates", "")

    def test_prompt_does_not_instruct_candidate_reconciliation(self):
        """Prompt must not instruct LLM to emit 'candidate_reconciliation' field."""
        prompt = _read(PROMPT_PATH)
        schema = _load_schema()
        # Schema does not declare candidate_reconciliation
        assert "candidate_reconciliation" not in schema["properties"]
        # Prompt must not list candidate_reconciliation as an output section.
        # It MAY appear in prohibition/failure sections (telling LLM NOT to emit it).
        output_section = prompt.split("## Output Structure")[1].split("## Failure Conditions")[0] if "## Output Structure" in prompt else ""
        assert "candidate_reconciliation" not in output_section

    def test_schema_top_level_additionalProperties_false(self):
        """Schema has additionalProperties: false at top level."""
        schema = _load_schema()
        assert schema["additionalProperties"] is False


# ===================================================================
# 2. meta compliance
# ===================================================================


class TestMetaCompliance:
    """meta block must match schema: schema_version const, no workflow_id."""

    def test_prompt_schema_version_matches_const(self):
        """Prompt instructs schema_version matching schema const value."""
        prompt = _read(PROMPT_PATH)
        schema = _load_schema()
        const_val = schema["properties"]["meta"]["properties"]["schema_version"]["const"]
        assert const_val == "3.0"
        # Prompt must instruct schema_version "3.0"
        assert 'schema_version' in prompt
        assert '"3.0"' in prompt or "'3.0'" in prompt

    def test_prompt_does_not_instruct_workflow_id_in_meta(self):
        """Prompt must not instruct LLM to emit meta.workflow_id."""
        prompt = _read(PROMPT_PATH)
        schema = _load_schema()
        meta_props = schema["properties"]["meta"]["properties"]
        # workflow_id is not in meta schema
        assert "workflow_id" not in meta_props
        # Prompt must not ask for workflow_id in meta output
        assert "workflow_id" not in prompt

    def test_meta_additionalProperties_false(self):
        """meta has additionalProperties: false."""
        schema = _load_schema()
        assert schema["properties"]["meta"]["additionalProperties"] is False


# ===================================================================
# 3. Candidate item compliance
# ===================================================================


class TestCandidateItemCompliance:
    """Each work_package_candidate item must use candidate_id, not wp_id."""

    def test_prompt_uses_candidate_id(self):
        """Prompt instructs candidate_id (WPC-### pattern), not wp_id."""
        prompt = _read(PROMPT_PATH)
        schema = _load_schema()
        wpc_def = schema["definitions"]["work_package_candidate"]
        assert "candidate_id" in wpc_def["required"]
        # Prompt must reference candidate_id for output
        assert "candidate_id" in prompt

    def test_prompt_candidate_id_pattern(self):
        """Prompt specifies WPC-### pattern for candidate_id."""
        prompt = _read(PROMPT_PATH)
        assert "WPC-" in prompt

    def test_candidate_schema_no_wp_level_fields(self):
        """Candidate schema does not include WP-level fields."""
        schema = _load_schema()
        wpc_def = schema["definitions"]["work_package_candidate"]
        wpc_props = set(wpc_def["properties"].keys())
        # These WP-level fields must NOT be in candidate schema
        assert "governance_pins" not in wpc_props
        assert "source_candidate_ids" not in wpc_props
        assert "transformation" not in wpc_props
        assert "transformation_notes" not in wpc_props
        assert "wp_id" not in wpc_props

    def test_prompt_does_not_instruct_wp_level_fields_on_candidates(self):
        """Prompt must not instruct governance_pins/source_candidate_ids as candidate output fields."""
        prompt = _read(PROMPT_PATH)
        # Extract the candidate output field spec section
        # These fields may appear in "Do NOT" / prohibition sections, but must not
        # appear as positive "must include" candidate fields
        candidate_section = ""
        if "## Work Package Candidates" in prompt:
            candidate_section = prompt.split("## Work Package Candidates")[1].split("##")[0]
        positive_lines = [
            line for line in candidate_section.splitlines()
            if line.strip().startswith("*") and "not" not in line.lower()
        ]
        positive_text = "\n".join(positive_lines)
        assert "governance_pins" not in positive_text
        assert "source_candidate_ids" not in positive_text

    def test_candidate_additionalProperties_false(self):
        """work_package_candidate has additionalProperties: false."""
        schema = _load_schema()
        wpc_def = schema["definitions"]["work_package_candidate"]
        assert wpc_def["additionalProperties"] is False


# ===================================================================
# 4. risk_summary compliance
# ===================================================================


class TestRiskSummaryCompliance:
    """risk_summary items must use affected_candidates with WPC-### ids."""

    def test_risk_summary_schema_uses_affected_candidates(self):
        """Schema risk_summary_item requires affected_candidates, not affected_wps."""
        schema = _load_schema()
        risk_def = schema["definitions"]["risk_summary_item"]
        assert "affected_candidates" in risk_def["required"]
        assert "affected_wps" not in risk_def.get("properties", {})

    def test_prompt_uses_affected_candidates(self):
        """Prompt instructs affected_candidates in risk_summary, not affected_wps."""
        prompt = _read(PROMPT_PATH)
        assert "affected_candidates" in prompt
        # affected_wps may appear in prohibition/failure conditions (telling LLM NOT to use it)
        # but must not appear as a positive output instruction
        risk_section = ""
        if "## risk_summary" in prompt:
            risk_section = prompt.split("## risk_summary")[1].split("##")[0]
        assert "affected_wps" not in risk_section

    def test_risk_summary_affected_candidates_pattern(self):
        """Schema requires WPC-### pattern for affected_candidates items."""
        schema = _load_schema()
        risk_def = schema["definitions"]["risk_summary_item"]
        items_schema = risk_def["properties"]["affected_candidates"]["items"]
        assert "pattern" in items_schema
        assert "WPC" in items_schema["pattern"]

    def test_risk_summary_additionalProperties_false(self):
        """risk_summary_item has additionalProperties: false."""
        schema = _load_schema()
        risk_def = schema["definitions"]["risk_summary_item"]
        assert risk_def["additionalProperties"] is False


# ===================================================================
# 5. Handler does not inject undeclared fields
# ===================================================================


class TestHandlerNoUndeclaredFields:
    """Handler transform must not add fields that violate additionalProperties: false."""

    def test_handler_transform_no_top_level_injection(self):
        """Handler transform must not add undeclared top-level fields."""
        src = _read(HANDLER_PATH)
        schema = _load_schema()
        top_level_props = set(schema["properties"].keys())
        # wp_count is not in schema properties — handler must not inject it
        assert "wp_count" not in top_level_props
        # Handler should not add wp_count to data
        assert 'data["wp_count"]' not in src

    def test_handler_transform_no_candidate_field_injection(self):
        """Handler transform must not add undeclared fields to candidate items."""
        src = _read(HANDLER_PATH)
        schema = _load_schema()
        wpc_props = set(schema["definitions"]["work_package_candidate"]["properties"].keys())
        # associated_risks is not in candidate schema
        assert "associated_risks" not in wpc_props
        # Handler should not inject associated_risks into candidates
        assert '["associated_risks"]' not in src
