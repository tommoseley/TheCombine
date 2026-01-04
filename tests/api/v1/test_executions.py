"""Tests for execution endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service
from app.api.v1.services.execution_service import ExecutionService
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    EntityTypeConfig,
    WorkflowNotFoundError,
    InMemoryStatePersistence,
)


class MockWorkflowRegistry:
    """Mock registry for testing."""
    
    def __init__(self):
        self._workflows = {}
    
    def add(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow
    
    def get(self, workflow_id: str) -> Workflow:
        if workflow_id not in self._workflows:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        return self._workflows[workflow_id]
    
    def list_ids(self) -> list:
        return list(self._workflows.keys())


@pytest.fixture
def test_workflow() -> Workflow:
    """Create a test workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test_workflow",
        revision="1",
        effective_date="2026-01-01",
        name="Test Workflow",
        description="A test workflow",
        scopes={
            "project": ScopeConfig(parent=None),
        },
        document_types={
            "discovery": DocumentTypeConfig(
                name="Discovery",
                scope="project",
            ),
            "user_input": DocumentTypeConfig(
                name="User Input",
                scope="project",
            ),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="discovery_step",
                scope="project",
                role="PM",
                task_prompt="Discover",
                produces="discovery",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow: Workflow) -> MockWorkflowRegistry:
    """Create mock registry."""
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def mock_persistence() -> InMemoryStatePersistence:
    """Create in-memory persistence."""
    return InMemoryStatePersistence()


@pytest.fixture
def app(mock_registry, mock_persistence) -> FastAPI:
    """Create test app."""
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    test_app.include_router(api_router)
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestStartWorkflow:
    """Tests for POST /workflows/{id}/start."""
    
    def test_start_workflow_success(self, client: TestClient):
        """Start workflow creates new execution."""
        response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_123"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "execution_id" in data
        assert data["execution_id"].startswith("exec_")
        assert data["workflow_id"] == "test_workflow"
        assert data["project_id"] == "proj_123"
        assert data["status"] == "running"
    
    def test_start_workflow_with_initial_context(self, client: TestClient):
        """Start workflow accepts initial context."""
        response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={
                "project_id": "proj_123",
                "initial_context": {"user_input": {"idea": "Build an app"}}
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "running"
    
    def test_start_workflow_not_found(self, client: TestClient):
        """Start non-existent workflow returns 404."""
        response = client.post(
            "/api/v1/workflows/unknown_workflow/start",
            json={"project_id": "proj_123"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "WORKFLOW_NOT_FOUND"
    
    def test_start_workflow_invalid_request(self, client: TestClient):
        """Start workflow without project_id returns 422."""
        response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={}
        )
        
        assert response.status_code == 422


class TestGetExecution:
    """Tests for GET /executions/{id}."""
    
    def test_get_execution_found(self, client: TestClient):
        """Get existing execution returns details."""
        # First create an execution
        start_response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_123"}
        )
        execution_id = start_response.json()["execution_id"]
        
        # Then get it
        response = client.get(f"/api/v1/executions/{execution_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["workflow_id"] == "test_workflow"
        assert data["project_id"] == "proj_123"
    
    def test_get_execution_not_found(self, client: TestClient):
        """Get non-existent execution returns 404."""
        response = client.get("/api/v1/executions/exec_nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "EXECUTION_NOT_FOUND"


class TestListExecutions:
    """Tests for GET /executions."""
    
    def test_list_executions_empty(self, client: TestClient):
        """List with no executions returns empty list."""
        response = client.get("/api/v1/executions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["executions"] == []
        assert data["total"] == 0
    
    def test_list_executions_with_results(self, client: TestClient):
        """List after starting executions returns them."""
        # Start two executions
        client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_2"}
        )
        
        response = client.get("/api/v1/executions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["executions"]) == 2
    
    def test_list_executions_filter_by_project(self, client: TestClient):
        """List with project filter returns matching executions."""
        # Start executions for different projects
        client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_a"}
        )
        client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_b"}
        )
        
        response = client.get("/api/v1/executions?project_id=proj_a")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["executions"][0]["project_id"] == "proj_a"


class TestCancelExecution:
    """Tests for POST /executions/{id}/cancel."""
    
    def test_cancel_execution_success(self, client: TestClient):
        """Cancel running execution succeeds."""
        # Start an execution
        start_response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_123"}
        )
        execution_id = start_response.json()["execution_id"]
        
        # Cancel it
        response = client.post(f"/api/v1/executions/{execution_id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_cancel_execution_not_found(self, client: TestClient):
        """Cancel non-existent execution returns 404."""
        response = client.post("/api/v1/executions/exec_nonexistent/cancel")
        
        assert response.status_code == 404
    
    def test_cancel_already_cancelled(self, client: TestClient):
        """Cancel already cancelled execution returns 409."""
        # Start and cancel
        start_response = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_123"}
        )
        execution_id = start_response.json()["execution_id"]
        client.post(f"/api/v1/executions/{execution_id}/cancel")
        
        # Try to cancel again
        response = client.post(f"/api/v1/executions/{execution_id}/cancel")
        
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_STATE"
