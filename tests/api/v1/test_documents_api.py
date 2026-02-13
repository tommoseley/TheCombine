"""Tests for V1 Documents API."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers.documents import (
    router,
    get_document_repository,
    set_document_repository,
    reset_document_repository,
)
from app.persistence import (
    InMemoryDocumentRepository,
    StoredDocument,
    DocumentStatus,
)


@pytest.fixture
def repo():
    """Create fresh in-memory repository."""
    return InMemoryDocumentRepository()


@pytest.fixture
def app(repo):
    """Create test app."""
    reset_document_repository()
    set_document_repository(repo)
    
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    
    yield test_app
    
    reset_document_repository()


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
        title="Test Strategy",
        content={"key": "value"},
        status=DocumentStatus.DRAFT,
    )


class TestListDocuments:
    """Tests for GET /documents."""
    
    def test_list_empty(self, client):
        """List with no documents returns empty."""
        response = client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_with_scope_filter(self, client, repo, sample_document):
        """List with scope filter returns matching documents."""
        await repo.save(sample_document)
        
        response = client.get(
            "/api/v1/documents",
            params={"scope_type": "project", "scope_id": "proj-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["title"] == "Test Strategy"
    
    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, client, repo, sample_document):
        """List with document type filter."""
        await repo.save(sample_document)
        
        response = client.get(
            "/api/v1/documents",
            params={
                "scope_type": "project",
                "scope_id": "proj-123",
                "document_type": "strategy",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestGetDocument:
    """Tests for GET /documents/{id}."""
    
    @pytest.mark.asyncio
    async def test_get_document(self, client, repo, sample_document):
        """Get existing document returns details."""
        await repo.save(sample_document)
        
        response = client.get(f"/api/v1/documents/{sample_document.document_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Strategy"
        assert data["content"] == {"key": "value"}
    
    def test_get_document_not_found(self, client):
        """Get non-existent document returns 404."""
        response = client.get(f"/api/v1/documents/{uuid4()}")
        
        assert response.status_code == 404


class TestGetDocumentByScope:
    """Tests for GET /documents/by-scope/{scope_type}/{scope_id}/{doc_type}."""
    
    @pytest.mark.asyncio
    async def test_get_by_scope(self, client, repo, sample_document):
        """Get document by scope and type."""
        await repo.save(sample_document)
        
        response = client.get("/api/v1/documents/by-scope/project/proj-123/strategy")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Strategy"
    
    def test_get_by_scope_not_found(self, client):
        """Get non-existent document returns 404."""
        response = client.get("/api/v1/documents/by-scope/project/proj-999/strategy")
        
        assert response.status_code == 404


class TestGetDocumentVersions:
    """Tests for GET /documents/by-scope/.../versions."""
    
    @pytest.mark.asyncio
    async def test_get_versions(self, client, repo):
        """Get all versions of a document."""
        # Create two versions
        doc1 = StoredDocument(
            document_id=uuid4(),
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            version=1,
            title="V1",
            content={},
            is_latest=False,
        )
        doc2 = StoredDocument(
            document_id=uuid4(),
            document_type="strategy",
            scope_type="project",
            scope_id="proj-123",
            version=2,
            title="V2",
            content={},
            is_latest=True,
        )
        await repo.save(doc1)
        await repo.save(doc2)
        
        response = client.get("/api/v1/documents/by-scope/project/proj-123/strategy/versions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["versions"][0]["version"] == 2  # Sorted newest first
        assert data["versions"][1]["version"] == 1
