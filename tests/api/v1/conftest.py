"""Test fixtures for API tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.api.v1.dependencies import (
    get_workflow_registry,
    clear_caches,
)
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    EntityTypeConfig,
    WorkflowNotFoundError,
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
        """List all workflow IDs."""
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
        description="A test workflow for API testing",
        scopes={
            "project": ScopeConfig(parent=None),
            "epic": ScopeConfig(parent="project"),
        },
        document_types={
            "discovery": DocumentTypeConfig(
                name="Project Discovery",
                scope="project",
            ),
            "backlog": DocumentTypeConfig(
                name="Epic Backlog",
                scope="project",
                acceptance_required=True,
                accepted_by=["PM"],
            ),
        },
        entity_types={
            "epic": EntityTypeConfig(
                name="Epic",
                parent_doc_type="backlog",
                creates_scope="epic",
            ),
        },
        steps=[
            WorkflowStep(
                step_id="discovery_step",
                scope="project",
                role="PM",
                task_prompt="Discover",
                produces="discovery",
                inputs=[],
            ),
            WorkflowStep(
                step_id="backlog_step",
                scope="project",
                role="PM",
                task_prompt="Create backlog",
                produces="backlog",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow: Workflow) -> MockWorkflowRegistry:
    """Create a mock registry with test workflow."""
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def app(mock_registry: MockWorkflowRegistry) -> FastAPI:
    """Create test FastAPI application."""
    clear_caches()
    
    test_app = FastAPI(title="Test API")
    test_app.include_router(api_router)
    
    # Override dependencies
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    
    yield test_app
    
    # Cleanup
    test_app.dependency_overrides.clear()
    clear_caches()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)
