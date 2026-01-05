"""Tests for human interaction forms."""

import pytest
from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import get_workflow_registry, get_persistence, clear_caches
from app.api.v1.routers.executions import reset_execution_service, get_execution_service
from app.ui.routers import pages_router, partials_router
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    WorkflowNotFoundError,
    WorkflowStatus,
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
        revision="1.0",
        effective_date="2026-01-01",
        name="Test Workflow",
        description="A test workflow",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(
                name="Discovery",
                scope="project",
                acceptance_required=True,
            ),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="step_1",
                scope="project",
                role="PM",
                task_prompt="Do step 1",
                produces="discovery",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow) -> MockWorkflowRegistry:
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def mock_persistence() -> InMemoryStatePersistence:
    return InMemoryStatePersistence()



@pytest.fixture
def mock_admin_user() -> User:
    """Create mock admin user."""
    from uuid import uuid4
    return User(
        user_id=str(uuid4()),
        email="admin@test.com",
        name="Test Admin",
        is_active=True,
        email_verified=True,
        is_admin=True,
    )

@pytest.fixture
def app(mock_registry, mock_persistence, mock_admin_user) -> FastAPI:
    clear_caches()
    reset_execution_service()
    
    test_app = FastAPI()
    
    # Override admin requirement
    async def mock_require_admin():
        return mock_admin_user
    test_app.dependency_overrides[require_admin] = mock_require_admin
    test_app.include_router(api_router)
    test_app.include_router(pages_router)
    test_app.include_router(partials_router)
    test_app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    test_app.dependency_overrides[get_persistence] = lambda: mock_persistence
    
    yield test_app
    
    test_app.dependency_overrides.clear()
    reset_execution_service()
    clear_caches()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def create_execution_and_get_service(client: TestClient, mock_persistence):
    """Helper to create an execution and return exec_id and service."""
    start_resp = client.post(
        "/admin/workflows/test_workflow/start",
        data={"project_id": "proj_test"},
        follow_redirects=False,
    )
    exec_id = start_resp.headers["location"].split("/")[-1]
    # Get the singleton service that was created during the request
    exec_service = get_execution_service(mock_persistence)
    return exec_id, exec_service


class TestAcceptanceForm:
    """Tests for acceptance form page."""
    
    def test_acceptance_form_renders_when_waiting(self, client: TestClient, mock_persistence):
        """Acceptance form renders when execution is waiting."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/admin/executions/{exec_id}/acceptance")
        assert response.status_code == 200
        assert "Review Document" in response.text
    
    def test_acceptance_form_shows_document_type(self, client: TestClient, mock_persistence):
        """Acceptance form shows which document needs review."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/admin/executions/{exec_id}/acceptance")
        assert "discovery" in response.text
    
    def test_accept_button_exists(self, client: TestClient, mock_persistence):
        """Acceptance form has approve button."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/admin/executions/{exec_id}/acceptance")
        assert "Approve" in response.text
    
    def test_reject_button_exists(self, client: TestClient, mock_persistence):
        """Acceptance form has reject button."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/admin/executions/{exec_id}/acceptance")
        assert "Reject" in response.text
    
    def test_comment_field_exists(self, client: TestClient, mock_persistence):
        """Acceptance form has optional comment field."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_acceptance(exec_id, "discovery")
        
        response = client.get(f"/admin/executions/{exec_id}/acceptance")
        assert "comment" in response.text.lower()
    
    def test_acceptance_redirects_when_not_waiting(self, client: TestClient, mock_persistence):
        """Acceptance form redirects if not in waiting state."""
        exec_id, _ = create_execution_and_get_service(client, mock_persistence)
        
        # Don't set waiting state - should redirect
        response = client.get(f"/admin/executions/{exec_id}/acceptance", follow_redirects=False)
        assert response.status_code == 303
        assert f"/admin/executions/{exec_id}" in response.headers["location"]


class TestClarificationForm:
    """Tests for clarification form page."""
    
    def test_clarification_form_renders_when_waiting(self, client: TestClient, mock_persistence):
        """Clarification form renders when execution is waiting."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_clarification(exec_id, "step_1")
        
        response = client.get(f"/admin/executions/{exec_id}/clarification")
        assert response.status_code == 200
        assert "Clarification" in response.text
    
    def test_clarification_form_shows_step(self, client: TestClient, mock_persistence):
        """Clarification form shows which step needs answers."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_clarification(exec_id, "step_1")
        
        response = client.get(f"/admin/executions/{exec_id}/clarification")
        assert "step_1" in response.text
    
    def test_clarification_submit_redirects(self, client: TestClient, mock_persistence):
        """Submitting clarification redirects to execution page."""
        exec_id, exec_service = create_execution_and_get_service(client, mock_persistence)
        exec_service.set_waiting_clarification(exec_id, "step_1")
        
        response = client.post(
            f"/admin/executions/{exec_id}/clarification",
            data={"answers[general]": "My answer"},
            follow_redirects=False,
        )
        assert response.status_code == 303
    
    def test_wrong_state_redirects(self, client: TestClient, mock_persistence):
        """Clarification form redirects if not in waiting state."""
        exec_id, _ = create_execution_and_get_service(client, mock_persistence)
        
        response = client.get(f"/admin/executions/{exec_id}/clarification", follow_redirects=False)
        assert response.status_code == 303
