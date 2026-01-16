"""Tests for Document Workflow API (ADR-039)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.routers.document_workflows import router, get_executor, _persistence
from app.domain.workflow.plan_executor import PlanExecutor, PlanExecutorError
from app.domain.workflow.plan_registry import PlanRegistry
from app.domain.workflow.plan_models import (
    Edge,
    EdgeKind,
    Governance,
    Node,
    NodeType,
    OutcomeMapping,
    ThreadOwnership,
    WorkflowPlan,
)
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
)


def make_test_plan() -> WorkflowPlan:
    """Create a test workflow plan."""
    return WorkflowPlan(
        workflow_id="test_workflow",
        version="1.0.0",
        name="Test Workflow",
        description="A test workflow for API testing",
        scope_type="document",
        document_type="test_doc",
        entry_node_ids=["start"],
        nodes=[
            Node(
                node_id="start",
                type=NodeType.TASK,
                description="Start task",
                task_ref="task1",
            ),
            Node(
                node_id="end",
                type=NodeType.END,
                description="End node",
                terminal_outcome="stabilized",
            ),
        ],
        edges=[
            Edge(
                edge_id="e1",
                from_node_id="start",
                to_node_id="end",
                outcome="success",
                label="Success",
                kind=EdgeKind.AUTO,
            ),
        ],
        outcome_mapping=[],
        thread_ownership=ThreadOwnership(owns_thread=False),
        governance=Governance(),
    )


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_executor():
    """Create mock executor."""
    return MagicMock(spec=PlanExecutor)


@pytest.fixture
def test_state():
    """Create a test workflow state."""
    return DocumentWorkflowState(
        execution_id="exec-123",
        workflow_id="test_workflow",
        document_id="doc-456",
        document_type="test_doc",
        current_node_id="start",
        status=DocumentWorkflowStatus.RUNNING,
    )


class TestStartExecution:
    """Tests for POST /document-workflows/start."""

    def test_start_execution_success(self, client, mock_executor, test_state, app):
        """Successfully start a workflow execution."""
        mock_executor.start_execution = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/start",
            json={
                "document_id": "doc-456",
                "document_type": "test_doc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-123"
        assert data["document_id"] == "doc-456"
        assert data["status"] == "running"

    def test_start_execution_unknown_type(self, client, mock_executor, app):
        """Start execution with unknown document type returns 400."""
        mock_executor.start_execution = AsyncMock(
            side_effect=PlanExecutorError("No workflow plan found")
        )
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/start",
            json={
                "document_id": "doc-456",
                "document_type": "unknown_type",
            },
        )

        assert response.status_code == 400
        assert "No workflow plan found" in response.json()["detail"]


class TestGetExecutionStatus:
    """Tests for GET /document-workflows/executions/{id}."""

    def test_get_status_success(self, client, mock_executor, app):
        """Get execution status successfully."""
        mock_executor.get_execution_status = AsyncMock(
            return_value={
                "execution_id": "exec-123",
                "document_id": "doc-456",
                "document_type": "test_doc",
                "workflow_id": "test_workflow",
                "status": "running",
                "current_node_id": "start",
                "terminal_outcome": None,
                "gate_outcome": None,
                "pending_user_input": False,
                "pending_prompt": None,
                "pending_choices": None,
                "escalation_active": False,
                "escalation_options": [],
                "step_count": 0,
                "created_at": "2026-01-16T12:00:00",
                "updated_at": "2026-01-16T12:00:00",
            }
        )
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.get("/api/v1/document-workflows/executions/exec-123")

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-123"
        assert data["status"] == "running"

    def test_get_status_not_found(self, client, mock_executor, app):
        """Get status for non-existent execution returns 404."""
        mock_executor.get_execution_status = AsyncMock(return_value=None)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.get("/api/v1/document-workflows/executions/nonexistent")

        assert response.status_code == 404


class TestExecuteStep:
    """Tests for POST /document-workflows/executions/{id}/step."""

    def test_execute_step_success(self, client, mock_executor, test_state, app):
        """Execute step successfully."""
        test_state.status = DocumentWorkflowStatus.COMPLETED
        test_state.terminal_outcome = "stabilized"
        mock_executor.execute_step = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post("/api/v1/document-workflows/executions/exec-123/step")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["terminal_outcome"] == "stabilized"

    def test_execute_step_pauses(self, client, mock_executor, test_state, app):
        """Execute step pauses for user input."""
        test_state.status = DocumentWorkflowStatus.PAUSED
        test_state.pending_user_input = True
        test_state.pending_prompt = "Please confirm"
        test_state.pending_choices = ["Yes", "No"]
        mock_executor.execute_step = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post("/api/v1/document-workflows/executions/exec-123/step")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["pending_user_input"] is True
        assert data["pending_prompt"] == "Please confirm"


class TestRunToCompletion:
    """Tests for POST /document-workflows/executions/{id}/run."""

    def test_run_completes(self, client, mock_executor, test_state, app):
        """Run completes workflow."""
        test_state.status = DocumentWorkflowStatus.COMPLETED
        test_state.terminal_outcome = "stabilized"
        mock_executor.run_to_completion_or_pause = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post("/api/v1/document-workflows/executions/exec-123/run")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_run_pauses(self, client, mock_executor, test_state, app):
        """Run pauses at user input."""
        test_state.status = DocumentWorkflowStatus.PAUSED
        test_state.pending_user_input = True
        mock_executor.run_to_completion_or_pause = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post("/api/v1/document-workflows/executions/exec-123/run")

        assert response.status_code == 200
        assert response.json()["status"] == "paused"


class TestSubmitUserInput:
    """Tests for POST /document-workflows/executions/{id}/input."""

    def test_submit_input_resumes(self, client, mock_executor, test_state, app):
        """Submit input resumes execution."""
        test_state.status = DocumentWorkflowStatus.COMPLETED
        mock_executor.submit_user_input = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/executions/exec-123/input",
            json={"user_choice": "Yes"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_submit_input_not_paused(self, client, mock_executor, app):
        """Submit input when not paused returns 400."""
        mock_executor.submit_user_input = AsyncMock(
            side_effect=PlanExecutorError("Execution is not paused")
        )
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/executions/exec-123/input",
            json={"user_input": "test"},
        )

        assert response.status_code == 400


class TestEscalation:
    """Tests for POST /document-workflows/executions/{id}/escalation."""

    def test_handle_escalation_abandon(self, client, mock_executor, test_state, app):
        """Handle abandon escalation."""
        test_state.status = DocumentWorkflowStatus.COMPLETED
        test_state.terminal_outcome = "abandoned"
        mock_executor.handle_escalation_choice = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/executions/exec-123/escalation",
            json={"choice": "abandon"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["terminal_outcome"] == "abandoned"

    def test_handle_escalation_retry(self, client, mock_executor, test_state, app):
        """Handle retry escalation."""
        test_state.status = DocumentWorkflowStatus.RUNNING
        test_state.escalation_active = False
        mock_executor.handle_escalation_choice = AsyncMock(return_value=test_state)
        app.dependency_overrides[get_executor] = lambda: mock_executor

        response = client.post(
            "/api/v1/document-workflows/executions/exec-123/escalation",
            json={"choice": "retry"},
        )

        assert response.status_code == 200
        assert response.json()["escalation_active"] is False


class TestListPlans:
    """Tests for GET /document-workflows/plans."""

    def test_list_plans_empty(self, client, app):
        """List plans returns empty when no plans registered."""
        with patch(
            "app.api.v1.routers.document_workflows.get_plan_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.list_plans.return_value = []
            mock_get_registry.return_value = mock_registry

            response = client.get("/api/v1/document-workflows/plans")

            assert response.status_code == 200
            assert response.json() == []

    def test_list_plans_with_data(self, client, app):
        """List plans returns registered plans."""
        with patch(
            "app.api.v1.routers.document_workflows.get_plan_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.list_plans.return_value = [make_test_plan()]
            mock_get_registry.return_value = mock_registry

            response = client.get("/api/v1/document-workflows/plans")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["workflow_id"] == "test_workflow"


class TestGetPlan:
    """Tests for GET /document-workflows/plans/{workflow_id}."""

    def test_get_plan_success(self, client, app):
        """Get plan successfully."""
        with patch(
            "app.api.v1.routers.document_workflows.get_plan_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get.return_value = make_test_plan()
            mock_get_registry.return_value = mock_registry

            response = client.get("/api/v1/document-workflows/plans/test_workflow")

            assert response.status_code == 200
            assert response.json()["workflow_id"] == "test_workflow"

    def test_get_plan_not_found(self, client, app):
        """Get non-existent plan returns 404."""
        with patch(
            "app.api.v1.routers.document_workflows.get_plan_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get.return_value = None
            mock_get_registry.return_value = mock_registry

            response = client.get("/api/v1/document-workflows/plans/nonexistent")

            assert response.status_code == 404
