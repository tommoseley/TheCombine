"""Tests for WS-PIPELINE-001: Pipeline Config & Doc Type Consolidation.

Verifies the IPP/IPF collapse into a single Implementation Plan (IP),
corrected POW step ordering, and execution_mode metadata.

Criteria 1-21 from WS-PIPELINE-001. All must FAIL before implementation
and PASS after.

Test approach: read combine-config files, app code, and verify structural
contracts. No runtime, no DB, no LLM.
"""

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMBINE_CONFIG = REPO_ROOT / "combine-config"
POW_DEF = (
    COMBINE_CONFIG / "workflows" / "software_product_development"
    / "releases" / "1.0.0" / "definition.json"
)
IP_RELEASE = COMBINE_CONFIG / "document_types" / "implementation_plan" / "releases" / "1.0.0"
IPP_DIR = COMBINE_CONFIG / "document_types" / "primary_implementation_plan"
WP_RELEASE = COMBINE_CONFIG / "document_types" / "work_package" / "releases" / "1.0.0"
ACTIVE_RELEASES = COMBINE_CONFIG / "_active" / "active_releases.json"
REGISTRY_PY = REPO_ROOT / "app" / "domain" / "handlers" / "registry.py"
DOC_NODE_JSX = REPO_ROOT / "spa" / "src" / "components" / "DocumentNode.jsx"
AUDIT_REPORT = REPO_ROOT / "docs" / "audits" / "WS-PIPELINE-001-prompt-audit.md"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _load_pow_steps() -> list:
    return _load_json(POW_DEF)["steps"]


def _step_by_produces(steps: list, produces: str) -> dict | None:
    for step in steps:
        if step.get("produces") == produces:
            return step
        # Check nested steps (e.g., per_work_package)
        for sub in step.get("steps", []):
            if sub.get("produces") == produces:
                return sub
    return None


def _step_index(steps: list, produces: str) -> int:
    for i, step in enumerate(steps):
        if step.get("produces") == produces:
            return i
    return -1


# =========================================================================
# POW Definition (Criteria 1-10)
# =========================================================================

class TestPOWDefinition:
    """Verify corrected POW step structure."""

    def test_c01_no_step_produces_primary_implementation_plan(self):
        """C1: No step produces primary_implementation_plan."""
        steps = _load_pow_steps()
        step = _step_by_produces(steps, "primary_implementation_plan")
        assert step is None, (
            "POW must not have a step producing primary_implementation_plan "
            "(collapsed into implementation_plan)"
        )

    def test_c02_implementation_plan_no_creates_entities(self):
        """C2: implementation_plan step has no creates_entities field."""
        steps = _load_pow_steps()
        step = _step_by_produces(steps, "implementation_plan")
        assert step is not None, "implementation_plan step must exist"
        assert "creates_entities" not in step, (
            f"implementation_plan step must not have creates_entities. "
            f"WP creation is now a separate manual step. "
            f"Found: {step.get('creates_entities')}"
        )

    def test_c03_work_package_creation_step_exists_after_ta(self):
        """C3: work_package_creation step exists after technical_architecture."""
        steps = _load_pow_steps()
        wpc_idx = _step_index(steps, "work_package")
        ta_idx = _step_index(steps, "technical_architecture")
        assert wpc_idx >= 0, (
            "POW must have a step producing work_package (work_package_creation)"
        )
        assert ta_idx >= 0, "POW must have a technical_architecture step"
        assert wpc_idx > ta_idx, (
            f"work_package_creation (idx {wpc_idx}) must come after "
            f"technical_architecture (idx {ta_idx})"
        )

    def test_c04_work_package_creation_inputs_include_ta(self):
        """C4: work_package_creation step inputs include technical_architecture."""
        steps = _load_pow_steps()
        step = _step_by_produces(steps, "work_package")
        assert step is not None, "work_package step must exist"
        inputs = step.get("inputs", [])
        input_doc_types = [
            inp.get("doc_type") if isinstance(inp, dict) else inp
            for inp in inputs
        ]
        assert "technical_architecture" in input_doc_types, (
            f"work_package step must include technical_architecture in inputs. "
            f"Current inputs: {inputs}"
        )

    def test_c05_work_package_creation_inputs_include_ip(self):
        """C5: work_package_creation step inputs include implementation_plan."""
        steps = _load_pow_steps()
        step = _step_by_produces(steps, "work_package")
        assert step is not None, "work_package step must exist"
        inputs = step.get("inputs", [])
        input_doc_types = [
            inp.get("doc_type") if isinstance(inp, dict) else inp
            for inp in inputs
        ]
        assert "implementation_plan" in input_doc_types, (
            f"work_package step must include implementation_plan in inputs. "
            f"Current inputs: {inputs}"
        )

    def test_c06_work_package_creation_execution_mode_manual(self):
        """C6: work_package_creation step has execution_mode: manual."""
        steps = _load_pow_steps()
        step = _step_by_produces(steps, "work_package")
        assert step is not None, "work_package step must exist"
        assert step.get("execution_mode") == "manual", (
            f"work_package step must have execution_mode: manual. "
            f"Found: {step.get('execution_mode')}"
        )

    def test_c07_step_order(self):
        """C7: Steps appear in order: discovery, implementation_plan,
        technical_architecture, work_package_creation, per_work_package."""
        steps = _load_pow_steps()
        expected_order = [
            "project_discovery",
            "implementation_plan",
            "technical_architecture",
        ]
        actual_produces = [s.get("produces") for s in steps if s.get("produces")]
        # Check the first 3 top-level steps are in the right order
        for i, expected in enumerate(expected_order):
            assert actual_produces[i] == expected, (
                f"Step {i} should produce '{expected}', "
                f"got '{actual_produces[i]}'. "
                f"Full order: {actual_produces}"
            )

    def test_c08_auto_steps_have_execution_mode(self):
        """C8: PD, IP, TA steps have execution_mode: auto."""
        steps = _load_pow_steps()
        for doc_type in ["project_discovery", "implementation_plan", "technical_architecture"]:
            step = _step_by_produces(steps, doc_type)
            assert step is not None, f"Step producing {doc_type} must exist"
            assert step.get("execution_mode") == "auto", (
                f"Step producing {doc_type} must have execution_mode: auto. "
                f"Found: {step.get('execution_mode')}"
            )

    def test_c09_per_work_package_execution_mode_manual(self):
        """C9: per_work_package step has execution_mode: manual."""
        steps = _load_pow_steps()
        # per_work_package is the step with iterate_over
        for step in steps:
            if step.get("iterate_over"):
                assert step.get("execution_mode") == "manual", (
                    f"per_work_package step must have execution_mode: manual. "
                    f"Found: {step.get('execution_mode')}"
                )
                return
        raise AssertionError("No per_work_package step (with iterate_over) found")

    def test_c10_no_primary_implementation_plan_in_document_types(self):
        """C10: POW document_types section has no primary_implementation_plan entry."""
        pow_def = _load_json(POW_DEF)
        doc_types = pow_def.get("document_types", {})
        assert "primary_implementation_plan" not in doc_types, (
            "POW document_types must not contain primary_implementation_plan"
        )


# =========================================================================
# Package Configs (Criteria 11-16)
# =========================================================================

class TestPackageConfigs:
    """Verify package.yaml and active_releases after consolidation."""

    def test_c11_no_primary_implementation_plan_directory(self):
        """C11: No primary_implementation_plan directory in document_types
        (or marked deprecated)."""
        if IPP_DIR.exists():
            # Check if it's marked deprecated
            pkg_yaml = IPP_DIR / "releases" / "1.0.0" / "package.yaml"
            if pkg_yaml.exists():
                pkg = _load_yaml(pkg_yaml)
                status = pkg.get("status", "active")
                assert status in ("deprecated", "archived", "superseded"), (
                    f"primary_implementation_plan directory still exists and is "
                    f"status='{status}'. Must be deprecated/archived or removed."
                )
            else:
                raise AssertionError(
                    "primary_implementation_plan directory exists but has no "
                    "package.yaml — ambiguous state"
                )

    def test_c12_ip_no_creates_children(self):
        """C12: implementation_plan package.yaml does not have
        creates_children: [work_package]."""
        pkg = _load_yaml(IP_RELEASE / "package.yaml")
        creates = pkg.get("creates_children", [])
        assert "work_package" not in creates, (
            f"implementation_plan must not have creates_children: [work_package]. "
            f"WP creation is now a separate manual step. Found: {creates}"
        )

    def test_c13_wp_requires_ta(self):
        """C13: work_package package.yaml required_inputs includes
        technical_architecture."""
        pkg = _load_yaml(WP_RELEASE / "package.yaml")
        req = pkg.get("required_inputs", [])
        assert "technical_architecture" in req, (
            f"work_package must require technical_architecture as input. "
            f"Current required_inputs: {req}"
        )

    def test_c14_wp_requires_ip(self):
        """C14: work_package package.yaml required_inputs includes
        implementation_plan."""
        pkg = _load_yaml(WP_RELEASE / "package.yaml")
        req = pkg.get("required_inputs", [])
        assert "implementation_plan" in req, (
            f"work_package must require implementation_plan as input. "
            f"Current required_inputs: {req}"
        )

    def test_c15_active_releases_no_ipp_in_document_types(self):
        """C15: active_releases.json has no primary_implementation_plan
        in document_types."""
        releases = _load_json(ACTIVE_RELEASES)
        doc_types = releases.get("document_types", {})
        assert "primary_implementation_plan" not in doc_types, (
            "active_releases.json must not contain primary_implementation_plan "
            "in document_types"
        )

    def test_c16_active_releases_no_ipp_in_schemas(self):
        """C16: active_releases.json has no primary_implementation_plan
        in schemas."""
        releases = _load_json(ACTIVE_RELEASES)
        schemas = releases.get("schemas", {})
        assert "primary_implementation_plan" not in schemas, (
            "active_releases.json must not contain primary_implementation_plan "
            "in schemas"
        )


# =========================================================================
# App Code (Criteria 17-18)
# =========================================================================

class TestAppCode:
    """Verify handler registry and UI after consolidation."""

    def test_c17_no_ipp_handler_in_registry(self):
        """C17: No handler registration for primary_implementation_plan
        in registry.py."""
        content = REGISTRY_PY.read_text()
        assert "primary_implementation_plan" not in content, (
            "registry.py must not register a handler for "
            "primary_implementation_plan"
        )

    def test_c18_no_ipp_in_doc_node_display_names(self):
        """C18: DocumentNode.jsx has no primary_implementation_plan
        in display names."""
        content = DOC_NODE_JSX.read_text()
        assert "primary_implementation_plan" not in content, (
            "DocumentNode.jsx must not reference primary_implementation_plan "
            "in DOC_TYPE_DISPLAY_NAMES"
        )


# =========================================================================
# Schema (Criteria 19-20)
# =========================================================================

class TestSchema:
    """Verify unified IP schema after consolidation."""

    def test_c19_ip_schema_has_plan_summary(self):
        """C19: IP output schema has plan_summary (not epic_set_summary)."""
        schema = _load_json(IP_RELEASE / "schemas" / "output.schema.json")
        props = schema.get("properties", {})
        assert "plan_summary" in props, (
            "IP output schema must have plan_summary field"
        )
        assert "epic_set_summary" not in props, (
            "IP output schema must not have epic_set_summary field "
            "(renamed to plan_summary)"
        )

    def test_c20_ip_schema_has_candidate_work_packages(self):
        """C20: IP output schema has candidate_work_packages section."""
        schema = _load_json(IP_RELEASE / "schemas" / "output.schema.json")
        props = schema.get("properties", {})
        assert "candidate_work_packages" in props or "work_package_candidates" in props, (
            "IP output schema must have candidate_work_packages (or "
            "work_package_candidates) section for advisory WP candidates"
        )


# =========================================================================
# Audit (Criterion 21)
# =========================================================================

class TestAudit:
    """Verify prompt audit report exists."""

    def test_c21_prompt_audit_report_exists(self):
        """C21: Prompt audit report exists at
        docs/audits/WS-PIPELINE-001-prompt-audit.md."""
        assert AUDIT_REPORT.exists(), (
            "Prompt audit report must exist at "
            "docs/audits/WS-PIPELINE-001-prompt-audit.md"
        )
