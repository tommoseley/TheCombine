"""Tests for document UI pages."""

import pytest
from uuid import uuid4
from datetime import datetime, UTC

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ui.routers.documents import (
    router,
    set_document_repo,
    reset_document_repo,
)
from app.persistence import (
    InMemoryDocumentRepository,
    StoredDocument,
    DocumentStatus,
)


@pytest.fixture(autouse=True)
def reset_repo():
    """Reset document repo before each test."""
    reset_document_repo()
    yield
    reset_document_repo()


@pytest.fixture
def repo():
    """Create fresh in-memory repository."""
    return InMemoryDocumentRepository()


@pytest.fixture
def app(repo):
    """Create test app."""
    set_document_repo(repo)
    
    test_app = FastAPI()
    test_app.include_router(router)
    
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def sample_document():
    """Create a sample document."""
    return StoredDocument(
        document_id=uuid4(),
        document_type="strategy",
        scope_type="project",
        scope_id="proj-123",
        version=1,
        title="Test Strategy Document",
        content={"objectives": ["Build MVP", "Launch product"]},
        status=DocumentStatus.ACTIVE,
        summary="A test document for strategy",
        is_latest=True,
    )


class TestDocumentList:
    """Tests for document list page."""
    
    def test_list_page_renders(self, client):
        """Document list page renders."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        assert "Documents" in response.text
    
    def test_list_empty_state(self, client):
        """List shows empty state when no scope filter."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        assert "No documents found" in response.text
    
    @pytest.mark.asyncio
    async def test_list_with_documents(self, client, repo, sample_document):
        """List shows documents when filtered."""
        await repo.save(sample_document)
        
        response = client.get(
            "/documents",
            params={
                "scope_type": "project",
                "scope_id": "proj-123",
            }
        )
        
        assert response.status_code == 200
        assert "Test Strategy Document" in response.text
    
    @pytest.mark.asyncio
    async def test_list_filter_by_type(self, client, repo, sample_document):
        """List filters by document type."""
        await repo.save(sample_document)
        
        response = client.get(
            "/documents",
            params={
                "scope_type": "project",
                "scope_id": "proj-123",
                "document_type": "strategy",
            }
        )
        
        assert response.status_code == 200
        assert "Test Strategy Document" in response.text


class TestDocumentDetail:
    """Tests for document detail page."""
    
    @pytest.mark.asyncio
    async def test_detail_page_renders(self, client, repo, sample_document):
        """Document detail page renders."""
        await repo.save(sample_document)
        
        response = client.get(f"/documents/{sample_document.document_id}")
        
        assert response.status_code == 200
        assert "Test Strategy Document" in response.text
    
    @pytest.mark.asyncio
    async def test_detail_shows_content(self, client, repo, sample_document):
        """Detail page shows document content."""
        await repo.save(sample_document)
        
        response = client.get(f"/documents/{sample_document.document_id}")
        
        assert response.status_code == 200
        assert "Build MVP" in response.text
    
    @pytest.mark.asyncio
    async def test_detail_shows_metadata(self, client, repo, sample_document):
        """Detail page shows document metadata."""
        await repo.save(sample_document)
        
        response = client.get(f"/documents/{sample_document.document_id}")
        
        assert response.status_code == 200
        assert "strategy" in response.text
        assert "project" in response.text
    
    def test_detail_not_found(self, client):
        """Detail returns 404 for non-existent document."""
        response = client.get(f"/documents/{uuid4()}")
        
        assert response.status_code == 404
    
    def test_detail_invalid_uuid(self, client):
        """Detail returns 400 for invalid UUID."""
        response = client.get("/documents/not-a-uuid")
        
        assert response.status_code == 400


class TestDocumentVersions:
    """Tests for document versions page."""
    
    @pytest.mark.asyncio
    async def test_versions_page_renders(self, client, repo, sample_document):
        """Versions page renders."""
        await repo.save(sample_document)
        
        response = client.get(f"/documents/{sample_document.document_id}/versions")
        
        assert response.status_code == 200
        assert "Version History" in response.text
    
    @pytest.mark.asyncio
    async def test_versions_shows_all_versions(self, client, repo):
        """Versions page shows all document versions."""
        doc_id_1 = uuid4()
        doc_id_2 = uuid4()
        
        doc1 = StoredDocument(
            document_id=doc_id_1,
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            version=1,
            title="Strategy v1",
            content={},
            is_latest=False,
        )
        doc2 = StoredDocument(
            document_id=doc_id_2,
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            version=2,
            title="Strategy v2",
            content={},
            is_latest=True,
        )
        
        await repo.save(doc1)
        await repo.save(doc2)
        
        response = client.get(f"/documents/{doc_id_2}/versions")
        
        assert response.status_code == 200
        assert "v1" in response.text
        assert "v2" in response.text
    
    def test_versions_not_found(self, client):
        """Versions returns 404 for non-existent document."""
        response = client.get(f"/documents/{uuid4()}/versions")
        
        assert response.status_code == 404
