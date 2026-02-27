"""
Tests for Implementation Plan v3 schema contract.

Updated for v3: IP produces candidate Work Packages (WPC-###), not committed WPs.
Reconciliation, governance pinning, and transformation are Work Binder concerns.

Test groups:
  C1: Schema defines work_package_candidates
  C2: Candidate structure (candidate_id, dependencies, definition_of_done)
  C3: Risk summary references candidates by WPC-### ID
  C4: Schema excludes committed-WP fields (no reconciliation, no governance_pins)
  C5: Transform enrichment
  C6: Validation against v3 schema
"""

import pytest

from app.config.package_loader import get_package_loader
from app.domain.handlers.implementation_plan_handler import (
    ImplementationPlanHandler,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return ImplementationPlanHandler()


@pytest.fixture
def ipf_package():
    """Return the combine-config package for implementation_plan."""
    return get_package_loader().get_document_type("implementation_plan")


@pytest.fixture
def ipf_schema(ipf_package):
    """Return the output schema from combine-config."""
    schema = ipf_package.get_schema()
    assert schema is not None, "implementation_plan schema not found in combine-config"
    return schema


@pytest.fixture
def ipf_data():
    """
    Representative v3 IP output with candidate Work Packages.

    Scenarios covered:
    - WPC-001: standalone candidate (no dependencies)
    - WPC-002: depends on WPC-001
    - WPC-003: depends on external prerequisite
    - WPC-004: depends on WPC-001 and WPC-002
    """
    return {
        "meta": {
            "schema_version": "3.0",
            "artifact_id": "test-ip-001",
            "created_at": "2026-01-01T00:00:00Z",
            "source": "human",
        },
        "plan_summary": {
            "overall_intent": "Build The Combine document pipeline",
            "mvp_definition": "Core document types processable end-to-end",
            "key_constraints": ["Stateless LLM execution", "All state changes traceable"],
            "sequencing_rationale": "Foundation first, then pipeline, then orchestration",
        },
        "work_package_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "Document Type Registry",
                "rationale": "Foundation for all document types",
                "scope_in": ["Handler registration", "Schema validation"],
                "scope_out": ["UI rendering"],
                "dependencies": [],
                "definition_of_done": ["All seed types registered", "Validation enforced"],
            },
            {
                "candidate_id": "WPC-002",
                "title": "LLM Client Integration",
                "rationale": "Stateless LLM invocation layer",
                "scope_in": ["API client", "Token management"],
                "scope_out": ["Conversation history"],
                "dependencies": [
                    {
                        "depends_on_candidate_id": "WPC-001",
                        "dependency_type": "must_complete_first",
                        "notes": "Need registry before LLM calls",
                    }
                ],
                "definition_of_done": ["LLM calls succeed", "Token usage tracked"],
            },
            {
                "candidate_id": "WPC-003",
                "title": "External Auth Integration",
                "rationale": "SSO and OAuth support",
                "scope_in": ["OAuth flow", "Token refresh"],
                "scope_out": ["Custom auth providers"],
                "dependencies": [
                    {
                        "depends_on_external": "SSO requirements clarified by security team",
                        "dependency_type": "must_complete_first",
                        "notes": "Cannot start until security review complete",
                    }
                ],
                "definition_of_done": ["OAuth login functional", "Token refresh works"],
            },
            {
                "candidate_id": "WPC-004",
                "title": "Workflow Orchestration Engine",
                "rationale": "POW and DCW execution",
                "scope_in": ["POW sequencing", "DCW gate execution"],
                "scope_out": ["Custom workflow DSL"],
                "dependencies": [
                    {
                        "depends_on_candidate_id": "WPC-001",
                        "dependency_type": "must_complete_first",
                        "notes": "Registry must exist",
                    },
                    {
                        "depends_on_candidate_id": "WPC-002",
                        "dependency_type": "must_complete_first",
                        "notes": "LLM client needed for gate execution",
                    },
                ],
                "definition_of_done": ["POW executes", "DCW gates validate"],
                "sequencing_hint": 4,
                "notes_for_work_binder": "Consider splitting orchestration and gate execution during TA review",
            },
        ],
        "cross_cutting_concerns": ["Stateless execution invariant"],
        "risk_summary": [
            {
                "risk": "LLM API rate limits may throttle pipeline throughput",
                "affected_candidates": ["WPC-002", "WPC-004"],
                "overall_impact": "medium",
                "mitigation_strategy": "Implement exponential backoff with circuit breaker",
            },
        ],
        "recommendations_for_architecture": [
            "Evaluate whether gate execution should be synchronous or event-driven",
        ],
        "open_questions": [
            {
                "question": "What is the expected document volume per day?",
                "why_it_matters": "Affects storage and LLM cost projections",
                "who_needs_to_answer": "Product owner",
            },
        ],
    }


# =========================================================================
# C1 -- Schema defines work_package_candidates
# =========================================================================


class TestC1SchemaStructure:
    def test_required_inputs_include_project_discovery(self, ipf_package):
        """IP requires project_discovery."""
        assert "project_discovery" in ipf_package.required_inputs

    def test_schema_has_work_package_candidates(self, ipf_schema):
        assert "work_package_candidates" in ipf_schema["properties"]

    def test_schema_requires_work_package_candidates(self, ipf_schema):
        assert "work_package_candidates" in ipf_schema["required"]

    def test_schema_has_no_epics_property(self, ipf_schema):
        assert "epics" not in ipf_schema.get("properties", {})

    def test_schema_version_is_3(self, ipf_schema):
        meta_props = ipf_schema["properties"]["meta"]["properties"]
        assert meta_props["schema_version"]["const"] == "3.0"


# =========================================================================
# C2 -- Candidate structure
# =========================================================================


class TestC2CandidateStructure:
    def test_data_has_4_candidates(self, ipf_data):
        assert len(ipf_data["work_package_candidates"]) == 4

    def test_each_candidate_has_unique_id(self, ipf_data):
        ids = [c["candidate_id"] for c in ipf_data["work_package_candidates"]]
        assert len(ids) == len(set(ids))

    def test_each_candidate_has_required_fields(self, ipf_data):
        required = [
            "candidate_id", "title", "rationale", "scope_in", "scope_out",
            "dependencies", "definition_of_done",
        ]
        for c in ipf_data["work_package_candidates"]:
            for field in required:
                assert field in c, f"Candidate '{c['candidate_id']}' missing '{field}'"

    def test_candidate_id_format(self, ipf_data):
        import re
        for c in ipf_data["work_package_candidates"]:
            assert re.match(r"^WPC-[0-9]{3}$", c["candidate_id"]), (
                f"candidate_id '{c['candidate_id']}' does not match WPC-### format"
            )

    def test_dependency_references_valid_candidates_or_external(self, ipf_data):
        candidate_ids = {c["candidate_id"] for c in ipf_data["work_package_candidates"]}
        for c in ipf_data["work_package_candidates"]:
            for dep in c["dependencies"]:
                if "depends_on_candidate_id" in dep:
                    assert dep["depends_on_candidate_id"] in candidate_ids, (
                        f"Dependency '{dep['depends_on_candidate_id']}' not found in candidates"
                    )
                else:
                    assert "depends_on_external" in dep, (
                        f"Dependency in '{c['candidate_id']}' has neither candidate nor external ref"
                    )


# =========================================================================
# C3 -- Risk summary references candidates
# =========================================================================


class TestC3RiskSummary:
    def test_risk_summary_exists(self, ipf_data):
        assert "risk_summary" in ipf_data
        assert len(ipf_data["risk_summary"]) >= 1

    def test_risk_affected_candidates_are_valid(self, ipf_data):
        candidate_ids = {c["candidate_id"] for c in ipf_data["work_package_candidates"]}
        for risk in ipf_data["risk_summary"]:
            for cid in risk["affected_candidates"]:
                assert cid in candidate_ids, (
                    f"Risk references '{cid}' which is not a valid candidate"
                )


# =========================================================================
# C4 -- Schema excludes committed-WP fields
# =========================================================================


class TestC4NoCommittedWPFields:
    def test_no_candidate_reconciliation_in_schema(self, ipf_schema):
        assert "candidate_reconciliation" not in ipf_schema["properties"]

    def test_no_work_packages_alias_in_schema(self, ipf_schema):
        """v3 schema should not have the deprecated work_packages alias."""
        assert "work_packages" not in ipf_schema["properties"]

    def test_candidate_def_has_no_governance_pins(self, ipf_schema):
        """Candidates should not have governance_pins (Work Binder concern)."""
        wp_ref = ipf_schema["properties"]["work_package_candidates"]["items"]
        if "$ref" in wp_ref:
            ref_name = wp_ref["$ref"].split("/")[-1]
            wp_props = ipf_schema["definitions"][ref_name]["properties"]
        else:
            wp_props = wp_ref["properties"]
        assert "governance_pins" not in wp_props
        assert "transformation" not in wp_props
        assert "source_candidate_ids" not in wp_props


# =========================================================================
# C5 -- Transform enrichment
# =========================================================================


class TestC5TransformEnrichment:
    def test_transform_adds_wp_count(self, handler, ipf_data):
        result = handler.transform(ipf_data)
        assert result["wp_count"] == 4

    def test_get_child_documents_returns_empty(self, handler, ipf_data):
        """WP creation is manual -- handler returns empty."""
        children = handler.get_child_documents(ipf_data, "Test Plan")
        assert children == []

    def test_transform_adds_associated_risks(self, handler, ipf_data):
        """Transform injects associated_risks from risk_summary."""
        result = handler.transform(ipf_data)
        # WPC-002 should have the LLM rate limit risk
        wpc_002 = [c for c in result["work_package_candidates"] if c["candidate_id"] == "WPC-002"][0]
        assert len(wpc_002["associated_risks"]) == 1
        assert "rate limit" in wpc_002["associated_risks"][0].lower()

    def test_transform_empty_candidates(self, handler):
        data = {"work_package_candidates": []}
        result = handler.transform(data)
        assert result["wp_count"] == 0


# =========================================================================
# C6 -- Validation against v3 schema
# =========================================================================


class TestC6Validation:
    def test_validation_passes(self, handler, ipf_schema, ipf_data):
        is_valid, errors = handler.validate(ipf_data, ipf_schema)
        assert is_valid, f"Validation errors: {errors}"
