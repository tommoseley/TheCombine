"""Tests for Document Interaction Workflow Plan registry (ADR-039)."""

import json
import pytest
from pathlib import Path

from app.domain.workflow.plan_models import WorkflowPlan
from app.domain.workflow.plan_registry import (
    PlanNotFoundError,
    PlanRegistry,
    get_plan_registry,
    reset_plan_registry,
)


@pytest.fixture
def registry():
    """Create a fresh PlanRegistry instance."""
    return PlanRegistry()


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


@pytest.fixture
def sample_plan(valid_plan_dict):
    """Create a sample WorkflowPlan."""
    return WorkflowPlan.from_dict(valid_plan_dict)


class TestPlanRegistryRegister:
    """Tests for plan registration."""

    def test_register_plan(self, registry, sample_plan):
        """Registering a plan makes it available."""
        registry.register(sample_plan)

        assert registry.has("test_plan")
        assert registry.get("test_plan") == sample_plan

    def test_register_duplicate_raises(self, registry, sample_plan):
        """Registering duplicate plan ID raises ValueError."""
        registry.register(sample_plan)

        with pytest.raises(ValueError) as exc_info:
            registry.register(sample_plan)

        assert "already registered" in str(exc_info.value)

    def test_register_indexes_by_document_type(self, registry, sample_plan):
        """Registered plan is indexed by document_type."""
        registry.register(sample_plan)

        found = registry.get_by_document_type("test_document")
        assert found == sample_plan


class TestPlanRegistryReplace:
    """Tests for plan replacement."""

    def test_replace_existing_plan(self, registry, valid_plan_dict):
        """Replacing existing plan works."""
        plan1 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.register(plan1)

        valid_plan_dict["version"] = "2.0.0"
        plan2 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.replace(plan2)

        assert registry.get("test_plan").version == "2.0.0"

    def test_replace_registers_if_new(self, registry, sample_plan):
        """Replacing non-existent plan registers it."""
        registry.replace(sample_plan)

        assert registry.has("test_plan")

    def test_replace_updates_document_type_index(self, registry, valid_plan_dict):
        """Replacing plan updates document type index."""
        plan1 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.register(plan1)

        # Change document type
        valid_plan_dict["document_type"] = "new_document"
        plan2 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.replace(plan2)

        # Old document type should not find it
        assert registry.get_by_document_type("test_document") is None
        # New document type should find it
        assert registry.get_by_document_type("new_document") == plan2


class TestPlanRegistryGet:
    """Tests for plan retrieval."""

    def test_get_existing_plan(self, registry, sample_plan):
        """Getting existing plan returns it."""
        registry.register(sample_plan)

        plan = registry.get("test_plan")
        assert plan == sample_plan

    def test_get_nonexistent_raises(self, registry):
        """Getting non-existent plan raises PlanNotFoundError."""
        with pytest.raises(PlanNotFoundError) as exc_info:
            registry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_get_optional_returns_none(self, registry):
        """get_optional returns None for non-existent plan."""
        result = registry.get_optional("nonexistent")
        assert result is None

    def test_get_optional_returns_plan(self, registry, sample_plan):
        """get_optional returns plan if it exists."""
        registry.register(sample_plan)

        result = registry.get_optional("test_plan")
        assert result == sample_plan

    def test_get_by_document_type_returns_none(self, registry):
        """get_by_document_type returns None if not found."""
        result = registry.get_by_document_type("nonexistent")
        assert result is None


class TestPlanRegistryList:
    """Tests for listing plans."""

    def test_list_ids_empty(self, registry):
        """list_ids returns empty list when no plans."""
        assert registry.list_ids() == []

    def test_list_ids(self, registry, valid_plan_dict):
        """list_ids returns all registered plan IDs."""
        plan1 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.register(plan1)

        valid_plan_dict["workflow_id"] = "plan_2"
        valid_plan_dict["document_type"] = "doc_2"
        plan2 = WorkflowPlan.from_dict(valid_plan_dict)
        registry.register(plan2)

        ids = registry.list_ids()
        assert set(ids) == {"test_plan", "plan_2"}

    def test_list_plans(self, registry, sample_plan):
        """list_plans returns all registered plans."""
        registry.register(sample_plan)

        plans = registry.list_plans()
        assert len(plans) == 1
        assert plans[0] == sample_plan


class TestPlanRegistryClear:
    """Tests for clearing registry."""

    def test_clear(self, registry, sample_plan):
        """clear removes all plans."""
        registry.register(sample_plan)
        assert registry.has("test_plan")

        registry.clear()

        assert not registry.has("test_plan")
        assert registry.list_ids() == []


class TestPlanRegistryLoadFromDirectory:
    """Tests for loading plans from directory."""

    def test_load_from_directory(self, registry, valid_plan_dict, tmp_path):
        """load_from_directory loads and registers plans."""
        # Write plan file
        plan_file = tmp_path / "test_plan.json"
        plan_file.write_text(json.dumps(valid_plan_dict))

        count = registry.load_from_directory(tmp_path)

        assert count == 1
        assert registry.has("test_plan")

    def test_load_from_empty_directory(self, registry, tmp_path):
        """load_from_directory returns 0 for empty directory."""
        count = registry.load_from_directory(tmp_path)
        assert count == 0


class TestPlanRegistryLoadFile:
    """Tests for loading single plan file."""

    def test_load_file(self, registry, valid_plan_dict, tmp_path):
        """load_file loads and registers a single plan."""
        plan_file = tmp_path / "test_plan.json"
        plan_file.write_text(json.dumps(valid_plan_dict))

        plan = registry.load_file(plan_file)

        assert plan.workflow_id == "test_plan"
        assert registry.has("test_plan")


class TestPlanNotFoundError:
    """Tests for PlanNotFoundError."""

    def test_error_message(self):
        """Error includes plan ID in message."""
        error = PlanNotFoundError("missing_plan")
        assert "missing_plan" in str(error)

    def test_error_shows_available(self):
        """Error shows available plans if provided."""
        error = PlanNotFoundError("missing", available=["plan_a", "plan_b"])
        error_str = str(error)

        assert "missing" in error_str
        assert "plan_a" in error_str
        assert "plan_b" in error_str


class TestGlobalPlanRegistry:
    """Tests for global registry functions."""

    def test_get_plan_registry_creates_instance(self):
        """get_plan_registry creates instance if none exists."""
        reset_plan_registry()

        registry = get_plan_registry()
        assert isinstance(registry, PlanRegistry)

    def test_get_plan_registry_returns_same_instance(self):
        """get_plan_registry returns same instance on subsequent calls."""
        reset_plan_registry()

        registry1 = get_plan_registry()
        registry2 = get_plan_registry()

        assert registry1 is registry2

    def test_reset_plan_registry(self, sample_plan):
        """reset_plan_registry clears the global instance."""
        reset_plan_registry()
        registry = get_plan_registry()
        registry.register(sample_plan)

        reset_plan_registry()
        new_registry = get_plan_registry()

        assert not new_registry.has("test_plan")


class TestLoadActualConciergeIntakePlan:
    """Integration test with actual concierge_intake.v1.json."""

    def test_load_and_retrieve_concierge_intake(self, registry):
        """Load concierge_intake.v1.json and retrieve by ID and document type."""
        plan_path = Path(__file__).parent.parent.parent.parent / \
            "seed" / "workflows" / "concierge_intake.v1.json"

        if not plan_path.exists():
            pytest.skip("concierge_intake.v1.json not found")

        registry.load_file(plan_path)

        # Retrieve by ID
        by_id = registry.get("concierge_intake")
        assert by_id.workflow_id == "concierge_intake"

        # Retrieve by document type
        by_doc = registry.get_by_document_type("concierge_intake")
        assert by_doc is not None
        assert by_doc.workflow_id == "concierge_intake"
