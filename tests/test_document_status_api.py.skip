"""
Integration Tests for Document Status API Endpoints (ADR-007)

Tests:
- GET /projects/{project_id}/document-statuses
- POST /documents/{document_id}/accept
- POST /documents/{document_id}/reject
- DELETE /documents/{document_id}/acceptance

Uses pytest-asyncio and httpx for async testing.

Requirements:
    pip install pytest-asyncio httpx aiosqlite
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from database import get_db


# =============================================================================
# ISOLATED TEST MODELS
# =============================================================================
# These mirror the real models but don't carry legacy FK baggage

TestBase = declarative_base()


class TestDocumentType(TestBase):
    """Test-only DocumentType model."""
    __tablename__ = "document_types"
    
    doc_type_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    scope = Column(String(32), default="project")
    icon = Column(String(32))
    acceptance_required = Column(Boolean, default=False)
    accepted_by_role = Column(String(64))
    required_inputs = Column(JSON, default=list)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class TestDocument(TestBase):
    """Test-only Document model."""
    __tablename__ = "documents"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doc_type_id = Column(String(64), nullable=False)
    space_type = Column(String(32), nullable=False)
    space_id = Column(PG_UUID(as_uuid=True), nullable=False)
    version = Column(Integer, default=1)
    is_latest = Column(Boolean, default=True)
    is_stale = Column(Boolean, default=False)
    content = Column(JSON)
    
    # Acceptance fields (ADR-007)
    accepted_at = Column(DateTime(timezone=True))
    accepted_by = Column(String(128))
    rejected_at = Column(DateTime(timezone=True))
    rejected_by = Column(String(128))
    rejection_reason = Column(Text)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
async def test_db():
    """Create a fresh async in-memory database for each test."""
    # Use aiosqlite for async SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def client(test_db):
    """Create async test client with database override."""
    # Import here to avoid circular imports
    from app.api.routers.document_status_router import router
    
    app = FastAPI()
    app.include_router(router, prefix="/api")
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def seed_document_types(test_db):
    """Seed document types for testing."""
    doc_types = [
        TestDocumentType(
            doc_type_id="project_discovery",
            name="Project Discovery",
            scope="project",
            icon="search",
            acceptance_required=False,
            accepted_by_role=None,
            required_inputs=[],
            display_order=10,
            is_active=True,
        ),
        TestDocumentType(
            doc_type_id="technical_architecture",
            name="Technical Architecture",
            scope="project",
            icon="landmark",
            acceptance_required=True,
            accepted_by_role="architect",
            required_inputs=["project_discovery"],
            display_order=20,
            is_active=True,
        ),
        TestDocumentType(
            doc_type_id="epic_backlog",
            name="Epic Backlog",
            scope="project",
            icon="layers",
            acceptance_required=True,
            accepted_by_role="pm",
            required_inputs=["project_discovery"],
            display_order=30,
            is_active=True,
        ),
        TestDocumentType(
            doc_type_id="story_backlog",
            name="Story Backlog",
            scope="project",
            icon="list-checks",
            acceptance_required=False,
            accepted_by_role=None,
            required_inputs=["technical_architecture", "epic_backlog"],
            display_order=40,
            is_active=True,
        ),
    ]
    
    for dt in doc_types:
        test_db.add(dt)
    await test_db.commit()
    
    return {dt.doc_type_id: dt for dt in doc_types}


@pytest.fixture
def project_id():
    """Generate a test project ID."""
    return uuid4()


@pytest.fixture
async def seed_documents(test_db, project_id, seed_document_types):
    """Seed documents for testing."""
    # Project discovery - ready
    discovery = TestDocument(
        id=uuid4(),
        doc_type_id="project_discovery",
        space_type="project",
        space_id=project_id,
        version=1,
        is_latest=True,
        is_stale=False,
        content={"title": "Test Discovery"},
    )
    
    # Technical architecture - needs acceptance
    architecture = TestDocument(
        id=uuid4(),
        doc_type_id="technical_architecture",
        space_type="project",
        space_id=project_id,
        version=1,
        is_latest=True,
        is_stale=False,
        content={"title": "Test Architecture"},
    )
    
    test_db.add(discovery)
    test_db.add(architecture)
    await test_db.commit()
    
    return {
        "project_discovery": discovery,
        "technical_architecture": architecture,
    }


# =============================================================================
# GET /projects/{project_id}/document-statuses TESTS
# =============================================================================

class TestGetProjectDocumentStatuses:
    """Tests for document statuses endpoint."""
    
    @pytest.mark.asyncio
    async def test_returns_all_document_types(
        self, client, project_id, seed_document_types
    ):
        """Should return status for all active document types."""
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["project_id"] == str(project_id)
        assert len(data["documents"]) == 4
    
    @pytest.mark.asyncio
    async def test_returns_correct_readiness_for_empty_project(
        self, client, project_id, seed_document_types
    ):
        """Empty project: discovery=waiting, others=blocked."""
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        data = response.json()
        
        docs_by_type = {d["doc_type_id"]: d for d in data["documents"]}
        
        # Project discovery has no deps - should be waiting
        assert docs_by_type["project_discovery"]["readiness"] == "waiting"
        
        # Others need project_discovery - should be blocked
        assert docs_by_type["technical_architecture"]["readiness"] == "blocked"
        assert docs_by_type["epic_backlog"]["readiness"] == "blocked"
        assert docs_by_type["story_backlog"]["readiness"] == "blocked"
    
    @pytest.mark.asyncio
    async def test_returns_correct_status_with_documents(
        self, client, project_id, seed_documents
    ):
        """With documents: shows correct readiness and acceptance."""
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        data = response.json()
        
        docs_by_type = {d["doc_type_id"]: d for d in data["documents"]}
        
        # Discovery exists, no acceptance required
        assert docs_by_type["project_discovery"]["readiness"] == "ready"
        assert docs_by_type["project_discovery"]["acceptance_state"] is None
        assert docs_by_type["project_discovery"]["document_id"] is not None
        
        # Architecture exists, needs acceptance
        assert docs_by_type["technical_architecture"]["readiness"] == "ready"
        assert docs_by_type["technical_architecture"]["acceptance_state"] == "needs_acceptance"
        
        # Epic backlog - deps met but not built
        assert docs_by_type["epic_backlog"]["readiness"] == "waiting"
        
        # Story backlog - missing epic_backlog
        assert docs_by_type["story_backlog"]["readiness"] == "blocked"
        assert "epic_backlog" in docs_by_type["story_backlog"]["missing_inputs"]
    
    @pytest.mark.asyncio
    async def test_returns_correct_action_flags(
        self, client, project_id, seed_documents
    ):
        """Action flags should reflect current state."""
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        data = response.json()
        
        docs_by_type = {d["doc_type_id"]: d for d in data["documents"]}
        
        # Ready doc without acceptance
        discovery = docs_by_type["project_discovery"]
        assert discovery["can_build"] is False  # Already built
        assert discovery["can_accept"] is False  # No acceptance required
        assert discovery["can_use_as_input"] is True
        
        # Ready doc needing acceptance
        arch = docs_by_type["technical_architecture"]
        assert arch["can_build"] is False  # Already built
        assert arch["can_accept"] is True  # Needs acceptance
        assert arch["can_use_as_input"] is False  # Not accepted yet
    
    @pytest.mark.asyncio
    async def test_ordered_by_display_order(
        self, client, project_id, seed_document_types
    ):
        """Documents should be ordered by display_order."""
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        data = response.json()
        
        doc_type_ids = [d["doc_type_id"] for d in data["documents"]]
        
        assert doc_type_ids == [
            "project_discovery",
            "technical_architecture",
            "epic_backlog",
            "story_backlog",
        ]


# =============================================================================
# POST /documents/{document_id}/accept TESTS
# =============================================================================

class TestAcceptDocument:
    """Tests for accept document endpoint."""
    
    @pytest.mark.asyncio
    async def test_accept_document_success(
        self, client, seed_documents
    ):
        """Should successfully accept a document."""
        doc_id = seed_documents["technical_architecture"].id
        
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": "architect@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == str(doc_id)
        assert data["accepted_by"] == "architect@example.com"
        assert "accepted_at" in data
    
    @pytest.mark.asyncio
    async def test_accept_clears_rejection(
        self, client, test_db, seed_documents
    ):
        """Accepting should clear any previous rejection."""
        doc = seed_documents["technical_architecture"]
        doc.rejected_at = datetime.now(timezone.utc)
        doc.rejected_by = "reviewer@example.com"
        doc.rejection_reason = "Needs work"
        await test_db.commit()
        
        response = await client.post(
            f"/api/documents/{doc.id}/accept",
            json={"accepted_by": "architect@example.com"}
        )
        
        assert response.status_code == 200
        
        # Verify rejection cleared
        await test_db.refresh(doc)
        assert doc.rejected_at is None
        assert doc.rejected_by is None
        assert doc.rejection_reason is None
    
    @pytest.mark.asyncio
    async def test_accept_not_found(self, client, seed_document_types):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        
        response = await client.post(
            f"/api/documents/{fake_id}/accept",
            json={"accepted_by": "user@example.com"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_accept_not_required(
        self, client, seed_documents
    ):
        """Should return 400 when acceptance not required."""
        doc_id = seed_documents["project_discovery"].id
        
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": "user@example.com"}
        )
        
        assert response.status_code == 400
        assert "does not require acceptance" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_accept_validates_accepted_by(self, client, seed_documents):
        """Should validate accepted_by field."""
        doc_id = seed_documents["technical_architecture"].id
        
        # Empty string
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": ""}
        )
        assert response.status_code == 422
        
        # Missing field
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={}
        )
        assert response.status_code == 422


# =============================================================================
# POST /documents/{document_id}/reject TESTS
# =============================================================================

class TestRejectDocument:
    """Tests for reject document endpoint."""
    
    @pytest.mark.asyncio
    async def test_reject_document_success(
        self, client, seed_documents
    ):
        """Should successfully reject a document."""
        doc_id = seed_documents["technical_architecture"].id
        
        response = await client.post(
            f"/api/documents/{doc_id}/reject",
            json={
                "rejected_by": "architect@example.com",
                "reason": "Missing error handling"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == str(doc_id)
        assert data["rejected_by"] == "architect@example.com"
        assert data["reason"] == "Missing error handling"
        assert "rejected_at" in data
    
    @pytest.mark.asyncio
    async def test_reject_without_reason(
        self, client, seed_documents
    ):
        """Should allow rejection without reason."""
        doc_id = seed_documents["technical_architecture"].id
        
        response = await client.post(
            f"/api/documents/{doc_id}/reject",
            json={"rejected_by": "architect@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["reason"] is None
    
    @pytest.mark.asyncio
    async def test_reject_clears_acceptance(
        self, client, test_db, seed_documents
    ):
        """Rejecting should clear any previous acceptance."""
        doc = seed_documents["technical_architecture"]
        doc.accepted_at = datetime.now(timezone.utc)
        doc.accepted_by = "architect@example.com"
        await test_db.commit()
        
        response = await client.post(
            f"/api/documents/{doc.id}/reject",
            json={"rejected_by": "lead@example.com", "reason": "Reconsider"}
        )
        
        assert response.status_code == 200
        
        # Verify acceptance cleared
        await test_db.refresh(doc)
        assert doc.accepted_at is None
        assert doc.accepted_by is None
    
    @pytest.mark.asyncio
    async def test_reject_not_found(self, client, seed_document_types):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        
        response = await client.post(
            f"/api/documents/{fake_id}/reject",
            json={"rejected_by": "user@example.com"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_reject_not_required(
        self, client, seed_documents
    ):
        """Should return 400 when acceptance not required."""
        doc_id = seed_documents["project_discovery"].id
        
        response = await client.post(
            f"/api/documents/{doc_id}/reject",
            json={"rejected_by": "user@example.com"}
        )
        
        assert response.status_code == 400


# =============================================================================
# DELETE /documents/{document_id}/acceptance TESTS
# =============================================================================

class TestClearAcceptance:
    """Tests for clear acceptance endpoint."""
    
    @pytest.mark.asyncio
    async def test_clear_acceptance(
        self, client, test_db, seed_documents
    ):
        """Should clear acceptance state."""
        doc = seed_documents["technical_architecture"]
        doc.accepted_at = datetime.now(timezone.utc)
        doc.accepted_by = "architect@example.com"
        await test_db.commit()
        
        response = await client.delete(f"/api/documents/{doc.id}/acceptance")
        
        assert response.status_code == 204
        
        # Verify cleared
        await test_db.refresh(doc)
        assert doc.accepted_at is None
        assert doc.accepted_by is None
    
    @pytest.mark.asyncio
    async def test_clear_rejection(
        self, client, test_db, seed_documents
    ):
        """Should clear rejection state."""
        doc = seed_documents["technical_architecture"]
        doc.rejected_at = datetime.now(timezone.utc)
        doc.rejected_by = "reviewer@example.com"
        doc.rejection_reason = "Needs work"
        await test_db.commit()
        
        response = await client.delete(f"/api/documents/{doc.id}/acceptance")
        
        assert response.status_code == 204
        
        # Verify cleared
        await test_db.refresh(doc)
        assert doc.rejected_at is None
        assert doc.rejected_by is None
        assert doc.rejection_reason is None
    
    @pytest.mark.asyncio
    async def test_clear_not_found(self, client, seed_document_types):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        
        response = await client.delete(f"/api/documents/{fake_id}/acceptance")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_clear_idempotent(
        self, client, seed_documents
    ):
        """Should be idempotent - clearing already clear is OK."""
        doc_id = seed_documents["technical_architecture"].id
        
        # Clear twice
        response1 = await client.delete(f"/api/documents/{doc_id}/acceptance")
        response2 = await client.delete(f"/api/documents/{doc_id}/acceptance")
        
        assert response1.status_code == 204
        assert response2.status_code == 204


# =============================================================================
# INTEGRATION FLOW TESTS
# =============================================================================

class TestAcceptanceWorkflow:
    """Test complete acceptance workflow."""
    
    @pytest.mark.asyncio
    async def test_full_acceptance_flow(
        self, client, project_id, seed_documents
    ):
        """Test: build → needs_acceptance → accept → ready to use."""
        doc_id = seed_documents["technical_architecture"].id
        
        # 1. Initial state - needs acceptance
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        docs = {d["doc_type_id"]: d for d in response.json()["documents"]}
        
        arch = docs["technical_architecture"]
        assert arch["acceptance_state"] == "needs_acceptance"
        assert arch["can_accept"] is True
        assert arch["can_use_as_input"] is False
        
        # 2. Accept the document
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": "architect@example.com"}
        )
        assert response.status_code == 200
        
        # 3. Verify - now accepted and usable
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        docs = {d["doc_type_id"]: d for d in response.json()["documents"]}
        
        arch = docs["technical_architecture"]
        assert arch["acceptance_state"] == "accepted"
        assert arch["can_accept"] is False
        assert arch["can_use_as_input"] is True
    
    @pytest.mark.asyncio
    async def test_rejection_and_reaccept_flow(
        self, client, project_id, seed_documents
    ):
        """Test: accept → reject → re-accept."""
        doc_id = seed_documents["technical_architecture"].id
        
        # 1. Accept
        await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": "architect@example.com"}
        )
        
        # 2. Reject
        response = await client.post(
            f"/api/documents/{doc_id}/reject",
            json={"rejected_by": "lead@example.com", "reason": "Needs revision"}
        )
        assert response.status_code == 200
        
        # 3. Verify rejected state
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        docs = {d["doc_type_id"]: d for d in response.json()["documents"]}
        
        arch = docs["technical_architecture"]
        assert arch["acceptance_state"] == "rejected"
        assert arch["subtitle"] == "Changes requested"
        assert arch["can_use_as_input"] is False
        
        # 4. Re-accept after changes
        response = await client.post(
            f"/api/documents/{doc_id}/accept",
            json={"accepted_by": "architect@example.com"}
        )
        assert response.status_code == 200
        
        # 5. Verify accepted again
        response = await client.get(f"/api/projects/{project_id}/document-statuses")
        docs = {d["doc_type_id"]: d for d in response.json()["documents"]}
        
        arch = docs["technical_architecture"]
        assert arch["acceptance_state"] == "accepted"
        assert arch["can_use_as_input"] is True