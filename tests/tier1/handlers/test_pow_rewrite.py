"""
Tests for POW Rewrite — WS-DCW-003.

Ten test groups mapping to the ten Tier 1 verification criteria:
  C1: No Epic references in POW
  C2: No Feature references in POW
  C3: WP scope exists (parent "project")
  C4: WS scope exists (parent "work_package")
  C5: Step ordering matches ADR-053
  C6: Iteration block references WP
  C7: WS decomposition step exists inside per_work_package
  C8: POW validates clean (structural integrity)
  C9: TA inputs include implementation_plan (IPF)
  C10: Split-brain guard (no seed-only workflow)
"""

import json
from pathlib import Path


# =========================================================================
# Path constants
# =========================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CC_WORKFLOWS_DIR = PROJECT_ROOT / "combine-config" / "workflows"
SEED_WORKFLOWS_DIR = PROJECT_ROOT / "seed" / "workflows"

POW_DIR = (
    CC_WORKFLOWS_DIR / "software_product_development"
    / "releases" / "1.0.0"
)
POW_PATH = POW_DIR / "definition.json"


# =========================================================================
# Helpers
# =========================================================================


def _load_pow():
    """Load the POW definition JSON."""
    with open(POW_PATH) as f:
        return json.load(f)


def _all_values_recursive(obj, _seen=None):
    """Yield every string value in a nested dict/list structure."""
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return
    _seen.add(obj_id)
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_values_recursive(v, _seen)
    elif isinstance(obj, list):
        for item in obj:
            yield from _all_values_recursive(item, _seen)
    elif isinstance(obj, str):
        yield obj


# =========================================================================
# C1 — No Epic references in POW
# =========================================================================


class TestC1NoEpicReferences:
    def test_no_epic_in_scopes(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        assert "epic" not in scopes, "scopes must not contain 'epic'"

    def test_no_epic_in_document_types(self):
        pow_def = _load_pow()
        doc_types = pow_def.get("document_types", {})
        assert "epic" not in doc_types, "document_types must not contain 'epic'"

    def test_no_epic_in_entity_types(self):
        pow_def = _load_pow()
        entity_types = pow_def.get("entity_types", {})
        assert "epic" not in entity_types, "entity_types must not contain 'epic'"

    def test_no_epic_in_step_ids(self):
        """No step_id contains 'epic'."""
        pow_def = _load_pow()
        steps = pow_def.get("steps", [])
        for step in steps:
            step_id = step.get("step_id", "")
            assert "epic" not in step_id, (
                f"step_id '{step_id}' contains 'epic'"
            )

    def test_no_epic_creates_entities(self):
        """No step has creates_entities referencing 'epic'."""
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            ce = step.get("creates_entities", "")
            assert ce != "epic", (
                f"step '{step.get('step_id')}' creates_entities = 'epic'"
            )


# =========================================================================
# C2 — No Feature references in POW
# =========================================================================


class TestC2NoFeatureReferences:
    def test_no_feature_in_scopes(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        assert "feature" not in scopes, "scopes must not contain 'feature'"

    def test_no_feature_in_document_types(self):
        pow_def = _load_pow()
        doc_types = pow_def.get("document_types", {})
        assert "feature" not in doc_types, (
            "document_types must not contain 'feature'"
        )

    def test_no_feature_in_entity_types(self):
        pow_def = _load_pow()
        entity_types = pow_def.get("entity_types", {})
        assert "feature" not in entity_types, (
            "entity_types must not contain 'feature'"
        )

    def test_no_feature_in_step_produces(self):
        """No step produces 'feature' documents."""
        pow_def = _load_pow()

        def _check_steps(steps):
            for step in steps:
                produces = step.get("produces", "")
                assert produces != "feature", (
                    f"step '{step.get('step_id')}' produces 'feature'"
                )
                # Check nested steps in iteration blocks
                for nested in step.get("steps", []):
                    produces = nested.get("produces", "")
                    assert produces != "feature", (
                        f"nested step '{nested.get('step_id')}' produces 'feature'"
                    )

        _check_steps(pow_def.get("steps", []))


# =========================================================================
# C3 — WP scope exists
# =========================================================================


class TestC3WPScopeExists:
    def test_scopes_include_work_package(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        assert "work_package" in scopes, (
            "scopes must include 'work_package'"
        )

    def test_work_package_parent_is_project(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        wp_scope = scopes.get("work_package", {})
        assert wp_scope.get("parent") == "project", (
            "work_package scope parent must be 'project'"
        )


# =========================================================================
# C4 — WS scope exists
# =========================================================================


class TestC4WSScopeExists:
    def test_scopes_include_work_statement(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        assert "work_statement" in scopes, (
            "scopes must include 'work_statement'"
        )

    def test_work_statement_parent_is_work_package(self):
        pow_def = _load_pow()
        scopes = pow_def.get("scopes", {})
        ws_scope = scopes.get("work_statement", {})
        assert ws_scope.get("parent") == "work_package", (
            "work_statement scope parent must be 'work_package'"
        )


# =========================================================================
# C5 — Step ordering matches ADR-053
# =========================================================================


class TestC5StepOrdering:
    def test_step_order_matches_adr_053(self):
        """Top-level steps execute in order per ADR-053.

        Expected: discovery, primary_plan, implementation_plan,
                  technical_architecture, per_work_package
        """
        pow_def = _load_pow()
        steps = pow_def.get("steps", [])
        step_ids = [s["step_id"] for s in steps]
        expected = [
            "discovery",
            "primary_plan",
            "implementation_plan",
            "technical_architecture",
            "per_work_package",
        ]
        assert step_ids == expected, (
            f"Step ordering mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {step_ids}"
        )


# =========================================================================
# C6 — Iteration block references WP
# =========================================================================


class TestC6IterationBlockReferencesWP:
    def test_per_work_package_step_exists(self):
        pow_def = _load_pow()
        step_ids = [s["step_id"] for s in pow_def.get("steps", [])]
        assert "per_work_package" in step_ids, (
            "steps must include 'per_work_package'"
        )

    def test_iteration_doc_type_is_implementation_plan(self):
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "per_work_package":
                iterate = step.get("iterate_over", {})
                assert iterate.get("doc_type") == "implementation_plan", (
                    "per_work_package must iterate over implementation_plan"
                )
                return
        raise AssertionError("per_work_package step not found")

    def test_iteration_collection_field_is_work_packages(self):
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "per_work_package":
                iterate = step.get("iterate_over", {})
                assert iterate.get("collection_field") == "work_packages", (
                    "per_work_package must iterate over collection_field 'work_packages'"
                )
                return
        raise AssertionError("per_work_package step not found")

    def test_iteration_entity_type_is_work_package(self):
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "per_work_package":
                iterate = step.get("iterate_over", {})
                assert iterate.get("entity_type") == "work_package", (
                    "per_work_package must iterate over entity_type 'work_package'"
                )
                return
        raise AssertionError("per_work_package step not found")


# =========================================================================
# C7 — WS decomposition step exists
# =========================================================================


class TestC7WSDecompositionStep:
    def test_work_statement_decomposition_step_exists(self):
        """Inside per_work_package, a step with step_id 'work_statement_decomposition' exists."""
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "per_work_package":
                nested_ids = [
                    s["step_id"] for s in step.get("steps", [])
                ]
                assert "work_statement_decomposition" in nested_ids, (
                    f"per_work_package must contain 'work_statement_decomposition' step, "
                    f"got: {nested_ids}"
                )
                return
        raise AssertionError("per_work_package step not found")

    def test_work_statement_decomposition_produces_work_statement(self):
        """The WS decomposition step produces 'work_statement' documents."""
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "per_work_package":
                for nested in step.get("steps", []):
                    if nested.get("step_id") == "work_statement_decomposition":
                        assert nested.get("produces") == "work_statement", (
                            "work_statement_decomposition must produce 'work_statement'"
                        )
                        return
        raise AssertionError(
            "work_statement_decomposition step not found inside per_work_package"
        )


# =========================================================================
# C8 — POW validates clean
# =========================================================================


class TestC8POWValidatesClean:
    def test_pow_has_required_top_level_fields(self):
        pow_def = _load_pow()
        for field in ["schema_version", "workflow_id", "name",
                       "scopes", "document_types", "steps"]:
            assert field in pow_def, f"Missing required field: {field}"

    def test_pow_workflow_id_is_correct(self):
        pow_def = _load_pow()
        assert pow_def["workflow_id"] == "software_product_development"

    def test_every_step_has_step_id(self):
        """Every step (including nested) must have a step_id."""
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            assert "step_id" in step, f"Step missing step_id: {step}"
            for nested in step.get("steps", []):
                assert "step_id" in nested, (
                    f"Nested step missing step_id: {nested}"
                )

    def test_all_scope_references_are_defined(self):
        """Every scope referenced in steps/document_types exists in scopes."""
        pow_def = _load_pow()
        defined_scopes = set(pow_def.get("scopes", {}).keys())
        # Check document_types scope references
        for dt_id, dt_def in pow_def.get("document_types", {}).items():
            scope = dt_def.get("scope")
            if scope:
                assert scope in defined_scopes, (
                    f"document_type '{dt_id}' references undefined scope '{scope}'"
                )


# =========================================================================
# C9 — TA inputs include implementation_plan (IPF)
# =========================================================================


class TestC9TAInputsIncludeIPF:
    def test_ta_step_receives_implementation_plan(self):
        """Technical architecture step has implementation_plan as input."""
        pow_def = _load_pow()
        for step in pow_def.get("steps", []):
            if step.get("step_id") == "technical_architecture":
                input_types = [
                    inp.get("doc_type")
                    for inp in step.get("inputs", [])
                ]
                assert "implementation_plan" in input_types, (
                    f"TA step must receive implementation_plan as input. "
                    f"Got: {input_types}"
                )
                return
        raise AssertionError("technical_architecture step not found")


# =========================================================================
# C10 — Split-brain guard
# =========================================================================


class TestC10SplitBrainGuard:
    def test_combine_config_has_spd_workflow(self):
        """combine-config must contain software_product_development workflow directory."""
        assert (CC_WORKFLOWS_DIR / "software_product_development").is_dir(), (
            "combine-config/workflows/software_product_development/ must exist"
        )

    def test_no_seed_only_workflows(self):
        """If a workflow exists in seed/workflows, combine-config must also have it."""
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
