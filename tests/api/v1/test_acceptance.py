"""Tests for acceptance and clarification endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
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
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
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
def mock_registry(test_workflow) -> MockWorkflowRegistry:
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


class TestAcceptance:
    """Tests for POST /executions/{id}/acceptance."""
    
    def test_submit_acceptance_approved(self, client: TestClient, app: FastAPI):
        """Accept document transitions to running."""
        # Start execution
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        # Set to waiting acceptance (via service)
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "discovery")
        
        # Submit acceptance
        response = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": True, "comment": "Looks good"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_submit_acceptance_rejected(self, client: TestClient, app: FastAPI):
        """Reject document transitions to failed."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": False, "comment": "Needs more detail"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
    
    def test_submit_acceptance_wrong_state(self, client: TestClient):
        """Accept when not waiting returns 409."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        # Don't set to waiting - still running
        response = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": True}
        )
        
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "INVALID_STATE"
    
    def test_submit_acceptance_not_found(self, client: TestClient):
        """Accept non-existent execution returns 404."""
        response = client.post(
            "/api/v1/executions/exec_nonexistent/acceptance",
            json={"accepted": True}
        )
        
        assert response.status_code == 404


class TestClarification:
    """Tests for POST /executions/{id}/clarification."""
    
    def test_submit_clarification_success(self, client: TestClient, app: FastAPI):
        """Submit answers transitions to running."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_clarification(exec_id, "discovery_step")
        
        response = client.post(
            f"/api/v1/executions/{exec_id}/clarification",
            json={"answers": {"q1": "Answer 1", "q2": "Answer 2"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_submit_clarification_wrong_state(self, client: TestClient):
        """Submit when not waiting returns 409."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        response = client.post(
            f"/api/v1/executions/{exec_id}/clarification",
            json={"answers": {"q1": "Answer"}}
        )
        
        assert response.status_code == 409
    
    def test_submit_clarification_not_found(self, client: TestClient):
        """Submit to non-existent execution returns 404."""
        response = client.post(
            "/api/v1/executions/exec_nonexistent/clarification",
            json={"answers": {"q1": "Answer"}}
        )
        
        assert response.status_code == 404


class TestResume:
    """Tests for POST /executions/{id}/resume."""
    
    def test_resume_after_acceptance(self, client: TestClient, app: FastAPI):
        """Resume after acceptance approval succeeds."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "discovery")
        
        # Accept
        client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": True}
        )
        
        # Resume
        response = client.post(f"/api/v1/executions/{exec_id}/resume")
        
        assert response.status_code == 200
        assert response.json()["status"] == "running"
    
    def test_resume_wrong_state(self, client: TestClient, app: FastAPI):
        """Resume when still waiting returns 409."""
        start_resp = client.post(
            "/api/v1/workflows/test_workflow/start",
            json={"project_id": "proj_1"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "discovery")
        
        # Don't accept - try to resume directly
        response = client.post(f"/api/v1/executions/{exec_id}/resume")
        
        assert response.status_code == 409
