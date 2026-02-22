"""
Tests for IPF Work Package Reconciliation — WS-ONTOLOGY-005.

Six test groups mapping to the six Mode A Tier 1 verification criteria:
  C1: IPF accepts WP candidates as input
  C2: IPF produces committed work_packages[]
  C3: Reconciliation entries (kept/split/merged/dropped)
  C4: Bidirectional traceability
  C5: Governance pinning on committed WPs
  C6: Committed WPs instantiated as child documents via get_child_documents()
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
    Representative IPF output with committed WPs reconciled from WPC candidates.

    Scenarios covered:
    - WPC-001 kept as wp_document_registry
    - WPC-002 split into wp_llm_client and wp_execution_logging
    - WPC-003 merged with WPC-004 into wp_workflow_engine
    - WPC-005 dropped
    """
    return {
        "meta": {
            "schema_version": "1.0",
            "artifact_id": "test-ipf-001",
            "created_at": "2026-01-01T00:00:00Z",
            "source": "human",
        },
        "plan_summary": {
            "overall_intent": "Build The Combine document pipeline",
            "mvp_definition": "Core document types processable end-to-end",
            "key_constraints": ["Stateless LLM execution", "All state changes traceable"],
            "sequencing_rationale": "Foundation first, then pipeline, then orchestration",
        },
        "work_packages": [
            {
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
                "transformation": "kept",
                "source_candidate_ids": ["WPC-001"],
                "transformation_notes": "Preserved from IPP",
            },
            {
                "wp_id": "wp_llm_client",
                "title": "LLM Client Integration",
                "rationale": "Stateless LLM invocation layer",
                "scope_in": ["API client", "Token management"],
                "scope_out": ["Conversation history"],
                "dependencies": [{"wp_id": "wp_document_registry", "dependency_type": "must_complete_first"}],
                "definition_of_done": ["LLM calls succeed", "Token usage tracked"],
                "governance_pins": {
                    "ta_version_id": "ta-v1.0",
                    "adr_refs": ["ADR-040"],
                    "policy_refs": [],
                },
                "transformation": "split",
                "source_candidate_ids": ["WPC-002"],
                "transformation_notes": "Split execution pipeline into client and logging",
            },
            {
                "wp_id": "wp_execution_logging",
                "title": "LLM Execution Logging",
                "rationale": "Full audit trail per ADR-010",
                "scope_in": ["Execution logging", "Replay capability"],
                "scope_out": ["Real-time monitoring"],
                "dependencies": [{"wp_id": "wp_llm_client", "dependency_type": "must_complete_first"}],
                "definition_of_done": ["All executions logged", "Replay functional"],
                "governance_pins": {
                    "ta_version_id": "ta-v1.0",
                    "adr_refs": ["ADR-010"],
                    "policy_refs": [],
                },
                "transformation": "split",
                "source_candidate_ids": ["WPC-002"],
                "transformation_notes": "Split execution pipeline into client and logging",
            },
            {
                "wp_id": "wp_workflow_engine",
                "title": "Workflow Orchestration Engine",
                "rationale": "POW and DCW execution",
                "scope_in": ["POW sequencing", "DCW gate execution"],
                "scope_out": ["Custom workflow DSL"],
                "dependencies": [
                    {"wp_id": "wp_document_registry", "dependency_type": "must_complete_first"},
                    {"wp_id": "wp_llm_client", "dependency_type": "must_complete_first"},
                ],
                "definition_of_done": ["POW executes", "DCW gates validate"],
                "governance_pins": {
                    "ta_version_id": "ta-v1.0",
                    "adr_refs": [],
                    "policy_refs": [],
                },
                "transformation": "merged",
                "source_candidate_ids": ["WPC-003", "WPC-004"],
                "transformation_notes": "Merged orchestration and gate execution",
            },
        ],
        "candidate_reconciliation": [
            {
                "candidate_id": "WPC-001",
                "outcome": "kept",
                "resulting_wp_ids": ["wp_document_registry"],
                "notes": "Direct mapping",
            },
            {
                "candidate_id": "WPC-002",
                "outcome": "split",
                "resulting_wp_ids": ["wp_llm_client", "wp_execution_logging"],
                "notes": "Architecture review separated client from logging concerns",
            },
            {
                "candidate_id": "WPC-003",
                "outcome": "merged",
                "resulting_wp_ids": ["wp_workflow_engine"],
                "notes": "Combined with WPC-004 per architecture recommendation",
            },
            {
                "candidate_id": "WPC-004",
                "outcome": "merged",
                "resulting_wp_ids": ["wp_workflow_engine"],
                "notes": "Combined with WPC-003 per architecture recommendation",
            },
            {
                "candidate_id": "WPC-005",
                "outcome": "dropped",
                "resulting_wp_ids": [],
                "notes": "Deferred — not needed for MVP",
            },
        ],
        "cross_cutting_concerns": ["Stateless execution invariant"],
        "risk_summary": [],
    }


# =========================================================================
# C1 — IPF accepts WP candidates as input
# =========================================================================


class TestC1AcceptsWPCandidates:
    def test_required_inputs_include_ipp(self, ipf_package):
        """IPF requires primary_implementation_plan (which now emits WP candidates)."""
        assert "primary_implementation_plan" in ipf_package.required_inputs

    def test_schema_has_work_packages_property(self, ipf_schema):
        assert "work_packages" in ipf_schema["properties"]

    def test_schema_requires_work_packages(self, ipf_schema):
        assert "work_packages" in ipf_schema["required"]

    def test_schema_has_no_epics_in_required(self, ipf_schema):
        assert "epics" not in ipf_schema.get("required", [])

    def test_schema_has_no_epics_property(self, ipf_schema):
        assert "epics" not in ipf_schema.get("properties", {})


# =========================================================================
# C2 — IPF produces committed work_packages[]
# =========================================================================


class TestC2ProducesCommittedWPs:
    def test_ipf_data_has_work_packages(self, ipf_data):
        assert "work_packages" in ipf_data
        assert len(ipf_data["work_packages"]) == 4

    def test_each_wp_has_unique_id(self, ipf_data):
        ids = [wp["wp_id"] for wp in ipf_data["work_packages"]]
        assert len(ids) == len(set(ids))

    def test_each_wp_has_required_fields(self, ipf_data):
        required = [
            "wp_id", "title", "rationale", "scope_in", "scope_out",
            "dependencies", "definition_of_done", "governance_pins",
        ]
        for wp in ipf_data["work_packages"]:
            for field in required:
                assert field in wp, f"WP '{wp['wp_id']}' missing '{field}'"

    def test_validation_passes(self, handler, ipf_schema, ipf_data):
        is_valid, errors = handler.validate(ipf_data, ipf_schema)
        assert is_valid, f"Validation errors: {errors}"


# =========================================================================
# C3 — Reconciliation entries (kept/split/merged/dropped)
# =========================================================================


class TestC3ReconciliationEntries:
    def test_schema_has_candidate_reconciliation(self, ipf_schema):
        assert "candidate_reconciliation" in ipf_schema["properties"]

    def test_reconciliation_entries_exist(self, ipf_data):
        assert "candidate_reconciliation" in ipf_data
        assert len(ipf_data["candidate_reconciliation"]) == 5

    def test_reconciliation_has_all_outcome_types(self, ipf_data):
        outcomes = {r["outcome"] for r in ipf_data["candidate_reconciliation"]}
        assert outcomes == {"kept", "split", "merged", "dropped"}

    def test_kept_entry_has_one_result(self, ipf_data):
        kept = [r for r in ipf_data["candidate_reconciliation"] if r["outcome"] == "kept"]
        assert len(kept) == 1
        assert len(kept[0]["resulting_wp_ids"]) == 1

    def test_split_entry_has_multiple_results(self, ipf_data):
        split = [r for r in ipf_data["candidate_reconciliation"] if r["outcome"] == "split"]
        assert len(split) == 1
        assert len(split[0]["resulting_wp_ids"]) == 2

    def test_dropped_entry_has_empty_results(self, ipf_data):
        dropped = [r for r in ipf_data["candidate_reconciliation"] if r["outcome"] == "dropped"]
        assert len(dropped) == 1
        assert dropped[0]["resulting_wp_ids"] == []

    def test_each_reconciliation_entry_has_required_fields(self, ipf_data):
        for entry in ipf_data["candidate_reconciliation"]:
            assert "candidate_id" in entry
            assert "outcome" in entry
            assert "resulting_wp_ids" in entry
            assert "notes" in entry


# =========================================================================
# C4 — Bidirectional traceability
# =========================================================================


class TestC4BidirectionalTraceability:
    def test_every_wp_has_source_candidate_ids(self, ipf_data):
        for wp in ipf_data["work_packages"]:
            assert "source_candidate_ids" in wp, f"WP '{wp['wp_id']}' missing source_candidate_ids"
            assert "transformation" in wp, f"WP '{wp['wp_id']}' missing transformation"

    def test_every_wp_traces_back_to_candidates(self, ipf_data):
        """Every WP with transformation != 'added' must have non-empty source_candidate_ids."""
        for wp in ipf_data["work_packages"]:
            if wp["transformation"] != "added":
                assert len(wp["source_candidate_ids"]) >= 1, (
                    f"WP '{wp['wp_id']}' has transformation '{wp['transformation']}' "
                    f"but empty source_candidate_ids"
                )

    def test_every_candidate_traces_forward(self, ipf_data):
        """Every candidate_id in reconciliation maps to an outcome."""
        candidate_ids = {r["candidate_id"] for r in ipf_data["candidate_reconciliation"]}
        assert len(candidate_ids) == len(ipf_data["candidate_reconciliation"])

    def test_resulting_wp_ids_reference_real_wps(self, ipf_data):
        """All resulting_wp_ids must exist in work_packages[]."""
        wp_ids = {wp["wp_id"] for wp in ipf_data["work_packages"]}
        for entry in ipf_data["candidate_reconciliation"]:
            for wp_id in entry["resulting_wp_ids"]:
                assert wp_id in wp_ids, (
                    f"Reconciliation references '{wp_id}' which is not in work_packages[]"
                )

    def test_merged_wp_has_multiple_sources(self, ipf_data):
        merged = [wp for wp in ipf_data["work_packages"] if wp["transformation"] == "merged"]
        assert len(merged) == 1
        assert len(merged[0]["source_candidate_ids"]) >= 2


# =========================================================================
# C5 — Governance pinning
# =========================================================================


class TestC5GovernancePinning:
    def test_every_wp_has_governance_pins(self, ipf_data):
        for wp in ipf_data["work_packages"]:
            assert "governance_pins" in wp, f"WP '{wp['wp_id']}' missing governance_pins"

    def test_governance_pins_has_ta_version_id(self, ipf_data):
        for wp in ipf_data["work_packages"]:
            pins = wp["governance_pins"]
            assert "ta_version_id" in pins, (
                f"WP '{wp['wp_id']}' governance_pins missing ta_version_id"
            )
            assert pins["ta_version_id"], (
                f"WP '{wp['wp_id']}' governance_pins.ta_version_id is empty"
            )

    def test_governance_pins_has_adr_refs(self, ipf_data):
        """adr_refs must exist (may be empty list)."""
        for wp in ipf_data["work_packages"]:
            pins = wp["governance_pins"]
            assert "adr_refs" in pins, (
                f"WP '{wp['wp_id']}' governance_pins missing adr_refs"
            )
            assert isinstance(pins["adr_refs"], list)

    def test_schema_defines_governance_pins_on_wp(self, ipf_schema):
        # work_packages items use $ref — resolve via definitions
        wp_ref = ipf_schema["properties"]["work_packages"]["items"]
        if "$ref" in wp_ref:
            ref_name = wp_ref["$ref"].split("/")[-1]
            wp_props = ipf_schema["definitions"][ref_name]["properties"]
        else:
            wp_props = wp_ref["properties"]
        assert "governance_pins" in wp_props


# =========================================================================
# C6 — Committed WPs instantiated via get_child_documents()
# =========================================================================


class TestC6WPInstantiation:
    def test_get_child_documents_returns_wp_children(self, handler, ipf_data):
        children = handler.get_child_documents(ipf_data, "Test Plan")
        assert len(children) == 4

    def test_child_doc_type_is_work_package(self, handler, ipf_data):
        children = handler.get_child_documents(ipf_data, "Test Plan")
        assert all(c["doc_type_id"] == "work_package" for c in children)

    def test_child_identifier_matches_wp_id(self, handler, ipf_data):
        children = handler.get_child_documents(ipf_data, "Test Plan")
        ids = [c["identifier"] for c in children]
        assert "wp_document_registry" in ids
        assert "wp_llm_client" in ids

    def test_child_content_has_wp_fields(self, handler, ipf_data):
        children = handler.get_child_documents(ipf_data, "Test Plan")
        content = children[0]["content"]
        assert content["wp_id"] == "wp_document_registry"
        assert content["title"] == "Document Type Registry"
        assert content["rationale"] == "Foundation for all document types"
        assert "scope_in" in content
        assert "scope_out" in content
        assert "definition_of_done" in content
        assert "governance_pins" in content

    def test_child_content_has_lineage(self, handler, ipf_data):
        children = handler.get_child_documents(ipf_data, "Test Plan")
        lineage = children[0]["content"]["_lineage"]
        assert lineage["parent_document_type"] == "implementation_plan"
        assert lineage["source_candidate_ids"] == ["WPC-001"]
        assert lineage["transformation"] == "kept"

    def test_child_wp_state_is_planned(self, handler, ipf_data):
        """Newly instantiated WPs start in PLANNED state."""
        children = handler.get_child_documents(ipf_data, "Test Plan")
        for child in children:
            assert child["content"]["state"] == "PLANNED"

    def test_empty_work_packages_returns_empty(self, handler):
        data = {"plan_summary": {}, "work_packages": []}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []

    def test_missing_work_packages_key_returns_empty(self, handler):
        data = {"plan_summary": {}}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []
