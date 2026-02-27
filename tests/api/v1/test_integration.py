"""Integration tests for workflow API - end-to-end flows."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.api.v1.services.event_broadcaster import reset_broadcaster
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
def simple_workflow() -> Workflow:
    """Simple single-step workflow."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="simple_workflow",
        revision="1",
        effective_date="2026-01-01",
        name="Simple Workflow",
        description="Single step workflow for testing",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="discovery",
                scope="project",
                role="PM",
                task_prompt="Discover requirements",
                produces="discovery",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def acceptance_workflow() -> Workflow:
    """Workflow with acceptance-required document."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="acceptance_workflow",
        revision="1",
        effective_date="2026-01-01",
        name="Acceptance Workflow",
        description="Workflow requiring document acceptance",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "proposal": DocumentTypeConfig(
                name="Proposal",
                scope="project",
                acceptance_required=True,
                accepted_by=["PM", "Stakeholder"],
            ),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="create_proposal",
                scope="project",
                role="BA",
                task_prompt="Create proposal",
                produces="proposal",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def mock_registry(simple_workflow, acceptance_workflow) -> MockWorkflowRegistry:
    """Create mock registry with test workflows."""
    registry = MockWorkflowRegistry()
    registry.add(simple_workflow)
    registry.add(acceptance_workflow)
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
    reset_broadcaster()
    
    test_app = FastAPI()
    test_app.include_router(api_router)
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    reset_broadcaster()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestFullWorkflowExecution:
    """Test complete workflow execution flows."""
    
    def test_start_and_check_status(self, client: TestClient):
        """Start workflow and verify status."""
        # Start
        start_resp = client.post(
            "/api/v1/workflows/simple_workflow/start",
            json={"project_id": "proj_int_1"}
        )
        assert start_resp.status_code == 201
        exec_id = start_resp.json()["execution_id"]
        
        # Check status
        status_resp = client.get(f"/api/v1/executions/{exec_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["execution_id"] == exec_id
        assert data["workflow_id"] == "simple_workflow"
        assert data["status"] == "running"
    
    def test_start_list_and_filter(self, client: TestClient):
        """Start multiple executions and filter list."""
        # Start executions for different projects
        client.post("/api/v1/workflows/simple_workflow/start", json={"project_id": "proj_a"})
        client.post("/api/v1/workflows/simple_workflow/start", json={"project_id": "proj_b"})
        client.post("/api/v1/workflows/acceptance_workflow/start", json={"project_id": "proj_a"})
        
        # List all
        all_resp = client.get("/api/v1/executions")
        assert all_resp.json()["total"] == 3
        
        # Filter by project
        proj_a_resp = client.get("/api/v1/executions?project_id=proj_a")
        assert proj_a_resp.json()["total"] == 2
        
        # Filter by workflow
        simple_resp = client.get("/api/v1/executions?workflow_id=simple_workflow")
        assert simple_resp.json()["total"] == 2


class TestAcceptanceFlow:
    """Test acceptance workflow flow."""
    
    def test_acceptance_approve_flow(self, client: TestClient, app: FastAPI):
        """Full flow: start -> wait acceptance -> approve -> running."""
        # Start workflow
        start_resp = client.post(
            "/api/v1/workflows/acceptance_workflow/start",
            json={"project_id": "proj_accept"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        # Simulate waiting for acceptance
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "proposal")
        
        # Verify waiting state
        status_resp = client.get(f"/api/v1/executions/{exec_id}")
        assert status_resp.json()["status"] == "waiting_acceptance"
        
        # Approve
        approve_resp = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": True, "comment": "LGTM"}
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "running"
    
    def test_acceptance_reject_flow(self, client: TestClient, app: FastAPI):
        """Full flow: start -> wait acceptance -> reject -> failed."""
        start_resp = client.post(
            "/api/v1/workflows/acceptance_workflow/start",
            json={"project_id": "proj_reject"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_acceptance(exec_id, "proposal")
        
        # Reject
        reject_resp = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": False, "comment": "Needs more detail"}
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "failed"


class TestClarificationFlow:
    """Test clarification workflow flow."""
    
    def test_clarification_answer_flow(self, client: TestClient, app: FastAPI):
        """Full flow: start -> wait clarification -> answer -> running."""
        start_resp = client.post(
            "/api/v1/workflows/simple_workflow/start",
            json={"project_id": "proj_clarify"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        svc = get_execution_service()
        svc.set_waiting_clarification(exec_id, "discovery")
        
        # Verify waiting state
        status_resp = client.get(f"/api/v1/executions/{exec_id}")
        assert status_resp.json()["status"] == "waiting_clarification"
        
        # Submit answers
        answer_resp = client.post(
            f"/api/v1/executions/{exec_id}/clarification",
            json={"answers": {"q1": "Build a todo app", "q2": "React frontend"}}
        )
        assert answer_resp.status_code == 200
        assert answer_resp.json()["status"] == "running"


class TestConcurrentExecutions:
    """Test handling of concurrent executions."""
    
    def test_multiple_concurrent_executions(self, client: TestClient):
        """Multiple executions can run independently."""
        # Start 5 executions
        exec_ids = []
        for i in range(5):
            resp = client.post(
                "/api/v1/workflows/simple_workflow/start",
                json={"project_id": f"proj_concurrent_{i}"}
            )
            exec_ids.append(resp.json()["execution_id"])
        
        # Verify all are tracked
        list_resp = client.get("/api/v1/executions")
        assert list_resp.json()["total"] == 5
        
        # Cancel one
        client.post(f"/api/v1/executions/{exec_ids[2]}/cancel")
        
        # Verify others unaffected
        for i, exec_id in enumerate(exec_ids):
            status_resp = client.get(f"/api/v1/executions/{exec_id}")
            if i == 2:
                assert status_resp.json()["status"] == "cancelled"
            else:
                assert status_resp.json()["status"] == "running"


class TestErrorResponses:
    """Test error response formats."""
    
    def test_not_found_error_format(self, client: TestClient):
        """404 errors have consistent format."""
        resp = client.get("/api/v1/executions/exec_nonexistent")
        
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert data["detail"]["error_code"] == "EXECUTION_NOT_FOUND"
        assert "message" in data["detail"]
    
    def test_conflict_error_format(self, client: TestClient, app: FastAPI):
        """409 errors have consistent format."""
        start_resp = client.post(
            "/api/v1/workflows/simple_workflow/start",
            json={"project_id": "proj_err"}
        )
        exec_id = start_resp.json()["execution_id"]
        
        # Try acceptance on non-waiting execution
        resp = client.post(
            f"/api/v1/executions/{exec_id}/acceptance",
            json={"accepted": True}
        )
        
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error_code"] == "INVALID_STATE"
    
    def test_validation_error_format(self, client: TestClient):
        """422 errors have consistent format."""
        resp = client.post(
            "/api/v1/workflows/simple_workflow/start",
            json={}  # Missing required project_id
        )
        
        assert resp.status_code == 422
