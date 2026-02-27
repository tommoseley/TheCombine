"""Tests for Document Interaction Workflow Plan loader (ADR-039)."""

import json
import pytest
from pathlib import Path

from app.domain.workflow.plan_loader import PlanLoader, PlanLoadError
from app.domain.workflow.plan_models import WorkflowPlan


@pytest.fixture
def loader():
    """Create a PlanLoader instance."""
    return PlanLoader()


@pytest.fixture
def valid_plan_dict():
    """A valid workflow plan dict."""
    return {
        "workflow_id": "test_plan",
        "version": "1.0.0",
        "name": "Test Plan",
        "description": "A test plan",
        "scope_type": "document",
        "document_type": "test_document",
        "entry_node_ids": ["start"],
        "nodes": [
            {"node_id": "start", "type": "task", "description": "Start"},
            {"node_id": "end", "type": "end", "description": "End",
             "terminal_outcome": "stabilized"},
        ],
        "edges": [
            {"edge_id": "e1", "from_node_id": "start",
             "to_node_id": "end", "outcome": "success"},
        ],
        "outcome_mapping": {"mappings": []},
        "thread_ownership": {"owns_thread": False},
        "governance": {},
    }


class TestPlanLoaderLoadDict:
    """Tests for load_dict method."""

    def test_load_valid_dict(self, loader, valid_plan_dict):
        """Loading valid dict returns WorkflowPlan."""
        plan = loader.load_dict(valid_plan_dict)

        assert isinstance(plan, WorkflowPlan)
        assert plan.workflow_id == "test_plan"
        assert plan.version == "1.0.0"

    def test_load_invalid_dict_raises(self, loader):
        """Loading invalid dict raises PlanLoadError."""
        invalid = {"nodes": []}  # Missing required fields

        with pytest.raises(PlanLoadError) as exc_info:
            loader.load_dict(invalid)

        assert "validation failed" in str(exc_info.value).lower()
        assert len(exc_info.value.errors) > 0

    def test_load_dict_with_source_path(self, loader, valid_plan_dict):
        """Source path is included in error messages."""
        invalid = {"nodes": []}

        with pytest.raises(PlanLoadError) as exc_info:
            loader.load_dict(invalid, source_path="/path/to/file.json")

        assert "/path/to/file.json" in str(exc_info.value)


class TestPlanLoaderLoadFile:
    """Tests for load method (file loading)."""

    def test_load_file_not_found(self, loader):
        """Loading non-existent file raises PlanLoadError."""
        with pytest.raises(PlanLoadError) as exc_info:
            loader.load(Path("/nonexistent/path.json"))

        assert "not found" in str(exc_info.value).lower()

    def test_load_invalid_json(self, loader, tmp_path):
        """Loading invalid JSON raises PlanLoadError."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ invalid json }")

        with pytest.raises(PlanLoadError) as exc_info:
            loader.load(bad_json)

        assert "invalid json" in str(exc_info.value).lower()

    def test_load_valid_file(self, loader, valid_plan_dict, tmp_path):
        """Loading valid JSON file returns WorkflowPlan."""
        plan_file = tmp_path / "test_plan.json"
        plan_file.write_text(json.dumps(valid_plan_dict))

        plan = loader.load(plan_file)

        assert isinstance(plan, WorkflowPlan)
        assert plan.workflow_id == "test_plan"

    def test_load_utf8_bom(self, loader, valid_plan_dict, tmp_path):
        """Loading file with UTF-8 BOM works."""
        plan_file = tmp_path / "bom_plan.json"
        # Write with BOM
        with open(plan_file, "w", encoding="utf-8-sig") as f:
            json.dump(valid_plan_dict, f)

        plan = loader.load(plan_file)
        assert plan.workflow_id == "test_plan"


class TestPlanLoaderLoadAll:
    """Tests for load_all method (directory loading)."""

    def test_load_all_empty_directory(self, loader, tmp_path):
        """Loading from empty directory returns empty list."""
        plans = loader.load_all(tmp_path)
        assert plans == []

    def test_load_all_skips_non_plan_files(self, loader, valid_plan_dict, tmp_path):
        """Non-plan JSON files are skipped."""
        # Write a plan file
        plan_file = tmp_path / "valid_plan.json"
        plan_file.write_text(json.dumps(valid_plan_dict))

        # Write a non-plan JSON file
        other_file = tmp_path / "schema.json"
        other_file.write_text(json.dumps({"$schema": "http://example.com"}))

        plans = loader.load_all(tmp_path)

        assert len(plans) == 1
        assert plans[0].workflow_id == "test_plan"

    def test_load_all_multiple_plans(self, loader, valid_plan_dict, tmp_path):
        """Loading multiple plan files works."""
        # Write first plan
        plan1 = valid_plan_dict.copy()
        plan1["workflow_id"] = "plan_1"
        (tmp_path / "plan_1.json").write_text(json.dumps(plan1))

        # Write second plan
        plan2 = valid_plan_dict.copy()
        plan2["workflow_id"] = "plan_2"
        (tmp_path / "plan_2.json").write_text(json.dumps(plan2))

        plans = loader.load_all(tmp_path)

        assert len(plans) == 2
        plan_ids = {p.workflow_id for p in plans}
        assert plan_ids == {"plan_1", "plan_2"}


class TestPlanLoadErrorFormatting:
    """Tests for PlanLoadError string formatting."""

    def test_error_with_no_validation_errors(self):
        """Error with no validation errors shows simple message."""
        error = PlanLoadError("Simple error")
        assert str(error) == "Simple error"

    def test_error_with_validation_errors(self):
        """Error with validation errors shows details."""
        from app.domain.workflow.plan_validator import (
            PlanValidationError,
            PlanValidationErrorCode,
        )

        errors = [
            PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message="Missing: workflow_id",
            ),
            PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message="Missing: nodes",
            ),
        ]
        error = PlanLoadError("Validation failed", errors=errors)

        error_str = str(error)
        assert "Validation failed" in error_str
        assert "Missing: workflow_id" in error_str
        assert "Missing: nodes" in error_str

    def test_error_truncates_many_errors(self):
        """Error with many validation errors is truncated."""
        from app.domain.workflow.plan_validator import (
            PlanValidationError,
            PlanValidationErrorCode,
        )

        errors = [
            PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Error {i}",
            )
            for i in range(10)
        ]
        error = PlanLoadError("Validation failed", errors=errors)

        error_str = str(error)
        assert "and 5 more errors" in error_str


class TestLoadActualConciergeIntakePlan:
    """Integration test loading the actual concierge_intake workflow."""

    def test_load_concierge_intake_plan(self, loader):
        """Load the actual concierge_intake workflow from combine-config."""
        plan_path = Path(__file__).parent.parent.parent.parent / \
            "combine-config" / "workflows" / "concierge_intake" / "releases" / "1.4.0" / "definition.json"

        if not plan_path.exists():
            pytest.skip("concierge_intake 1.4.0 definition.json not found")

        plan = loader.load(plan_path)

        assert plan.workflow_id == "concierge_intake"
        assert plan.version == "1.4.0"
        assert plan.scope_type == "document"
        assert plan.document_type == "concierge_intake"
        assert len(plan.nodes) == 7
        assert len(plan.edges) >= 10
        assert plan.thread_ownership.owns_thread is False  # Intake gate doesn't own thread
        assert plan.governance.circuit_breaker is not None
        assert plan.governance.circuit_breaker.max_retries == 2
