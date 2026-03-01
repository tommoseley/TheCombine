"""
Tests for ProjectDiscoveryHandler methods -- WS-CRAP-004.

Tests validate, transform, extract_title, render, and render_summary
methods to achieve coverage on the existing (already decomposed) handler.
"""

import pytest

from app.domain.handlers.project_discovery_handler import ProjectDiscoveryHandler


@pytest.fixture
def handler():
    return ProjectDiscoveryHandler()


# =========================================================================
# validate
# =========================================================================


class TestValidate:
    """Tests for ProjectDiscoveryHandler.validate."""

    def test_valid_full_document(self, handler):
        data = {
            "project_name": "Test Project",
            "preliminary_summary": {
                "problem_understanding": "We need a thing",
                "architectural_intent": "Build it well",
            },
        }
        valid, errors = handler.validate(data)
        assert valid is True
        assert errors == []

    def test_missing_project_name(self, handler):
        data = {
            "preliminary_summary": {
                "problem_understanding": "We need a thing",
                "architectural_intent": "Build it well",
            },
        }
        valid, errors = handler.validate(data)
        assert valid is False
        assert any("project_name" in e for e in errors)

    def test_empty_project_name(self, handler):
        data = {
            "project_name": "",
            "preliminary_summary": {
                "problem_understanding": "text",
                "architectural_intent": "text",
            },
        }
        valid, errors = handler.validate(data)
        assert valid is False

    def test_missing_preliminary_summary(self, handler):
        data = {"project_name": "Test"}
        valid, errors = handler.validate(data)
        assert valid is False
        assert any("preliminary_summary" in e for e in errors)

    def test_string_summary_valid(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": "A simple summary",
        }
        valid, errors = handler.validate(data)
        assert valid is True

    def test_empty_string_summary_invalid(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": "   ",
        }
        valid, errors = handler.validate(data)
        assert valid is False

    def test_dict_summary_missing_required_fields(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {"other_field": "value"},
        }
        valid, errors = handler.validate(data)
        assert valid is False
        assert any("problem_understanding" in e for e in errors)

    def test_non_dict_non_string_summary_invalid(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": 42,
        }
        valid, errors = handler.validate(data)
        assert valid is False


# =========================================================================
# transform
# =========================================================================


class TestTransform:
    """Tests for ProjectDiscoveryHandler.transform."""

    def test_ensures_array_fields(self, handler):
        data = {"project_name": "Test"}
        result = handler.transform(data)
        assert result["unknowns"] == []
        assert result["stakeholder_questions"] == []
        assert result["early_decision_points"] == []
        assert result["known_constraints"] == []
        assert result["assumptions"] == []
        assert result["identified_risks"] == []
        assert result["mvp_guardrails"] == []
        assert result["recommendations_for_pm"] == []

    def test_preserves_existing_arrays(self, handler):
        data = {"unknowns": [{"question": "why?"}]}
        result = handler.transform(data)
        assert result["unknowns"] == [{"question": "why?"}]

    def test_string_summary_converted_to_dict(self, handler):
        data = {"preliminary_summary": "A simple summary"}
        result = handler.transform(data)
        assert isinstance(result["preliminary_summary"], dict)
        assert result["preliminary_summary"]["problem_understanding"] == "A simple summary"
        assert result["preliminary_summary"]["architectural_intent"] == ""
        assert result["preliminary_summary"]["scope_pressure_points"] == ""


# =========================================================================
# extract_title
# =========================================================================


class TestExtractTitle:
    """Tests for ProjectDiscoveryHandler.extract_title."""

    def test_with_project_name(self, handler):
        data = {"project_name": "My Project"}
        assert handler.extract_title(data) == "Project Discovery: My Project"

    def test_without_project_name(self, handler):
        data = {}
        assert handler.extract_title(data) == "Project Discovery"

    def test_empty_project_name(self, handler):
        data = {"project_name": ""}
        assert handler.extract_title(data) == "Project Discovery"

    def test_custom_fallback(self, handler):
        data = {}
        assert handler.extract_title(data, fallback="Custom") == "Custom"


# =========================================================================
# render
# =========================================================================


class TestRender:
    """Tests for ProjectDiscoveryHandler.render."""

    def test_basic_render(self, handler):
        data = {
            "project_name": "Test Project",
            "preliminary_summary": {
                "problem_understanding": "We need this",
                "architectural_intent": "Build well",
            },
        }
        html = handler.render(data)
        assert "Test Project" in html
        assert "We need this" in html
        assert "Build well" in html

    def test_render_with_blocking_questions(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "stakeholder_questions": [
                {"question": "What about security?", "blocking": True, "directed_to": "CTO"},
            ],
        }
        html = handler.render(data)
        assert "Blocking Questions" in html
        assert "What about security?" in html
        assert "CTO" in html

    def test_render_with_unknowns(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "unknowns": [
                {
                    "question": "How many users?",
                    "why_it_matters": "Affects scaling",
                    "impact_if_unresolved": "Over-provisioning",
                }
            ],
        }
        html = handler.render(data)
        assert "Unknowns" in html
        assert "How many users?" in html
        assert "Affects scaling" in html
        assert "Over-provisioning" in html

    def test_render_with_decision_points(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "early_decision_points": [
                {
                    "decision_area": "Database choice",
                    "why_early": "Affects everything",
                    "options": ["PostgreSQL", "MongoDB"],
                    "recommendation_direction": "Use PostgreSQL",
                }
            ],
        }
        html = handler.render(data)
        assert "Database choice" in html
        assert "Affects everything" in html
        assert "PostgreSQL" in html
        assert "MongoDB" in html
        assert "Use PostgreSQL" in html

    def test_render_with_constraints_and_assumptions(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "known_constraints": ["Must use AWS"],
            "assumptions": ["Team has AWS experience"],
        }
        html = handler.render(data)
        assert "Must use AWS" in html
        assert "Team has AWS experience" in html

    def test_render_with_risks(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "identified_risks": [
                {"description": "Timeline risk", "likelihood": "high", "impact_on_planning": "May delay"},
                {"description": "Budget risk", "likelihood": "medium", "impact_on_planning": "Need approval"},
                {"description": "Minor risk", "likelihood": "low", "impact_on_planning": "Manageable"},
            ],
        }
        html = handler.render(data)
        assert "Timeline risk" in html
        assert "Budget risk" in html
        assert "Minor risk" in html

    def test_render_with_guardrails_string(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "mvp_guardrails": ["No blockchain"],
        }
        html = handler.render(data)
        assert "No blockchain" in html

    def test_render_with_guardrails_dict(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "mvp_guardrails": [{"guardrail": "No blockchain"}],
        }
        html = handler.render(data)
        assert "No blockchain" in html

    def test_render_with_recommendations(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "recommendations_for_pm": ["Start with auth module"],
        }
        html = handler.render(data)
        assert "Start with auth module" in html

    def test_render_with_non_blocking_questions(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "stakeholder_questions": [
                {"question": "Nice to know?", "blocking": False, "directed_to": "team"},
            ],
        }
        html = handler.render(data)
        assert "Other Stakeholder Questions" in html
        assert "Nice to know?" in html

    def test_render_html_escaping(self, handler):
        data = {
            "project_name": "<script>alert('xss')</script>",
            "preliminary_summary": {},
        }
        html = handler.render(data)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_scope_pressure_points(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {
                "problem_understanding": "test",
                "architectural_intent": "test",
                "scope_pressure_points": "Timeline is tight",
            },
        }
        html = handler.render(data)
        assert "Timeline is tight" in html


# =========================================================================
# render_summary
# =========================================================================


class TestRenderSummary:
    """Tests for ProjectDiscoveryHandler.render_summary."""

    def test_basic_summary(self, handler):
        data = {
            "project_name": "My Project",
            "preliminary_summary": {
                "problem_understanding": "We need to build something",
            },
        }
        html = handler.render_summary(data)
        assert "My Project" in html
        assert "We need to build something" in html

    def test_string_summary(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": "Simple text summary",
        }
        html = handler.render_summary(data)
        assert "Simple text summary" in html

    def test_counts_unknowns_and_blocking(self, handler):
        data = {
            "project_name": "Test",
            "preliminary_summary": {},
            "unknowns": [{"q": "a"}, {"q": "b"}],
            "stakeholder_questions": [
                {"question": "a", "blocking": True},
                {"question": "b", "blocking": False},
                {"question": "c", "blocking": True},
            ],
        }
        html = handler.render_summary(data)
        assert "2 unknowns" in html
        assert "2 blocking questions" in html

    def test_empty_data(self, handler):
        html = handler.render_summary({})
        assert "Project" in html
        assert "0 unknowns" in html
        assert "0 blocking questions" in html
