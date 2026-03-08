"""Tier-1 contract tests for IA gate verification (ADR-054).

These tests verify that every active package.yaml IA definition has bind paths
that match the actual document content structure produced by the LLM pipeline.
When IA binds reference fields that don't exist in real content, the ia_gate
returns FAIL and the binder render returns 409.

Each test uses a representative content fixture extracted from production data.
If any IA bind path is changed in package.yaml, these tests catch mismatches
before they reach the browser.

No DB, no HTTP, no side effects.
"""
# ruff: noqa: E501

import pytest
import yaml
from pathlib import Path

from app.domain.services.ia_gate import verify_document_ia


# ---------------------------------------------------------------------------
# Fixture loader: reads IA from combine-config package.yaml
# ---------------------------------------------------------------------------

_CONFIG_ROOT = Path(__file__).resolve().parents[3] / "combine-config"
_ACTIVE_RELEASES_PATH = _CONFIG_ROOT / "_active" / "active_releases.json"


def _load_ia(doc_type_id: str, version: str) -> dict | None:
    """Load information_architecture from a package.yaml."""
    pkg_path = (
        _CONFIG_ROOT / "document_types" / doc_type_id
        / "releases" / version / "package.yaml"
    )
    if not pkg_path.exists():
        return None
    with open(pkg_path) as f:
        pkg = yaml.safe_load(f)
    return pkg.get("information_architecture")


def _load_active_releases() -> dict:
    """Load active_releases.json."""
    import json
    with open(_ACTIVE_RELEASES_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Representative content fixtures (from production DB, 2026-03-07)
#
# These are the REAL top-level keys produced by the LLM pipeline.
# If the LLM output schema changes, update these fixtures.
# ---------------------------------------------------------------------------

CONCIERGE_INTAKE_CONTENT = {
    "outcome": {
        "status": "qualified",
        "rationale": "Request is straightforward.",
        "next_action": "Proceed to implementation.",
    },
    "summary": {
        "description": "The user wants to build a CLI app.",
        "user_statement": "I want to build a CLI Hello World app",
    },
    "version": "1.0",
    "open_gaps": {
        "questions": ["Which language?"],
        "missing_context": ["Platform preferences"],
        "assumptions_made": ["Standalone executable"],
    },
    "constraints": {
        "explicit": ["Must be CLI", "Must output Hello World"],
        "inferred": [],
        "none_stated": False,
    },
    "project_name": "CLI Hello World App",
    "project_type": {
        "category": "produce_output",
        "rationale": "User wants a deliverable.",
        "confidence": "high",
    },
    "document_type": "concierge_intake_document",
}

PROJECT_DISCOVERY_CONTENT = {
    "meta": {"version": "1.0"},
    "project_name": "CLI Hello World App",
    "preliminary_summary": {
        "problem_understanding": "Build a CLI app.",
        "architectural_intent": "Simple script.",
        "proposed_system_shape": "Single file.",
    },
    "unknowns": [
        {"id": "U-001", "question": "Language?", "why_it_matters": "Affects tooling",
         "impact_if_unresolved": "Can't start"},
    ],
    "assumptions": [
        {"id": "A-001", "assumption": "Python", "confidence": "high",
         "validation_approach": "Confirm with user"},
    ],
    "known_constraints": [
        {"id": "C-001", "constraint": "CLI only", "source": "user", "impact": "No GUI"},
    ],
    "risks": [
        {"id": "R-001", "risk": "None", "likelihood": "low", "impact": "low",
         "mitigation": "N/A"},
    ],
    "mvp_guardrails": ["Keep it simple"],
    "early_decision_points": [
        {"id": "D-001", "decision": "Use Python", "options": ["Python", "Go"],
         "recommendation": "Python"},
    ],
    "stakeholder_questions": [
        {"id": "SQ-001", "question": "Target platform?", "for_stakeholder": "User",
         "priority": "high"},
    ],
    "recommendations_for_pm": ["Start with Python script"],
}

TECHNICAL_ARCHITECTURE_CONTENT = {
    "meta": {"version": "1.0"},
    "architecture_summary": {
        "title": "CLI Architecture",
        "style": "Script",
        "key_decisions": ["Python", "Single file"],
    },
    "components": [{"name": "main", "purpose": "Entry point"}],
    "data_models": [{"name": "Config", "fields": []}],
    "api_interfaces": [{"name": "CLI", "type": "command-line"}],
    "quality_attributes": {
        "performance": "Fast startup",
        "security": "No secrets",
        "scalability": "N/A",
        "maintainability": "Simple code",
        "observability": "stdout",
    },
    "workflows": [{"name": "Run", "steps": ["Parse args", "Print"]}],
    "risks": [{"id": "R-001", "risk": "None"}],
    "open_questions": [{"id": "Q-001", "question": "None"}],
    "mvp_scope": {
        "included": ["Hello World output"],
        "deferred": ["Config files"],
    },
}

IMPLEMENTATION_PLAN_CONTENT = {
    "meta": {"version": "1.0"},
    "plan_summary": {
        "overall_intent": "Build a CLI app.",
        "mvp_definition": "Prints Hello World.",
        "key_constraints": ["CLI only"],
        "sequencing_rationale": "Linear.",
        "assumptions": ["Python available"],
        "out_of_scope": ["GUI"],
    },
    "work_package_candidates": [
        {"wpc_id": "WPC-001", "title": "Core CLI", "scope_summary": "Main script"},
    ],
    "risk_summary": [{"id": "R-001", "risk": "None"}],
    "cross_cutting_concerns": ["Testing"],
    "recommendations_for_architecture": ["Keep simple"],
    "open_questions": [{"id": "Q-001", "question": "None"}],
}

WORK_PACKAGE_CONTENT = {
    "wp_id": "WP-001",
    "title": "Core CLI Implementation",
    "rationale": "Implements the CLI.",
    "state": "draft",
    "scope_in": ["Python script", "Main function"],
    "scope_out": ["GUI", "Config"],
    "definition_of_done": ["Script runs", "Tests pass"],
    "dependencies": [],
    "governance_pins": {
        "ta_version_id": "TA-001-v1",
        "adr_refs": [],
        "policy_refs": ["POL-CODE-001"],
    },
    "ws_index": [
        {"ws_id": "WS-001", "order_key": "a0"},
    ],
    "revision": {
        "edition": 1,
        "updated_at": "2026-03-07T12:00:00Z",
        "updated_by": "system",
    },
    "source_candidate_ids": ["WPC-001"],
    "transformation": "kept",
    "transformation_notes": "",
    "_lineage": {
        "parent_document_type": "implementation_plan",
        "parent_execution_id": None,
        "source_candidate_ids": ["WPC-001"],
        "transformation": "kept",
        "transformation_notes": "",
    },
}

# Work package with MINIMAL content (newly promoted, sparse)
WORK_PACKAGE_MINIMAL_CONTENT = {
    "wp_id": "WP-002",
    "title": "Packaging",
    "rationale": "Package the app.",
    "state": "draft",
    "scope_in": ["Packaging"],
    "scope_out": [],
    "definition_of_done": ["Package works"],
    "dependencies": [],
    "governance_pins": {
        "ta_version_id": None,
        "adr_refs": [],
        "policy_refs": [],
    },
    "ws_index": [],
    "revision": {"edition": 1, "updated_at": "2026-03-07T12:00:00Z", "updated_by": "system"},
    "source_candidate_ids": [],
    "transformation": "kept",
    "transformation_notes": "",
    "_lineage": {
        "parent_document_type": "implementation_plan",
        "parent_execution_id": None,
        "source_candidate_ids": [],
        "transformation": "kept",
        "transformation_notes": "",
    },
}


# ---------------------------------------------------------------------------
# Doc types WITHOUT IA — should always SKIP
# ---------------------------------------------------------------------------

WORK_PACKAGE_CANDIDATE_CONTENT = {
    "wpc_id": "WPC-001",
    "title": "Core CLI",
    "rationale": "Main package",
    "scope_summary": "Implements the script",
    "source_ip_id": "IP-001",
    "source_ip_version": 1,
    "frozen_at": "2026-03-07T12:00:00Z",
    "frozen_by": "system",
}

WORK_STATEMENT_CONTENT = {
    "ws_id": "WS-001",
    "title": "Create Script",
    "objective": "Set up file structure",
    "state": "draft",
    "parent_wp_id": "WP-001",
    "scope_in": ["File structure"],
    "scope_out": ["Tests"],
    "procedure": ["Create file", "Add imports"],
    "verification_criteria": ["File exists"],
    "prohibited_actions": ["Don't modify other files"],
    "allowed_paths": ["src/"],
    "governance_pins": {"ta_version_id": None, "adr_refs": [], "policy_refs": []},
    "revision": {"edition": 1, "updated_at": "2026-03-07T12:00:00Z", "updated_by": "system"},
    "order_key": "a0",
}


# ---------------------------------------------------------------------------
# Map doc_type -> (content, expected_status)
# ---------------------------------------------------------------------------

_DOC_TYPE_FIXTURES = {
    "concierge_intake": ("1.0.0", CONCIERGE_INTAKE_CONTENT),
    "project_discovery": ("1.4.0", PROJECT_DISCOVERY_CONTENT),
    "technical_architecture": ("1.0.0", TECHNICAL_ARCHITECTURE_CONTENT),
    "implementation_plan": ("1.0.0", IMPLEMENTATION_PLAN_CONTENT),
    "work_package": ("1.1.0", WORK_PACKAGE_CONTENT),
}

_NO_IA_FIXTURES = {
    "work_package_candidate": ("1.0.0", WORK_PACKAGE_CANDIDATE_CONTENT),
    "work_statement": ("1.1.0", WORK_STATEMENT_CONTENT),
    "execution_plan": ("1.0.0", {}),
    "pipeline_run": ("1.0.0", {}),
    "intent_packet": ("1.0.0", {}),
}


# ===========================================================================
# Tests: IA gate passes for all doc types with representative content
# ===========================================================================

class TestIAGatePassesWithProductionContent:
    """Every active doc type with IA must PASS the gate using production content shapes.

    This is the critical contract test. If this fails, binder render will 409.
    """

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_ia_gate_passes(self, doc_type_id):
        version, content = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        assert ia is not None, f"No IA found for {doc_type_id} v{version}"

        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS", (
            f"{doc_type_id} FAILED IA gate: coverage={result['coverage']}, "
            f"failures={result['failures']}"
        )

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_ia_gate_100_percent_coverage(self, doc_type_id):
        """Production content should achieve 100% coverage (all fields present)."""
        version, content = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        result = verify_document_ia(content, ia)
        assert result["coverage"] == 1.0, (
            f"{doc_type_id} coverage={result['coverage']}, "
            f"warnings={result.get('warnings', [])}"
        )


class TestIAGateSkipsWithoutIA:
    """Doc types without IA should SKIP, never FAIL."""

    @pytest.mark.parametrize("doc_type_id", list(_NO_IA_FIXTURES.keys()))
    def test_ia_gate_skips(self, doc_type_id):
        version, content = _NO_IA_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        result = verify_document_ia(content, ia)
        assert result["status"] in ("SKIP", "PASS"), (
            f"{doc_type_id} unexpectedly FAILED: {result}"
        )


# ===========================================================================
# Tests: IA bind paths exist in content
# ===========================================================================

class TestIABindPathsExistInContent:
    """Every IA bind path must resolve to a non-None value in the fixture content.

    This catches the exact bug: IA declared `captured_intent` but content had
    `summary.description`. Field-level verification.
    """

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_all_bind_paths_resolve(self, doc_type_id):
        version, content = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        assert ia is not None

        missing = []
        for section in ia.get("sections", []):
            for bind in section.get("binds", []):
                path = bind.get("path", "")
                if not path:
                    continue
                value = _resolve_path(content, path)
                if value is None:
                    missing.append(f"{section['id']}.{path}")

        assert not missing, (
            f"{doc_type_id}: IA bind paths not found in content: {missing}"
        )


def _resolve_path(content: dict, path: str):
    """Mirror of ia_gate._resolve_path for test verification."""
    if not path:
        return None
    if "." not in path:
        return content.get(path)
    parts = path.split(".")
    current = content
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ===========================================================================
# Tests: Sparse / minimal content still passes threshold
# ===========================================================================

class TestIAGateWithSparseContent:
    """Documents with sparse content (newly created) must still pass the 50% threshold."""

    def test_work_package_minimal_passes(self):
        """A newly promoted WP with minimal content should PASS."""
        ia = _load_ia("work_package", "1.1.0")
        result = verify_document_ia(WORK_PACKAGE_MINIMAL_CONTENT, ia)
        assert result["status"] == "PASS", (
            f"Minimal WP FAILED: coverage={result['coverage']}, "
            f"failures={result['failures']}"
        )

    def test_concierge_intake_without_optional_fields_passes(self):
        """CI without version/document_type (non-IA fields) still passes."""
        content = {
            "outcome": {"status": "qualified", "rationale": "OK", "next_action": "Go"},
            "summary": {"description": "Build an app.", "user_statement": "I want an app"},
            "project_type": {"category": "greenfield", "rationale": "New project"},
            "constraints": {"explicit": ["Must work"], "inferred": []},
            "open_gaps": {"questions": [], "missing_context": [], "assumptions_made": []},
        }
        ia = _load_ia("concierge_intake", "1.0.0")
        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS"
        assert result["coverage"] == 1.0


# ===========================================================================
# Tests: IA config structural validation
# ===========================================================================

class TestIAConfigStructure:
    """Validate that package.yaml IA sections are well-formed."""

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_ia_has_version(self, doc_type_id):
        version, _ = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        assert ia is not None
        assert "version" in ia, f"{doc_type_id}: IA missing 'version'"
        assert ia["version"] == 2, f"{doc_type_id}: expected IA version 2"

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_ia_sections_have_required_fields(self, doc_type_id):
        version, _ = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        for section in ia.get("sections", []):
            assert "id" in section, f"{doc_type_id}: section missing 'id'"
            assert "label" in section, f"{doc_type_id}: section missing 'label'"
            assert "binds" in section, f"{doc_type_id}: section {section['id']} missing 'binds'"
            for bind in section["binds"]:
                assert "path" in bind, (
                    f"{doc_type_id}: bind in {section['id']} missing 'path'"
                )
                assert "render_as" in bind, (
                    f"{doc_type_id}: bind {bind.get('path')} in {section['id']} missing 'render_as'"
                )

    @pytest.mark.parametrize("doc_type_id", list(_DOC_TYPE_FIXTURES.keys()))
    def test_ia_section_ids_unique(self, doc_type_id):
        version, _ = _DOC_TYPE_FIXTURES[doc_type_id]
        ia = _load_ia(doc_type_id, version)
        ids = [s["id"] for s in ia.get("sections", [])]
        assert len(ids) == len(set(ids)), (
            f"{doc_type_id}: duplicate section IDs: {ids}"
        )


# ===========================================================================
# Tests: Binder render integration (pure function, no DB)
# ===========================================================================

class TestBinderIAGateIntegration:
    """End-to-end: a full binder with all doc types must pass IA gate for every doc.

    This simulates what the binder render endpoint does before calling
    render_project_binder().
    """

    def test_full_binder_all_docs_pass_ia_gate(self):
        """Every document in a realistic binder passes verify_document_ia."""
        releases = _load_active_releases()
        docs = [
            ("concierge_intake", CONCIERGE_INTAKE_CONTENT),
            ("project_discovery", PROJECT_DISCOVERY_CONTENT),
            ("implementation_plan", IMPLEMENTATION_PLAN_CONTENT),
            ("technical_architecture", TECHNICAL_ARCHITECTURE_CONTENT),
            ("work_package", WORK_PACKAGE_CONTENT),
            ("work_package", WORK_PACKAGE_MINIMAL_CONTENT),
            ("work_package_candidate", WORK_PACKAGE_CANDIDATE_CONTENT),
            ("work_statement", WORK_STATEMENT_CONTENT),
        ]

        failures = []
        for doc_type_id, content in docs:
            version = releases.get(doc_type_id, "1.0.0")
            ia = _load_ia(doc_type_id, version)
            result = verify_document_ia(content, ia)
            if result["status"] == "FAIL":
                failures.append(
                    f"{doc_type_id}: coverage={result['coverage']}, "
                    f"missing={result['failures']}"
                )

        assert not failures, (
            f"Binder IA gate would return 409. Failures:\n" +
            "\n".join(f"  - {f}" for f in failures)
        )

    def test_binder_renders_without_error(self):
        """render_project_binder completes without exception for all doc types."""
        from app.domain.services.binder_renderer import render_project_binder

        releases = _load_active_releases()
        binder_docs = []
        for doc_type_id, content in [
            ("concierge_intake", CONCIERGE_INTAKE_CONTENT),
            ("project_discovery", PROJECT_DISCOVERY_CONTENT),
            ("implementation_plan", IMPLEMENTATION_PLAN_CONTENT),
            ("technical_architecture", TECHNICAL_ARCHITECTURE_CONTENT),
            ("work_package", WORK_PACKAGE_CONTENT),
        ]:
            version = releases.get(doc_type_id, "1.0.0")
            ia = _load_ia(doc_type_id, version)
            binder_docs.append({
                "display_id": f"{doc_type_id[:2].upper()}-001",
                "doc_type_id": doc_type_id,
                "title": f"Test {doc_type_id}",
                "content": content,
                "ia": ia,
            })

        md = render_project_binder(
            project_id="TEST-001",
            project_title="Test Project",
            documents=binder_docs,
            generated_at="2026-03-07T12:00:00Z",
        )
        assert "TEST-001" in md
        assert "Documents: 5" in md


# ===========================================================================
# Regression test: the exact bug that caused the 409
# ===========================================================================

class TestRegressionConciergeIntakeIAMismatch:
    """Regression: IA binds must match nested content structure, not flat schema fields.

    The bug: IA declared `captured_intent`, `gate_outcome`, `routing_rationale`,
    `conversation_summary`, `known_unknowns` — but actual content uses nested
    objects: `summary.description`, `outcome.status`, `outcome.rationale`,
    `open_gaps.questions`, `constraints.explicit`, `project_type.category`.

    Coverage dropped to 28% -> FAIL -> binder 409.
    """

    def test_ia_binds_match_nested_content_not_flat_schema(self):
        """IA must bind to what's IN the content, not what the schema says."""
        ia = _load_ia("concierge_intake", "1.0.0")
        result = verify_document_ia(CONCIERGE_INTAKE_CONTENT, ia)
        assert result["status"] == "PASS", (
            f"Concierge intake IA mismatch! coverage={result['coverage']}, "
            f"failures={result['failures']}. "
            f"IA binds must match actual nested content keys, not flat schema fields."
        )
        assert result["coverage"] == 1.0

    def test_flat_schema_fields_would_fail(self):
        """Prove that the OLD (wrong) IA binds would fail with real content."""
        wrong_ia = {
            "version": 2,
            "sections": [
                {"id": "s1", "label": "Intent", "binds": [
                    {"path": "captured_intent", "render_as": "paragraph"},
                ]},
                {"id": "s2", "label": "Outcome", "binds": [
                    {"path": "gate_outcome", "render_as": "paragraph"},
                    {"path": "routing_rationale", "render_as": "paragraph"},
                    {"path": "conversation_summary", "render_as": "paragraph"},
                ]},
                {"id": "s3", "label": "Unknowns", "binds": [
                    {"path": "known_unknowns", "render_as": "string-list"},
                ]},
            ],
        }
        result = verify_document_ia(CONCIERGE_INTAKE_CONTENT, wrong_ia)
        assert result["status"] == "FAIL", (
            "Wrong IA should FAIL — these flat field names don't exist in content"
        )
        assert result["coverage"] < 0.5


class TestRegressionWorkPackageComputedFields:
    """Regression: IA must not declare computed/handler-injected fields.

    The bug: IA declared `ws_total`, `ws_done`, `mode_b_count`, `change_summary`
    which are added by the handler's transform() at render time, not stored in
    the document content. The ia_gate runs against raw stored content, so these
    are always missing.
    """

    def test_ia_does_not_declare_computed_fields(self):
        """WP IA should not reference handler-computed fields."""
        ia = _load_ia("work_package", "1.1.0")
        all_paths = []
        for section in ia.get("sections", []):
            for bind in section.get("binds", []):
                all_paths.append(bind.get("path", ""))

        computed_fields = {"ws_total", "ws_done", "mode_b_count", "change_summary"}
        declared_computed = computed_fields & set(all_paths)
        assert not declared_computed, (
            f"WP IA declares computed fields that aren't in stored content: "
            f"{declared_computed}. These cause false warnings in the IA gate."
        )
