"""Tests for evidence mode render endpoints (WS-RENDER-004).

Tier-1 tests verifying that mode=evidence:
- Single doc: prepends YAML frontmatter with source_hash
- Single doc: filename includes -evidence suffix
- Binder: includes Evidence Index table
- Binder: filename includes -evidence suffix
- Invalid mode returns 400
- Standard mode (default) has no YAML frontmatter

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


def _mock_document(display_id="PD-001", doc_type_id="project_discovery", content=None):
    d = MagicMock()
    d.id = uuid4()
    d.doc_type_id = doc_type_id
    d.display_id = display_id
    d.title = "Project Discovery"
    d.content = content or {"summary": "A brief summary"}
    d.version = 3
    d.status = "complete"
    d.lifecycle_state = "complete"
    d.created_at = None
    d.updated_at = None
    return d


def _mock_package(ia=None):
    pkg = MagicMock()
    pkg.information_architecture = ia or {
        "version": 2,
        "sections": [
            {
                "id": "s1",
                "label": "Overview",
                "binds": [{"path": "summary", "render_as": "paragraph"}],
            },
        ],
    }
    return pkg


def _create_test_app(mock_db=None):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    if mock_db is None:
        mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return app, mock_db


def _setup_single_doc_db(document):
    """Mock DB that returns a single document on scalar query."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = document
    mock_db.execute.return_value = mock_result
    return mock_db


def _setup_binder_db(documents):
    """Mock DB that returns a list of documents on scalars().all()."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = documents
    mock_db.execute.return_value = mock_result
    return mock_db


# ---------------------------------------------------------------------------
# Single document evidence mode
# ---------------------------------------------------------------------------

class TestSingleDocEvidenceMode:

    @pytest.mark.asyncio
    async def test_evidence_mode_prepends_yaml_frontmatter(self):
        """mode=evidence prepends YAML frontmatter with source_hash."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_single_doc_db(document)
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = package
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md&mode=evidence"
                )

        assert resp.status_code == 200
        text = resp.text
        assert text.startswith("---\n")
        assert "source_hash: sha256:" in text
        assert "project_id: HWCA-001" in text
        assert "display_id: PD-001" in text

    @pytest.mark.asyncio
    async def test_evidence_mode_filename_has_suffix(self):
        """mode=evidence filename includes -evidence suffix."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_single_doc_db(document)
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = package
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md&mode=evidence"
                )

        assert resp.status_code == 200
        content_disp = resp.headers.get("content-disposition", "")
        assert "HWCA-001-PD-001-evidence.md" in content_disp

    @pytest.mark.asyncio
    async def test_standard_mode_no_frontmatter(self):
        """Default mode=standard does not include YAML frontmatter."""
        project = _mock_project()
        document = _mock_document()
        package = _mock_package()
        mock_db = _setup_single_doc_db(document)
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
        assert not resp.text.startswith("---\n")

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_400(self):
        """Invalid mode value returns 400."""
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/documents/PD-001/render?format=md&mode=full"
                )

        assert resp.status_code == 400
        assert "Unsupported mode" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Binder evidence mode
# ---------------------------------------------------------------------------

class TestBinderEvidenceMode:

    @pytest.mark.asyncio
    async def test_evidence_mode_includes_evidence_index(self):
        """mode=evidence binder includes Evidence Index table."""
        project = _mock_project()
        doc = _mock_document(content={"summary": "Test"})
        package = _mock_package()
        mock_db = _setup_binder_db([doc])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = package
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md&mode=evidence"
                )

        assert resp.status_code == 200
        assert "## Evidence Index" in resp.text
        assert "| Display ID |" in resp.text

    @pytest.mark.asyncio
    async def test_evidence_mode_binder_filename_has_suffix(self):
        """mode=evidence binder filename includes -evidence suffix."""
        project = _mock_project()
        doc = _mock_document(content={"summary": "Test"})
        package = _mock_package()
        mock_db = _setup_binder_db([doc])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = package
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md&mode=evidence"
                )

        assert resp.status_code == 200
        content_disp = resp.headers.get("content-disposition", "")
        assert "HWCA-001-binder-evidence.md" in content_disp

    @pytest.mark.asyncio
    async def test_standard_mode_binder_no_evidence_index(self):
        """Default mode=standard binder does not include Evidence Index."""
        project = _mock_project()
        doc = _mock_document(content={"summary": "Test"})
        package = _mock_package()
        mock_db = _setup_binder_db([doc])
        app, _ = _create_test_app(mock_db)

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = package
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md"
                )

        assert resp.status_code == 200
        assert "## Evidence Index" not in resp.text

    @pytest.mark.asyncio
    async def test_invalid_mode_binder_returns_400(self):
        """Invalid mode on binder endpoint returns 400."""
        project = _mock_project()
        app, _ = _create_test_app()

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/projects/HWCA-001/render?scope=project&format=md&mode=full"
                )

        assert resp.status_code == 400
        assert "Unsupported mode" in resp.json()["detail"]
