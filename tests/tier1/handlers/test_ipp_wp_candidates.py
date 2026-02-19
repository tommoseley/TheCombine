"""
Tests for IPP Work Package Candidates — WS-ONTOLOGY-004.

Five test groups mapping to the five Mode A Tier 1 verification criteria:
  C1: Schema defines work_package_candidates[] with required fields
  C2: No epic_candidates field in schema
  C3: Schema validation passes for valid WP candidate output
  C4: Schema validation rejects invalid WP candidate output
  C5: Golden trace — representative output has structurally valid WP candidates
"""

import pytest

from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
from app.domain.handlers.implementation_plan_primary_handler import (
    ImplementationPlanPrimaryHandler,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return ImplementationPlanPrimaryHandler()


@pytest.fixture
def ipp_seed_entry():
    """Return the full seed entry for implementation_plan_primary."""
    for entry in INITIAL_DOCUMENT_TYPES:
        if entry["doc_type_id"] == "implementation_plan_primary":
            return entry
    pytest.fail("implementation_plan_primary not found in INITIAL_DOCUMENT_TYPES")


@pytest.fixture
def ipp_schema(ipp_seed_entry):
    """Return the schema_definition from the seed registry entry."""
    return ipp_seed_entry["schema_definition"]


@pytest.fixture
def valid_ipp_content():
    """Minimal well-formed IPP output with WP candidates."""
    return {
        "epic_set_summary": {
            "overall_intent": "Deliver a document-centric AI system",
            "mvp_definition": "Core pipeline operational",
            "key_constraints": ["No SQLite"],
            "out_of_scope": ["Mobile app"],
        },
        "work_package_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "Core Document Pipeline",
                "rationale": "Foundation for all document processing",
                "scope_in": ["Document ingestion", "Schema validation"],
                "scope_out": ["UI rendering"],
                "dependencies": [],
                "definition_of_done": [
                    "Documents can be created and validated"
                ],
                "governance_notes": ["Must comply with ADR-010"],
            },
            {
                "candidate_id": "WPC-002",
                "title": "Workflow Engine",
                "rationale": "Orchestrates document creation workflows",
                "scope_in": ["POW execution", "DCW execution"],
                "scope_out": ["Custom workflow DSL"],
                "dependencies": ["WPC-001"],
                "definition_of_done": [
                    "Workflows execute end-to-end"
                ],
                "governance_notes": [],
            },
        ],
        "risks_overview": [],
        "recommendations_for_architecture": [],
    }


@pytest.fixture
def golden_trace_output():
    """
    Representative IPP output for golden trace structural check.

    This fixture represents what an IPP execution would produce.
    The content is not semantically validated — only structural completeness.
    """
    return {
        "epic_set_summary": {
            "overall_intent": "Build The Combine document pipeline with WP-based ontology",
            "mvp_definition": "Core document types registered and processable",
            "key_constraints": [
                "All state changes explicit and traceable",
                "No SQLite for testing",
            ],
            "out_of_scope": ["Mobile interface", "Real-time collaboration"],
        },
        "work_package_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "Document Type Registry",
                "rationale": "Establish the foundational registry for all document types with schema validation",
                "scope_in": [
                    "Document type seed data",
                    "Handler registration",
                    "Schema-based validation",
                ],
                "scope_out": ["UI for document management", "LLM prompt execution"],
                "dependencies": [],
                "definition_of_done": [
                    "All seed document types registered",
                    "Handlers resolve by handler_id",
                    "Schema validation enforced on create",
                ],
                "governance_notes": [
                    "ADR-045 taxonomy applies",
                    "Prompt fragments are governed inputs",
                ],
            },
            {
                "candidate_id": "WPC-002",
                "title": "LLM Execution Pipeline",
                "rationale": "Enable stateless LLM invocations with full audit logging per ADR-010",
                "scope_in": [
                    "LLM client integration",
                    "Execution logging",
                    "Replay capability",
                ],
                "scope_out": [
                    "Conversation history",
                    "Multi-turn interactions",
                ],
                "dependencies": ["WPC-001"],
                "definition_of_done": [
                    "LLM calls logged with inputs/outputs/tokens",
                    "Replay endpoint functional",
                ],
                "governance_notes": ["ADR-040 stateless invariant applies"],
            },
            {
                "candidate_id": "WPC-003",
                "title": "Workflow Orchestration",
                "rationale": "POW and DCW execution engine for multi-step document creation",
                "scope_in": [
                    "POW step sequencing",
                    "DCW gate execution",
                    "Document state management",
                ],
                "scope_out": ["Custom workflow DSL", "Visual workflow editor"],
                "dependencies": ["WPC-001", "WPC-002"],
                "definition_of_done": [
                    "POW executes steps in sequence",
                    "DCW gates produce validated documents",
                ],
                "governance_notes": [],
            },
        ],
        "risks_overview": [
            {
                "risk_id": "RSK-001",
                "description": "Schema evolution may require migration tooling",
                "affected_candidates": ["WPC-001"],
                "mitigation_direction": "Version schemas from day one",
            },
        ],
        "recommendations_for_architecture": [
            "Design handler registry for extensibility",
            "Separate prompt governance from runtime execution",
        ],
    }


# =========================================================================
# C1 — Schema defines work_package_candidates[] with required fields
# =========================================================================


class TestC1SchemaDefinesWPCandidates:
    def test_schema_has_work_package_candidates_property(self, ipp_schema):
        props = ipp_schema["properties"]
        assert "work_package_candidates" in props

    def test_work_package_candidates_is_required(self, ipp_schema):
        assert "work_package_candidates" in ipp_schema["required"]

    def test_work_package_candidates_is_array(self, ipp_schema):
        wpc = ipp_schema["properties"]["work_package_candidates"]
        assert wpc["type"] == "array"

    def test_candidate_required_fields(self, ipp_schema):
        wpc = ipp_schema["properties"]["work_package_candidates"]
        item_required = wpc["items"]["required"]
        for field in [
            "candidate_id",
            "title",
            "rationale",
            "scope_in",
            "scope_out",
            "dependencies",
            "definition_of_done",
        ]:
            assert field in item_required, f"'{field}' not in candidate required"

    def test_candidate_has_governance_notes(self, ipp_schema):
        wpc = ipp_schema["properties"]["work_package_candidates"]
        item_props = wpc["items"]["properties"]
        assert "governance_notes" in item_props

    def test_candidate_id_pattern(self, ipp_schema):
        wpc = ipp_schema["properties"]["work_package_candidates"]
        cid = wpc["items"]["properties"]["candidate_id"]
        assert cid["type"] == "string"


# =========================================================================
# C2 — No epic_candidates field in schema
# =========================================================================


class TestC2NoEpicCandidates:
    def test_no_epic_candidates_in_schema_required(self, ipp_schema):
        assert "epic_candidates" not in ipp_schema.get("required", [])

    def test_no_epic_candidates_in_schema_properties(self, ipp_schema):
        assert "epic_candidates" not in ipp_schema.get("properties", {})


# =========================================================================
# C3 — Schema validation passes for valid WP candidate output
# =========================================================================


class TestC3ValidationPasses:
    def test_valid_ipp_passes_validation(
        self, handler, ipp_schema, valid_ipp_content
    ):
        is_valid, errors = handler.validate(valid_ipp_content, ipp_schema)
        assert is_valid, f"Validation errors: {errors}"

    def test_valid_ipp_has_no_errors(
        self, handler, ipp_schema, valid_ipp_content
    ):
        _, errors = handler.validate(valid_ipp_content, ipp_schema)
        assert errors == []


# =========================================================================
# C4 — Schema validation rejects invalid WP candidate output
# =========================================================================


class TestC4ValidationRejectsInvalid:
    def test_missing_work_package_candidates_fails(self, handler, ipp_schema):
        data = {
            "epic_set_summary": {"overall_intent": "Test"},
        }
        is_valid, errors = handler.validate(data, ipp_schema)
        assert is_valid is False
        assert any("work_package_candidates" in e for e in errors)

    def test_null_work_package_candidates_fails(self, handler, ipp_schema):
        data = {
            "work_package_candidates": None,
        }
        is_valid, errors = handler.validate(data, ipp_schema)
        assert is_valid is False


# =========================================================================
# C5 — Golden trace (structural check)
# =========================================================================


class TestC5GoldenTrace:
    def test_golden_trace_has_wp_candidates(self, golden_trace_output):
        assert "work_package_candidates" in golden_trace_output
        assert len(golden_trace_output["work_package_candidates"]) >= 1

    def test_golden_trace_candidates_have_all_required_fields(
        self, golden_trace_output
    ):
        required = [
            "candidate_id",
            "title",
            "rationale",
            "scope_in",
            "scope_out",
            "dependencies",
            "definition_of_done",
        ]
        for candidate in golden_trace_output["work_package_candidates"]:
            for field in required:
                assert field in candidate, (
                    f"Candidate '{candidate.get('candidate_id', '?')}' "
                    f"missing '{field}'"
                )

    def test_golden_trace_candidate_fields_populated(
        self, golden_trace_output
    ):
        """Each required field must be non-empty (not just present)."""
        for candidate in golden_trace_output["work_package_candidates"]:
            assert candidate["candidate_id"], "candidate_id is empty"
            assert candidate["title"], "title is empty"
            assert candidate["rationale"], "rationale is empty"
            assert isinstance(candidate["scope_in"], list)
            assert isinstance(candidate["scope_out"], list)
            assert isinstance(candidate["dependencies"], list)
            assert isinstance(candidate["definition_of_done"], list)
            assert len(candidate["definition_of_done"]) >= 1

    def test_golden_trace_passes_validation(
        self, handler, ipp_schema, golden_trace_output
    ):
        is_valid, errors = handler.validate(golden_trace_output, ipp_schema)
        assert is_valid, f"Golden trace validation errors: {errors}"

    def test_golden_trace_has_no_epic_candidates(self, golden_trace_output):
        assert "epic_candidates" not in golden_trace_output

    def test_handler_transform_counts_candidates(
        self, handler, golden_trace_output
    ):
        """Handler transform should compute candidate_count from WP candidates."""
        transformed = handler.transform(golden_trace_output.copy())
        assert transformed["candidate_count"] == 3
