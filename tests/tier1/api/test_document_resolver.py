"""Tests for Universal Document Resolver Endpoint (WS-ROUTE-001).

Tier-1 tests for GET /api/v1/projects/{project_id}/documents/{display_id}
using ADR-055 display_id resolution.

Pure business logic -- uses mocked DB via FastAPI dependency overrides.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.projects import router
from app.core.database import get_db


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_project():
    """Create a mock project."""
    project = MagicMock()
    project.id = uuid4()
    project.project_id = "HWCA-001"
    project.name = "Hardware Cluster Automation"
    return project


@pytest.fixture
def mock_document(mock_project):
    """Create a mock document with display_id."""
    doc = MagicMock()
    doc.id = uuid4()
    doc.display_id = "PD-001"
    doc.doc_type_id = "project_discovery"
    doc.title = "Project Discovery"
    doc.summary = "Discovery document summary"
    doc.content = {"preliminary_summary": {"problem_understanding": "test"}}
    doc.version = 1
    doc.status = "draft"
    doc.lifecycle_state = "active"
    doc.created_at = MagicMock()
    doc.created_at.isoformat.return_value = "2026-03-04T10:00:00"
    doc.updated_at = MagicMock()
    doc.updated_at.isoformat.return_value = "2026-03-04T10:00:00"
    doc.accepted_at = None
    doc.accepted_by = None
    doc.space_id = mock_project.id
    return doc


def _make_app_with_db(db_mock):
    """Create a FastAPI app with the projects router and overridden DB dependency."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    async def override_get_db():
        yield db_mock

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


def _setup_db_for_display_id(mock_project, mock_document=None):
    """Setup mock DB for display_id resolution path.

    Call sequence: project lookup → document lookup (via scalars().first()).
    """
    db = AsyncMock()

    # First call: project lookup (scalar_one_or_none)
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = mock_project

    # Second call: document lookup (scalars().first())
    doc_result = MagicMock()
    doc_result.scalars.return_value.first.return_value = mock_document

    db.execute = AsyncMock(side_effect=[project_result, doc_result])
    return db


def _setup_db_for_doc_type(mock_project, mock_document=None):
    """Setup mock DB for doc_type_id resolution path.

    Call sequence: project lookup → document lookup (via scalar_one_or_none).
    """
    db = AsyncMock()

    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = mock_project

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    db.execute = AsyncMock(side_effect=[project_result, doc_result])
    return db


def _setup_db_project_not_found():
    """Setup mock DB where project is not found."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


# ===========================================================================
# Display ID Resolver Tests
# ===========================================================================

class TestDocumentResolverEndpoint:
    """Tests for GET /projects/{project_id}/documents/{display_id} using display_id format."""

    @pytest.mark.asyncio
    async def test_valid_project_and_display_id_returns_200(self, mock_project, mock_document):
        """Valid project_id + valid display_id → 200 with document JSON."""
        db = _setup_db_for_display_id(mock_project, mock_document)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock, return_value="project_discovery"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_id"] == "PD-001"
        assert data["doc_type_id"] == "project_discovery"
        assert data["title"] == "Project Discovery"
        assert data["content"] is not None
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_invalid_project_id_returns_404(self):
        """Invalid project_id → 404."""
        db = _setup_db_project_not_found()
        app = _make_app_with_db(db)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/projects/NOPE-999/documents/PD-001")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unknown_display_id_returns_404(self, mock_project):
        """Valid project_id + unknown display_id → 404."""
        db = _setup_db_for_display_id(mock_project, None)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock, return_value="project_discovery"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_display_id_format_returns_400(self, mock_project):
        """display_id with valid prefix but resolve_display_id raises ValueError → 400.

        Note: identifiers that don't match display_id pattern (e.g., 'wp_wb_001')
        fall through to doc_type_id path, which returns 404 not 400.
        Only display_id-shaped identifiers with bad prefixes get 400.
        """
        db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project
        db.execute = AsyncMock(return_value=project_result)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock,
                    side_effect=ValueError("Invalid display_id format: 'BAD-001'")):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/BAD-001")

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_prefix_returns_400(self, mock_project):
        """display_id with unknown prefix → 400."""
        db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project
        db.execute = AsyncMock(return_value=project_result)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock,
                    side_effect=ValueError("Unknown display_id prefix: 'ZZZ'")):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/ZZZ-001")

        assert resp.status_code == 400
        assert "prefix" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_response_includes_required_fields(self, mock_project, mock_document):
        """Response includes display_id, doc_type_id, title, content, version."""
        db = _setup_db_for_display_id(mock_project, mock_document)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock, return_value="project_discovery"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-001")

        data = resp.json()
        required_fields = ["display_id", "doc_type_id", "title", "content", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_work_package_display_id_resolves(self, mock_project):
        """WP-001 display_id resolves correctly."""
        wp_doc = MagicMock()
        wp_doc.id = uuid4()
        wp_doc.display_id = "WP-001"
        wp_doc.doc_type_id = "work_package"
        wp_doc.title = "Work Package 1"
        wp_doc.summary = None
        wp_doc.content = {"ws_index": []}
        wp_doc.version = 1
        wp_doc.status = "governed"
        wp_doc.lifecycle_state = "active"
        wp_doc.created_at = MagicMock()
        wp_doc.created_at.isoformat.return_value = "2026-03-04T10:00:00"
        wp_doc.updated_at = None
        wp_doc.accepted_at = None
        wp_doc.accepted_by = None

        db = _setup_db_for_display_id(mock_project, wp_doc)
        app = _make_app_with_db(db)

        with patch("app.domain.services.display_id_service.resolve_display_id",
                    new_callable=AsyncMock, return_value="work_package"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/WP-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_id"] == "WP-001"
        assert data["doc_type_id"] == "work_package"


# ===========================================================================
# Existing doc_type_id path still works (regression tests)
# ===========================================================================

class TestDocTypeIdPathStillWorks:
    """Ensure the existing /{project_id}/documents/{doc_type_id} path
    continues to work for snake_case doc_type_ids."""

    @pytest.mark.asyncio
    async def test_doc_type_id_still_resolves(self, mock_project, mock_document):
        """Traditional doc_type_id path like 'project_discovery' still works."""
        db = _setup_db_for_doc_type(mock_project, mock_document)
        app = _make_app_with_db(db)

        # For doc_type_id paths, resolve_display_id is NOT called
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/projects/HWCA-001/documents/project_discovery")

        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_type_id"] == "project_discovery"

    @pytest.mark.asyncio
    async def test_doc_type_id_not_found_returns_404(self, mock_project):
        """doc_type_id that doesn't exist returns 404."""
        db = _setup_db_for_doc_type(mock_project, None)
        app = _make_app_with_db(db)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/projects/HWCA-001/documents/nonexistent_doc_type")

        assert resp.status_code == 404
