"""Tests for ImplementationPlanHandler child document extraction and transform."""

import pytest
from app.domain.handlers.implementation_plan_handler import ImplementationPlanHandler


@pytest.fixture
def handler():
    return ImplementationPlanHandler()


@pytest.fixture
def plan_data():
    """Minimal IPF content with 2 Work Packages."""
    return {
        "plan_summary": {
            "overall_intent": "Build the app",
            "mvp_definition": "Core features",
            "key_constraints": ["On-prem only"],
            "sequencing_rationale": "Foundation first",
        },
        "work_packages": [
            {
                "wp_id": "wp_storage_foundation",
                "title": "Storage Foundation",
                "rationale": "Implement local storage",
                "scope_in": ["Storage API"],
                "scope_out": ["Cloud sync"],
                "dependencies": [],
                "definition_of_done": ["Storage API functional"],
                "governance_pins": {
                    "ta_version_id": "ta-v1.0",
                    "adr_refs": [],
                    "policy_refs": [],
                },
                "transformation": "kept",
                "source_candidate_ids": ["WPC-001"],
                "transformation_notes": "Preserved from IPP",
            },
            {
                "wp_id": "wp_data_models",
                "title": "Data Models",
                "rationale": "Core data structures",
                "scope_in": ["ChildProfile", "LearningSession"],
                "scope_out": ["Advanced analytics"],
                "dependencies": [{"wp_id": "wp_storage_foundation", "dependency_type": "must_complete_first"}],
                "definition_of_done": ["Models validated"],
                "governance_pins": {
                    "ta_version_id": "ta-v1.0",
                    "adr_refs": ["ADR-045"],
                    "policy_refs": [],
                },
                "transformation": "merged",
                "source_candidate_ids": ["WPC-002", "WPC-003"],
                "transformation_notes": "Merged models and validation",
            },
        ],
        "candidate_reconciliation": [],
    }


class TestGetChildDocuments:
    def test_extracts_correct_count(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert len(children) == 2

    def test_child_doc_type_is_work_package(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert all(c["doc_type_id"] == "work_package" for c in children)

    def test_child_identifier_matches_wp_id(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        ids = [c["identifier"] for c in children]
        assert ids == ["wp_storage_foundation", "wp_data_models"]

    def test_child_title_includes_wp_name(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert children[0]["title"] == "WP: Storage Foundation"
        assert children[1]["title"] == "WP: Data Models"

    def test_child_content_has_all_fields(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        content = children[0]["content"]
        assert content["wp_id"] == "wp_storage_foundation"
        assert content["title"] == "Storage Foundation"
        assert content["rationale"] == "Implement local storage"
        assert content["scope_in"] == ["Storage API"]
        assert content["scope_out"] == ["Cloud sync"]
        assert content["dependencies"] == []
        assert content["definition_of_done"] == ["Storage API functional"]
        assert content["state"] == "PLANNED"
        assert content["ws_child_refs"] == []
        assert content["governance_pins"]["ta_version_id"] == "ta-v1.0"

    def test_child_content_has_lineage(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        lineage = children[0]["content"]["_lineage"]
        assert lineage["parent_document_type"] == "implementation_plan"
        assert lineage["parent_execution_id"] is None  # Injected by caller
        assert lineage["source_candidate_ids"] == ["WPC-001"]
        assert lineage["transformation"] == "kept"
        assert lineage["transformation_notes"] == "Preserved from IPP"

    def test_merged_wp_lineage_has_multiple_sources(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        lineage = children[1]["content"]["_lineage"]
        assert lineage["source_candidate_ids"] == ["WPC-002", "WPC-003"]
        assert lineage["transformation"] == "merged"

    def test_empty_work_packages_returns_empty(self, handler):
        data = {"plan_summary": {}, "work_packages": []}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []

    def test_missing_work_packages_key_returns_empty(self, handler):
        data = {"plan_summary": {}}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []


class TestTransform:
    def test_adds_wp_count(self, handler, plan_data):
        result = handler.transform(plan_data)
        assert result["wp_count"] == 2

    def test_empty_work_packages_gives_zero_count(self, handler):
        data = {"work_packages": []}
        result = handler.transform(data)
        assert result["wp_count"] == 0
