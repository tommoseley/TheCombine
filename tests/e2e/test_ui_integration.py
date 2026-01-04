"""End-to-end UI integration tests."""

import pytest
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ui.routers.documents import (
    router as doc_ui_router,
    set_document_repo,
    reset_document_repo,
)
from app.ui.routers.dashboard import (
    router as dashboard_ui_router,
    set_telemetry_svc,
    reset_telemetry_svc,
)
from app.persistence import (
    InMemoryDocumentRepository,
    StoredDocument,
    DocumentStatus,
)
from app.llm import (
    TelemetryService,
    InMemoryTelemetryStore,
)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_document_repo()
    reset_telemetry_svc()
    yield
    reset_document_repo()
    reset_telemetry_svc()


@pytest.fixture
def doc_repo():
    return InMemoryDocumentRepository()


@pytest.fixture
def telemetry_store():
    return InMemoryTelemetryStore()


@pytest.fixture
def telemetry_service(telemetry_store):
    return TelemetryService(telemetry_store)


@pytest.fixture
def app(doc_repo, telemetry_service):
    """Create test app with UI routers."""
    set_document_repo(doc_repo)
    set_telemetry_svc(telemetry_service)
    
    test_app = FastAPI()
    test_app.include_router(doc_ui_router)
    test_app.include_router(dashboard_ui_router)
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestDocumentUIIntegration:
    """Tests for document UI with real data."""
    
    @pytest.mark.asyncio
    async def test_document_list_shows_real_documents(self, client, doc_repo):
        """Document list UI shows actual documents."""
        # Create documents
        doc = StoredDocument(
            document_id=uuid4(),
            document_type="strategy",
            scope_type="project",
            scope_id="ui-test-proj",
            version=1,
            title="UI Test Strategy",
            content={"test": True},
            status=DocumentStatus.ACTIVE,
        )
        await doc_repo.save(doc)
        
        response = client.get(
            "/documents",
            params={"scope_type": "project", "scope_id": "ui-test-proj"}
        )
        
        assert response.status_code == 200
        assert "UI Test Strategy" in response.text
    
    @pytest.mark.asyncio
    async def test_document_detail_shows_content(self, client, doc_repo):
        """Document detail UI shows document content."""
        doc = StoredDocument(
            document_id=uuid4(),
            document_type="requirements",
            scope_type="project",
            scope_id="ui-test",
            version=1,
            title="Test Requirements",
            content={"requirements": ["REQ-001", "REQ-002"]},
            status=DocumentStatus.DRAFT,
        )
        await doc_repo.save(doc)
        
        response = client.get(f"/documents/{doc.document_id}")
        
        assert response.status_code == 200
        assert "Test Requirements" in response.text
        assert "REQ-001" in response.text
    
    @pytest.mark.asyncio
    async def test_version_history_shows_all_versions(self, client, doc_repo):
        """Version history UI shows all document versions."""
        # Create multiple versions
        doc1 = StoredDocument(
            document_id=uuid4(),
            document_type="spec",
            scope_type="project",
            scope_id="version-test",
            version=1,
            title="Spec",
            content={},
            is_latest=False,
        )
        doc2 = StoredDocument(
            document_id=uuid4(),
            document_type="spec",
            scope_type="project",
            scope_id="version-test",
            version=2,
            title="Spec",
            content={},
            is_latest=True,
        )
        await doc_repo.save(doc1)
        await doc_repo.save(doc2)
        
        response = client.get(f"/documents/{doc2.document_id}/versions")
        
        assert response.status_code == 200
        assert "v1" in response.text
        assert "v2" in response.text


class TestDashboardUIIntegration:
    """Tests for dashboard UI with real data."""
    
    @pytest.mark.asyncio
    async def test_dashboard_shows_real_costs(self, client, telemetry_service):
        """Dashboard shows actual telemetry data."""
        # Log some calls
        await telemetry_service.log_call(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="ui-test-step",
            model="sonnet",
            input_tokens=5000,
            output_tokens=2000,
            latency_ms=500.0,
        )
        
        response = client.get("/dashboard/costs?days=1")
        
        assert response.status_code == 200
        # Should show the tokens we logged
        assert "7,000" in response.text or "7000" in response.text
    
    def test_dashboard_period_selection(self, client):
        """Dashboard period selection works."""
        for days in [7, 14, 30]:
            response = client.get(f"/dashboard/costs?days={days}")
            assert response.status_code == 200


class TestCrossComponentIntegration:
    """Tests for integration across UI components."""
    
    @pytest.mark.asyncio
    async def test_document_links_work(self, client, doc_repo):
        """Links between document pages work."""
        doc = StoredDocument(
            document_id=uuid4(),
            document_type="analysis",
            scope_type="project",
            scope_id="link-test",
            version=1,
            title="Link Test",
            content={},
        )
        await doc_repo.save(doc)
        
        # Go to list
        list_response = client.get(
            "/documents",
            params={"scope_type": "project", "scope_id": "link-test"}
        )
        assert list_response.status_code == 200
        assert f"/documents/{doc.document_id}" in list_response.text
        
        # Go to detail
        detail_response = client.get(f"/documents/{doc.document_id}")
        assert detail_response.status_code == 200
        assert f"/documents/{doc.document_id}/versions" in detail_response.text
        
        # Go to versions
        versions_response = client.get(f"/documents/{doc.document_id}/versions")
        assert versions_response.status_code == 200
