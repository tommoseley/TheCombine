"""End-to-end workflow integration tests."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

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
    set_telemetry_service,
    reset_telemetry_service,
)
from app.api.v1.dependencies import get_workflow_registry
from app.persistence import (
    InMemoryDocumentRepository,
    StoredDocument,
    DocumentStatus,
)
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
)
from app.domain.workflow import (
    Workflow,
    WorkflowStep,
    ScopeConfig,
    DocumentTypeConfig,
    WorkflowNotFoundError,
)


class MockWorkflowRegistry:
    """Mock registry for E2E testing."""
    
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
    """Create a test workflow for E2E tests."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="e2e_test_workflow",
        revision="1.0",
        effective_date="2026-01-01",
        name="E2E Test Workflow",
        description="Workflow for end-to-end testing",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
            "requirements": DocumentTypeConfig(name="Requirements", scope="project"),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="discovery_step",
                scope="project",
                role="PM",
                task_prompt="Discover requirements",
                produces="discovery",
                inputs=[],
            ),
            WorkflowStep(
                step_id="requirements_step",
                scope="project",
                role="BA",
                task_prompt="Define requirements",
                produces="requirements",
                inputs=["discovery"],
            ),
        ],
    )


@pytest.fixture
def mock_registry(test_workflow) -> MockWorkflowRegistry:
    registry = MockWorkflowRegistry()
    registry.add(test_workflow)
    return registry


@pytest.fixture
def doc_repo():
    """Create document repository."""
    return InMemoryDocumentRepository()


@pytest.fixture
def telemetry_store():
    """Create telemetry store."""
    return InMemoryTelemetryStore()


@pytest.fixture
def telemetry_service(telemetry_store):
    """Create telemetry service."""
    return TelemetryService(telemetry_store)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_document_repository()
    reset_telemetry_service()
    yield
    reset_document_repository()
    reset_telemetry_service()


@pytest.fixture
def app(mock_registry, doc_repo, telemetry_service, telemetry_store):
    """Create test app with all routers."""
    set_document_repository(doc_repo)
    set_telemetry_service(telemetry_service, telemetry_store)
    
    test_app = FastAPI()
    test_app.include_router(workflows_router, prefix="/api/v1")
    test_app.include_router(documents_router, prefix="/api/v1")
    test_app.include_router(telemetry_router, prefix="/api/v1")
    
    # Override dependency
    test_app.dependency_overrides[get_workflow_registry] = lambda: mock_registry
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestWorkflowToDocumentFlow:
    """Tests for workflow -> document creation flow."""
    
    def test_workflow_list_available(self, client):
        """Workflows are listed via API."""
        response = client.get("/api/v1/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["workflows"][0]["workflow_id"] == "e2e_test_workflow"
    
    def test_workflow_detail_available(self, client):
        """Workflow details available via API."""
        response = client.get("/api/v1/workflows/e2e_test_workflow")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["steps"]) == 2
        assert "discovery" in data["document_types"]
    
    @pytest.mark.asyncio
    async def test_document_created_and_retrievable(self, client, doc_repo):
        """Documents can be created and retrieved."""
        # Create a document
        doc = StoredDocument(
            document_id=uuid4(),
            document_type="discovery",
            scope_type="project",
            scope_id="proj-e2e",
            version=1,
            title="E2E Discovery",
            content={"findings": ["test"]},
            status=DocumentStatus.ACTIVE,
        )
        await doc_repo.save(doc)
        
        # Retrieve via API
        response = client.get(f"/api/v1/documents/{doc.document_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "E2E Discovery"
        assert data["content"]["findings"] == ["test"]
    
    @pytest.mark.asyncio
    async def test_document_versions_tracked(self, client, doc_repo):
        """Document versions are tracked correctly."""
        # Create v1
        doc_v1 = StoredDocument(
            document_id=uuid4(),
            document_type="discovery",
            scope_type="project",
            scope_id="proj-e2e",
            version=1,
            title="Discovery v1",
            content={},
            is_latest=False,
        )
        await doc_repo.save(doc_v1)
        
        # Create v2
        doc_v2 = StoredDocument(
            document_id=uuid4(),
            document_type="discovery",
            scope_type="project",
            scope_id="proj-e2e",
            version=2,
            title="Discovery v2",
            content={},
            is_latest=True,
        )
        await doc_repo.save(doc_v2)
        
        # Get versions
        response = client.get(
            f"/api/v1/documents/by-scope/project/proj-e2e/discovery/versions"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["versions"][0]["version"] == 2  # Latest first


class TestTelemetryIntegration:
    """Tests for telemetry tracking across workflow."""
    
    @pytest.mark.asyncio
    async def test_costs_tracked_for_execution(self, client, telemetry_service):
        """Costs are tracked when steps execute."""
        exec_id = uuid4()
        
        # Log calls for execution
        await telemetry_service.log_call(
            call_id=uuid4(),
            execution_id=exec_id,
            step_id="discovery_step",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=250.0,
        )
        await telemetry_service.log_call(
            call_id=uuid4(),
            execution_id=exec_id,
            step_id="requirements_step",
            model="sonnet",
            input_tokens=2000,
            output_tokens=1000,
            latency_ms=350.0,
        )
        
        # Get execution costs
        response = client.get(f"/api/v1/telemetry/executions/{exec_id}/costs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["call_count"] == 2
        assert data["total_tokens"] == 4500
        assert data["total_cost_usd"] > 0
    
    def test_daily_summary_available(self, client):
        """Daily cost summary is available."""
        response = client.get("/api/v1/telemetry/costs/daily")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_cost_usd" in data
        assert "call_count" in data


class TestErrorHandling:
    """Tests for error handling across components."""
    
    def test_workflow_not_found(self, client):
        """Non-existent workflow returns 404."""
        response = client.get("/api/v1/workflows/nonexistent")
        
        assert response.status_code == 404
    
    def test_document_not_found(self, client):
        """Non-existent document returns 404."""
        response = client.get(f"/api/v1/documents/{uuid4()}")
        
        assert response.status_code == 404
    
    def test_execution_costs_not_found(self, client):
        """Non-existent execution costs returns 404."""
        response = client.get(f"/api/v1/telemetry/executions/{uuid4()}/costs")
        
        assert response.status_code == 404
    
    def test_invalid_uuid_rejected(self, client):
        """Invalid UUID format is rejected."""
        response = client.get("/api/v1/documents/not-a-uuid")
        
        assert response.status_code == 422
