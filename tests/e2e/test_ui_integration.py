"""End-to-end integration tests for UI pages with real data."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from app.core.database import get_db

from app.web.routes.admin.documents import (
    router as doc_ui_router,
    set_document_repo,
    reset_document_repo,
)
from app.web.routes.admin.dashboard import (
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
def app(doc_repo, telemetry_service, mock_admin_user):
    """Create test app with UI routers."""
    set_document_repo(doc_repo)
    set_telemetry_svc(telemetry_service)
    
    test_app = FastAPI()
    
    # Override admin requirement
    async def mock_require_admin():
        return mock_admin_user
    test_app.dependency_overrides[require_admin] = mock_require_admin
    
    # Mock database for LLMRun queries
    async def mock_get_db():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.fetchall.return_value = []
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        mock_db.execute = mock_execute
        yield mock_db
    test_app.dependency_overrides[get_db] = mock_get_db
    
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
            document_type="requirement",
            scope_type="project",
            scope_id="test-project",
            title="Test Requirement",
            content={"body": "Test requirement content"},
            status=DocumentStatus.DRAFT,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user",
        )
        await doc_repo.save(doc)
        
        response = client.get("/admin/documents?scope_type=project&scope_id=test-project")
        
        assert response.status_code == 200
        assert str(doc.document_id) in response.text
    
    @pytest.mark.asyncio
    async def test_document_detail_shows_content(self, client, doc_repo):
        """Document detail shows document content."""
        doc = StoredDocument(
            document_id=uuid4(),
            document_type="requirement",
            scope_type="project",
            scope_id="test-project",
            title="Detailed Document",
            content={"body": "# Detailed Content\n\nThis is the full content."},
            status=DocumentStatus.DRAFT,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user",
        )
        await doc_repo.save(doc)
        
        response = client.get(f"/admin/documents/{doc.document_id}")
        
        assert response.status_code == 200
        assert "Detailed Content" in response.text


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
        
        response = client.get("/admin/dashboard/costs?days=1")
        
        assert response.status_code == 200
        # Should show the tokens we logged
        assert "7,000" in response.text or "7000" in response.text