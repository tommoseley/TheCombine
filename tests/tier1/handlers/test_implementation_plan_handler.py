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
    def test_transform_is_identity(self, handler, plan_data):
        """Transform is a no-op — schema has additionalProperties: false,
        so computed fields are provided at render time instead."""
        result = handler.transform(plan_data)
        assert result is plan_data

    def test_transform_does_not_inject_wp_count(self, handler, plan_data):
        result = handler.transform(plan_data)
        assert "wp_count" not in result

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
