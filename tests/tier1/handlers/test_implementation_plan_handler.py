"""Tests for ImplementationPlanHandler child document extraction."""

import pytest
from app.domain.handlers.implementation_plan_handler import ImplementationPlanHandler


@pytest.fixture
def handler():
    return ImplementationPlanHandler()


@pytest.fixture
def plan_data():
    """Minimal IPF content with 2 epics."""
    return {
        "plan_summary": {
            "overall_intent": "Build the app",
            "mvp_definition": "Core features",
            "key_constraints": ["On-prem only"],
            "sequencing_rationale": "Foundation first",
        },
        "epics": [
            {
                "epic_id": "storage_foundation",
                "name": "Storage Foundation",
                "intent": "Implement local storage",
                "sequence": 1,
                "mvp_phase": "mvp",
                "design_required": "not_needed",
                "transformation": "kept",
                "source_candidate_ids": ["EC-1"],
                "transformation_notes": "Preserved from IPP",
                "in_scope": ["Storage API"],
                "out_of_scope": ["Cloud sync"],
                "dependencies": [],
                "risks": [{"risk": "Quota limits", "impact": "medium", "mitigation": "Monitor"}],
                "open_questions": [],
                "architecture_notes": ["Must support IndexedDB"],
            },
            {
                "epic_id": "data_models",
                "name": "Data Models",
                "intent": "Core data structures",
                "sequence": 2,
                "mvp_phase": "mvp",
                "design_required": "recommended",
                "transformation": "merged",
                "source_candidate_ids": ["EC-2", "EC-3"],
                "transformation_notes": "Merged models and validation",
                "in_scope": ["ChildProfile", "LearningSession"],
                "out_of_scope": ["Advanced analytics"],
                "dependencies": [{"epic_id": "storage_foundation", "dependency_type": "must_complete_first"}],
                "risks": [],
                "open_questions": [{"question": "Schema version?", "blocking": False}],
                "architecture_notes": [],
            },
        ],
    }


class TestGetChildDocuments:
    def test_extracts_correct_count(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert len(children) == 2

    def test_child_doc_type_is_epic(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert all(c["doc_type_id"] == "epic" for c in children)

    def test_child_identifier_matches_epic_id(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        ids = [c["identifier"] for c in children]
        assert ids == ["storage_foundation", "data_models"]

    def test_child_title_includes_epic_name(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert children[0]["title"] == "Epic: Storage Foundation"
        assert children[1]["title"] == "Epic: Data Models"

    def test_child_content_has_all_fields(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        content = children[0]["content"]
        assert content["epic_id"] == "storage_foundation"
        assert content["name"] == "Storage Foundation"
        assert content["intent"] == "Implement local storage"
        assert content["sequence"] == 1
        assert content["mvp_phase"] == "mvp"
        assert content["in_scope"] == ["Storage API"]
        assert content["out_of_scope"] == ["Cloud sync"]
        assert content["dependencies"] == []
        assert len(content["risks"]) == 1
        assert content["architecture_notes"] == ["Must support IndexedDB"]

    def test_child_content_has_lineage(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        lineage = children[0]["content"]["_lineage"]
        assert lineage["parent_document_type"] == "implementation_plan"
        assert lineage["parent_execution_id"] is None  # Injected by caller
        assert lineage["source_candidate_ids"] == ["EC-1"]
        assert lineage["transformation"] == "kept"
        assert lineage["transformation_notes"] == "Preserved from IPP"

    def test_merged_epic_lineage_has_multiple_sources(self, handler, plan_data):
        children = handler.get_child_documents(plan_data, "Test Plan")
        lineage = children[1]["content"]["_lineage"]
        assert lineage["source_candidate_ids"] == ["EC-2", "EC-3"]
        assert lineage["transformation"] == "merged"

    def test_empty_epics_returns_empty(self, handler):
        data = {"plan_summary": {}, "epics": []}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []

    def test_missing_epics_key_returns_empty(self, handler):
        data = {"plan_summary": {}}
        children = handler.get_child_documents(data, "Test Plan")
        assert children == []


class TestTransform:
    def test_adds_computed_fields(self, handler, plan_data):
        result = handler.transform(plan_data)
        assert result["epic_count"] == 2
        assert result["mvp_count"] == 2
        assert result["later_count"] == 0
        assert result["design_required_count"] == 0
        assert result["design_recommended_count"] == 1

    def test_derives_risk_summary_from_epic_risks(self, handler, plan_data):
        """risk_summary is mechanically projected from per-epic risks."""
        result = handler.transform(plan_data)
        rs = result["risk_summary"]
        assert len(rs) == 1  # Only storage_foundation has a risk
        assert rs[0]["risk"] == "Quota limits"
        assert rs[0]["affected_epics"] == ["storage_foundation"]
        assert rs[0]["overall_impact"] == "medium"
        assert rs[0]["mitigation_strategy"] == "Monitor"

    def test_risk_summary_empty_when_no_risks(self, handler):
        data = {
            "epics": [
                {"epic_id": "a", "mvp_phase": "mvp", "risks": []},
                {"epic_id": "b", "mvp_phase": "mvp", "risks": []},
            ]
        }
        result = handler.transform(data)
        assert result["risk_summary"] == []

    def test_risk_summary_multiple_epics_multiple_risks(self, handler):
        data = {
            "epics": [
                {
                    "epic_id": "auth",
                    "mvp_phase": "mvp",
                    "risks": [
                        {"risk": "Token expiry", "impact": "high", "mitigation": "Refresh flow"},
                        {"risk": "Brute force", "impact": "medium", "mitigation": "Rate limit"},
                    ],
                },
                {
                    "epic_id": "storage",
                    "mvp_phase": "mvp",
                    "risks": [
                        {"risk": "Data loss", "impact": "high", "mitigation": "Backups"},
                    ],
                },
            ]
        }
        result = handler.transform(data)
        rs = result["risk_summary"]
        assert len(rs) == 3
        # Order follows epic order, then risk order within epic
        assert rs[0]["risk"] == "Token expiry"
        assert rs[0]["affected_epics"] == ["auth"]
        assert rs[0]["overall_impact"] == "high"
        assert rs[1]["risk"] == "Brute force"
        assert rs[1]["affected_epics"] == ["auth"]
        assert rs[2]["risk"] == "Data loss"
        assert rs[2]["affected_epics"] == ["storage"]

    def test_risk_summary_overwrites_llm_generated(self, handler):
        """If LLM produced risk_summary, transform() overwrites it."""
        data = {
            "epics": [
                {
                    "epic_id": "x",
                    "mvp_phase": "mvp",
                    "risks": [{"risk": "Real risk", "impact": "low", "mitigation": "Handle it"}],
                },
            ],
            "risk_summary": [
                {"risk": "LLM hallucinated this", "affected_epics": ["x"],
                 "overall_impact": "critical", "mitigation_strategy": "Panic"},
            ],
        }
        result = handler.transform(data)
        rs = result["risk_summary"]
        assert len(rs) == 1
        assert rs[0]["risk"] == "Real risk"  # Mechanical, not LLM
