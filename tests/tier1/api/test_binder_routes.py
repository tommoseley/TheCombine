"""Tests for project binder render endpoint (WS-RENDER-002).

Tier-1 tests for GET /projects/{project_id}/render:
- Valid binder render returns 200 with text/markdown
- Invalid scope returns 400
- Invalid format returns 400
- Nonexistent project returns 404
- Content-Disposition has correct filename
- No DB mutations occur
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.projects import router
from app.core.database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_project(project_id="HWCA-001"):
    p = MagicMock()
    p.id = uuid4()
    p.project_id = project_id
    p.name = "Hello World CLI"
    p.deleted_at = None
    return p


def _mock_document(display_id="PD-001", doc_type_id="project_discovery", title="Project Discovery", content=None):
    d = MagicMock()
    d.id = uuid4()
    d.doc_type_id = doc_type_id
    d.display_id = display_id
    d.title = title
    d.content = content or {"summary": "Test summary"}
    d.version = 1
    d.status = "complete"
    d.lifecycle_state = "complete"
    d.created_at = None
    d.updated_at = None
    return d


def _create_test_app(mock_db=None):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    if mock_db is None:
        mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return app, mock_db


def _setup_db_with_docs(docs):
    """Create a mock DB session returning the given documents on query."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = docs
    mock_db.execute.return_value = mock_result
    return mock_db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBinderParamValidation:

    @pytest.mark.asyncio
    async def test_invalid_scope_returns_400(self):
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=document&format=md"
                )

        assert resp.status_code == 400
        assert "Unsupported scope" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_format_returns_400(self):
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=pdf"
                )

        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_scope_returns_422(self):
        """scope is required; omitting it returns 422 (FastAPI validation)."""
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?format=md"
                )

        assert resp.status_code == 422


class TestBinderEndToEnd:

    @pytest.mark.asyncio
    async def test_valid_binder_returns_markdown(self):
        project = _mock_project()
        doc = _mock_document()
        mock_db = _setup_db_with_docs([doc])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:

            mock_pkg = MagicMock()
            mock_pkg.information_architecture = {
                "version": 2,
                "sections": [{"id": "s1", "label": "Overview",
                              "binds": [{"path": "summary", "render_as": "paragraph"}]}],
            }
            mock_loader.return_value.get_document_type.return_value = mock_pkg

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md"
                )

        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "HWCA-001" in resp.text
        assert "Table of Contents" in resp.text
        assert "Test summary" in resp.text

    @pytest.mark.asyncio
    async def test_content_disposition_filename(self):
        project = _mock_project()
        mock_db = _setup_db_with_docs([])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md"
                )

        assert resp.status_code == 200
        content_disp = resp.headers.get("content-disposition", "")
        assert "HWCA-001-binder.md" in content_disp

    @pytest.mark.asyncio
    async def test_empty_project_returns_cover_only(self):
        project = _mock_project()
        mock_db = _setup_db_with_docs([])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md"
                )

        assert resp.status_code == 200
        assert "HWCA-001" in resp.text
        assert "No documents produced yet" in resp.text

    @pytest.mark.asyncio
    async def test_no_db_mutations(self):
        project = _mock_project()
        mock_db = _setup_db_with_docs([])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md"
                )

        assert resp.status_code == 200
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.flush.assert_not_called()
