"""Tests for ImplementationPlanHandler transform and render.

Updated for v3 schema: work_package_candidates with candidate_id (WPC-###),
no governance_pins/transformation/source_candidate_ids (Work Binder concerns).
risk_summary uses affected_candidates with WPC-### IDs.
"""

import pytest
from app.domain.handlers.implementation_plan_handler import ImplementationPlanHandler


@pytest.fixture
def handler():
    return ImplementationPlanHandler()


@pytest.fixture
def plan_data():
    """v3 IP content with 2 WP candidates and risk summary."""
    return {
        "meta": {
            "schema_version": "3.0",
            "artifact_id": "test-ip-001",
            "created_at": "2026-01-01T00:00:00Z",
            "source": "human",
        },
        "plan_summary": {
            "overall_intent": "Build the app",
            "mvp_definition": "Core features",
            "key_constraints": ["On-prem only"],
            "sequencing_rationale": "Foundation first",
        },
        "work_package_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "Storage Foundation",
                "rationale": "Implement local storage",
                "scope_in": ["Storage API"],
                "scope_out": ["Cloud sync"],
                "dependencies": [],
                "definition_of_done": ["Storage API functional"],
            },
            {
                "candidate_id": "WPC-002",
                "title": "Data Models",
                "rationale": "Core data structures",
                "scope_in": ["ChildProfile", "LearningSession"],
                "scope_out": ["Advanced analytics"],
                "dependencies": [
                    {
                        "depends_on_candidate_id": "WPC-001",
                        "dependency_type": "must_complete_first",
                        "notes": "Storage must exist first",
                    }
                ],
                "definition_of_done": ["Models validated"],
            },
        ],
        "risk_summary": [
            {
                "risk": "Storage API may not support concurrent writes",
                "affected_candidates": ["WPC-001"],
                "overall_impact": "medium",
                "mitigation_strategy": "Add locking strategy",
            },
        ],
        "cross_cutting_concerns": ["Stateless execution invariant"],
    }


class TestTransform:
    def test_adds_wp_count(self, handler, plan_data):
        result = handler.transform(plan_data)
        assert result["wp_count"] == 2

    def test_empty_candidates_gives_zero_count(self, handler):
        data = {"work_package_candidates": []}
        result = handler.transform(data)
        assert result["wp_count"] == 0

    def test_associated_risks_injected_from_risk_summary(self, handler, plan_data):
        """Transform injects associated_risks from risk_summary (v3)."""
        result = handler.transform(plan_data)
        wp1 = result["work_package_candidates"][0]
        assert len(wp1["associated_risks"]) == 1
        assert "concurrent writes" in wp1["associated_risks"][0]

    def test_no_risks_leaves_empty_list(self, handler, plan_data):
        """WP with no matching risks gets empty associated_risks."""
        result = handler.transform(plan_data)
        wp2 = result["work_package_candidates"][1]
        assert wp2["associated_risks"] == []

    def test_associated_risks_from_risks_overview(self, handler):
        """Transform also supports v2 risks_overview format."""
        data = {
            "work_package_candidates": [
                {"candidate_id": "WPC-001", "title": "Test"},
            ],
            "risks_overview": [
                {
                    "risk_id": "RSK-001",
                    "description": "Test risk",
                    "affected_candidates": ["WPC-001"],
                },
            ],
        }
        result = handler.transform(data)
        wp = result["work_package_candidates"][0]
        assert len(wp["associated_risks"]) == 1
        assert "RSK-001" in wp["associated_risks"][0]

    def test_get_child_documents_returns_empty(self, handler, plan_data):
        """WP creation is manual -- handler's get_child_documents returns empty.
        (Base class provides default empty implementation.)"""
        children = handler.get_child_documents(plan_data, "Test Plan")
        assert children == []


class TestRender:
    def test_render_includes_count(self, handler, plan_data):
        result = handler.transform(plan_data)
        rendered = handler.render(result)
        assert "2" in rendered
        assert "WP candidates" in rendered

    def test_render_summary_includes_count(self, handler, plan_data):
        result = handler.transform(plan_data)
        summary = handler.render_summary(result)
        assert "2" in summary
