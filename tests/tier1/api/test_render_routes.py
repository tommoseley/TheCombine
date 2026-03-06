"""Tests for document render endpoint (WS-RENDER-001).

Tier-1 tests for GET /projects/{project_id}/documents/{display_id}/render:
- Invalid format param returns 400
- Invalid display_id format returns 400
- Response content type is text/markdown
- Content-Disposition header has correct filename
- No DB mutations occur

Pure business logic -- uses mocked DB and PackageLoader.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.projects import router
from app.core.database import get_db


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mock_project(project_id="HWCA-001"):
    p = MagicMock()
    p.id = uuid4()
    p.project_id = project_id
    p.name = "Hello World CLI"
    p.deleted_at = None
    return p


def _mock_document(display_id="PD-001", content=None):
    d = MagicMock()
    d.id = uuid4()
    d.doc_type_id = "project_discovery"
    d.display_id = display_id
    d.title = "Project Discovery"
    d.content = content or {"summary": "A brief summary", "goals": ["Goal 1", "Goal 2"]}
    d.version = 3
    d.status = "complete"
    d.lifecycle_state = "complete"
    d.created_at = None
    d.updated_at = None
    return d


def _mock_package():
    pkg = MagicMock()
    pkg.information_architecture = {
        "version": 2,
        "sections": [
            {
                "id": "s1",
                "label": "Overview",
                "binds": [{"path": "summary", "render_as": "paragraph"}],
            },
            {
                "id": "s2",
                "label": "Goals",
                "binds": [{"path": "goals", "render_as": "list"}],
            },
        ],
    }
    return pkg


def _create_test_app(mock_db=None):
    """Create a minimal FastAPI app with the projects router + DB override."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    if mock_db is None:
        mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return app, mock_db


def _setup_db_with_document(document):
    """Create a mock DB session that returns the given document on query."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = document
    mock_db.execute.return_value = mock_result
    return mock_db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRenderFormatValidation:
    """Format param validation."""

    @pytest.mark.asyncio
    async def test_invalid_format_returns_400(self):
        """Requesting format other than 'md' returns 400."""
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=html"
                )

        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_display_id_format_returns_400(self):
        """Non-display_id identifier (snake_case) returns 400."""
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/project_discovery/render?format=md"
                )

        assert resp.status_code == 400
        assert "Invalid display_id" in resp.json()["detail"]


class TestRenderEndToEnd:
    """Full render flow with mocked DB and PackageLoader."""

    @pytest.mark.asyncio
    async def test_valid_render_returns_markdown(self):
        """Valid render request returns 200 with text/markdown and correct content."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_db_with_document(document)
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:

            mock_loader.return_value.get_document_type.return_value = package

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md"
                )

        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "## Overview" in resp.text
        assert "A brief summary" in resp.text
        assert "## Goals" in resp.text
        assert "- Goal 1" in resp.text
        assert "- Goal 2" in resp.text

    @pytest.mark.asyncio
    async def test_content_disposition_filename(self):
        """Content-Disposition header includes project_id-display_id.md filename."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_db_with_document(document)
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:

            mock_loader.return_value.get_document_type.return_value = package

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md"
                )

        assert resp.status_code == 200
        content_disp = resp.headers.get("content-disposition", "")
        assert 'HWCA-001-PD-001.md' in content_disp

    @pytest.mark.asyncio
    async def test_no_db_mutations(self):
        """Render endpoint does not write to the database."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_db_with_document(document)
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:

            mock_loader.return_value.get_document_type.return_value = package

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md"
                )

        assert resp.status_code == 200
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_nonexistent_document_returns_404(self):
        """Request for nonexistent display_id returns 404."""
        project = _mock_project()
        mock_db = _setup_db_with_document(None)  # No document found
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-999/render?format=md"
                )

        assert resp.status_code == 404
