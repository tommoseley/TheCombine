"""API integration tests - verifying all endpoints work together."""

import pytest
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers.workflows import router as workflows_router
from app.api.v1.routers.documents import (
    router as documents_router,
    set_document_repository,
    reset_document_repository,
)
from app.api.v1.routers.telemetry import (
    router as telemetry_router,
    reset_telemetry_service,
)
from app.api.v1.routers.sse import sse_router
from app.api.v1.dependencies import get_workflow_registry
from app.persistence import InMemoryDocumentRepository
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    WorkflowNotFoundError,
)


class MockRegistry:
    def __init__(self):
        self._workflows = {}
    
    def add(self, wf):
        self._workflows[wf.workflow_id] = wf
    
    def get(self, wf_id):
        if wf_id not in self._workflows:
            raise WorkflowNotFoundError(wf_id)
        return self._workflows[wf_id]
    
    def list_ids(self):
        return list(self._workflows.keys())


@pytest.fixture
def workflow():
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="api_test",
        revision="1",
        effective_date="2026-01-01",
        name="API Test",
        description="Test",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={"doc": DocumentTypeConfig(name="Doc", scope="project")},
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="step1",
                scope="project",
                role="PM",
                task_prompt="Test",
                produces="doc",
                inputs=[],
            )
        ],
    )


@pytest.fixture
def registry(workflow):
    r = MockRegistry()
    r.add(workflow)
    return r


@pytest.fixture(autouse=True)
def reset():
    reset_document_repository()
    reset_telemetry_service()
    yield
    reset_document_repository()
    reset_telemetry_service()


@pytest.fixture
def app(registry):
    set_document_repository(InMemoryDocumentRepository())
    
    test_app = FastAPI()
    test_app.include_router(workflows_router, prefix="/api/v1")
    test_app.include_router(documents_router, prefix="/api/v1")
    test_app.include_router(telemetry_router, prefix="/api/v1")
    test_app.include_router(sse_router.router, prefix="/api/v1")
    
    test_app.dependency_overrides[get_workflow_registry] = lambda: registry
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestAPIEndpointsAvailable:
    """Verify all API endpoints are accessible."""
    
    def test_workflows_list(self, client):
        """GET /workflows returns 200."""
        r = client.get("/api/v1/workflows")
        assert r.status_code == 200
    
    def test_workflows_detail(self, client):
        """GET /workflows/{id} returns 200."""
        r = client.get("/api/v1/workflows/api_test")
        assert r.status_code == 200
    
    def test_workflows_step_schema(self, client):
        """GET /workflows/{id}/steps/{step}/schema returns 200."""
        r = client.get("/api/v1/workflows/api_test/steps/step1/schema")
        assert r.status_code == 200
    
    def test_documents_list(self, client):
        """GET /documents returns 200."""
        r = client.get("/api/v1/documents")
        assert r.status_code == 200
    
    def test_telemetry_summary(self, client):
        """GET /telemetry/summary returns 200."""
        r = client.get("/api/v1/telemetry/summary")
        assert r.status_code == 200
    
    def test_telemetry_daily(self, client):
        """GET /telemetry/costs/daily returns 200."""
        r = client.get("/api/v1/telemetry/costs/daily")
        assert r.status_code == 200
    
    def test_telemetry_workflow_stats(self, client):
        """GET /telemetry/workflows/{id}/stats returns 200."""
        r = client.get("/api/v1/telemetry/workflows/test/stats")
        assert r.status_code == 200


class TestAPIResponseFormats:
    """Verify API response formats are consistent."""
    
    def test_workflows_list_format(self, client):
        """Workflows list has expected structure."""
        r = client.get("/api/v1/workflows")
        data = r.json()
        
        assert "workflows" in data
        assert "total" in data
        assert isinstance(data["workflows"], list)
    
    def test_workflow_detail_format(self, client):
        """Workflow detail has expected structure."""
        r = client.get("/api/v1/workflows/api_test")
        data = r.json()
        
        assert "workflow_id" in data
        assert "name" in data
        assert "steps" in data
        assert "document_types" in data
    
    def test_documents_list_format(self, client):
        """Documents list has expected structure."""
        r = client.get("/api/v1/documents")
        data = r.json()
        
        assert "documents" in data
        assert "total" in data
    
    def test_telemetry_summary_format(self, client):
        """Telemetry summary has expected structure."""
        r = client.get("/api/v1/telemetry/summary")
        data = r.json()
        
        assert "total_calls" in data
        assert "total_cost_usd" in data
        assert "success_rate" in data


class TestAPIErrorResponses:
    """Verify error responses are consistent."""
    
    def test_404_workflow_format(self, client):
        """404 for workflow has error details."""
        r = client.get("/api/v1/workflows/nonexistent")
        
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data
    
    def test_404_document_format(self, client):
        """404 for document has error details."""
        r = client.get(f"/api/v1/documents/{uuid4()}")
        
        assert r.status_code == 404
        data = r.json()
        assert "detail" in data
    
    def test_422_invalid_uuid(self, client):
        """422 for invalid UUID format."""
        r = client.get("/api/v1/documents/bad-uuid")
        
        assert r.status_code == 422
