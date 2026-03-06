"""Tests for IA gate before render (WS-RENDER-003).

Tier-1 tests verifying that IA verification must pass before rendering.
- IA passes → 200, returns Markdown
- IA fails → 409, returns ia_violation JSON
- Document type with no IA → 200, renders via fallback (gate skipped)
- Binder: all pass → 200; any fail → 409 with all failures
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.projects import router
from app.core.database import get_db
from app.domain.services.ia_gate import verify_document_ia


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


def _mock_document(display_id="PD-001", doc_type_id="project_discovery", content=None):
    d = MagicMock()
    d.id = uuid4()
    d.doc_type_id = doc_type_id
    d.display_id = display_id
    d.title = "Project Discovery"
    d.content = content or {"summary": "Test"}
    d.version = 1
    d.status = "complete"
    d.lifecycle_state = "complete"
    d.created_at = None
    d.updated_at = None
    return d


def _ia(*binds):
    return {
        "version": 2,
        "sections": [{"id": "s1", "label": "Overview", "binds": list(binds)}],
    }


def _create_test_app(mock_db=None):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    if mock_db is None:
        mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return app, mock_db


# ---------------------------------------------------------------------------
# Pure verification tests
# ---------------------------------------------------------------------------

class TestVerifyDocumentIA:
    """Tests for the pure IA verification function."""

    def test_passes_when_all_fields_present(self):
        content = {"summary": "Test", "goals": ["A", "B"]}
        ia = _ia(
            {"path": "summary", "render_as": "paragraph"},
            {"path": "goals", "render_as": "list"},
        )
        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS"
        assert len(result["failures"]) == 0
        assert result["coverage"] == 1.0

    def test_passes_with_one_of_two_fields_present(self):
        """One of two fields present (50% coverage) → PASS with warnings."""
        content = {"summary": "Test"}  # missing "goals"
        ia = _ia(
            {"path": "summary", "render_as": "paragraph"},
            {"path": "goals", "render_as": "list"},
        )
        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS"
        assert len(result["warnings"]) == 1
        assert any("goals" in w for w in result["warnings"])
        assert result["coverage"] == 0.5

    def test_fails_when_no_fields_present(self):
        """No declared fields present (0% coverage) → FAIL."""
        content = {"other": "data"}  # missing both "summary" and "goals"
        ia = _ia(
            {"path": "summary", "render_as": "paragraph"},
            {"path": "goals", "render_as": "list"},
        )
        result = verify_document_ia(content, ia)
        assert result["status"] == "FAIL"
        assert len(result["failures"]) > 0
        assert result["coverage"] == 0.0

    def test_fails_below_threshold(self):
        """Below 50% coverage → FAIL."""
        content = {"a": "present"}  # 1 of 3 fields = 33%
        ia = _ia(
            {"path": "a", "render_as": "paragraph"},
            {"path": "b", "render_as": "paragraph"},
            {"path": "c", "render_as": "paragraph"},
        )
        result = verify_document_ia(content, ia)
        assert result["status"] == "FAIL"
        assert result["coverage"] < 0.5

    def test_passes_with_no_ia(self):
        """No IA definitions → SKIP (not FAIL)."""
        content = {"summary": "Test"}
        result = verify_document_ia(content, None)
        assert result["status"] == "SKIP"

    def test_passes_with_empty_sections(self):
        content = {"summary": "Test"}
        ia = {"version": 2, "sections": []}
        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS"

    def test_nested_path_verification(self):
        """Dot-separated paths are verified."""
        content = {"meta": {"author": "Tom"}}
        ia = _ia({"path": "meta.author", "render_as": "paragraph"})
        result = verify_document_ia(content, ia)
        assert result["status"] == "PASS"

    def test_nested_path_missing_fails(self):
        """Single bind, single missing → 0% coverage → FAIL."""
        content = {"meta": {}}  # missing "author" in meta
        ia = _ia({"path": "meta.author", "render_as": "paragraph"})
        result = verify_document_ia(content, ia)
        assert result["status"] == "FAIL"


# ---------------------------------------------------------------------------
# Single document render with IA gate
# ---------------------------------------------------------------------------

class TestSingleDocRenderGate:

    @pytest.mark.asyncio
    async def test_ia_passes_returns_200(self):
        """Document with valid content passes IA gate and renders."""
        project = _mock_project()
        document = _mock_document(content={"summary": "Test content"})
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = document
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = _ia(
            {"path": "summary", "render_as": "paragraph"}
        )

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-001/render?format=md")

        assert resp.status_code == 200
        assert "Test content" in resp.text

    @pytest.mark.asyncio
    async def test_ia_fails_returns_409(self):
        """Document missing IA-required fields returns 409."""
        project = _mock_project()
        document = _mock_document(content={"other_field": "value"})  # missing "summary"
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = document
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = _ia(
            {"path": "summary", "render_as": "paragraph"}
        )

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-001/render?format=md")

        assert resp.status_code == 409
        body = resp.json()
        assert body["status"] == "ia_violation"
        assert "PD-001" in body["message"]

    @pytest.mark.asyncio
    async def test_no_ia_definitions_renders_fallback(self):
        """Document type without IA definitions → gate skipped, renders via fallback."""
        project = _mock_project()
        document = _mock_document(content={"summary": "Fallback content"})
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = document
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = None  # No IA

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.domain.services.display_id_service.resolve_display_id", new_callable=AsyncMock, return_value="project_discovery"), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/documents/PD-001/render?format=md")

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Binder render with IA gate
# ---------------------------------------------------------------------------

class TestBinderRenderGate:

    @pytest.mark.asyncio
    async def test_all_docs_pass_returns_200(self):
        """Binder renders when all documents pass IA."""
        project = _mock_project()
        doc = _mock_document(content={"summary": "Test"})
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [doc]
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = _ia(
            {"path": "summary", "render_as": "paragraph"}
        )

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/render?scope=project&format=md")

        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_one_doc_fails_returns_409(self):
        """Binder returns 409 when any document fails IA."""
        project = _mock_project()
        doc = _mock_document(content={"other": "no summary"})  # missing "summary"
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [doc]
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = _ia(
            {"path": "summary", "render_as": "paragraph"}
        )

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/render?scope=project&format=md")

        assert resp.status_code == 409
        body = resp.json()
        assert body["status"] == "ia_violation"
        assert len(body["failures"]) > 0

    @pytest.mark.asyncio
    async def test_no_ia_docs_render_normally(self):
        """Documents without IA definitions don't block the binder."""
        project = _mock_project()
        doc = _mock_document(content={"summary": "Test"})
        app, mock_db = _create_test_app()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [doc]
        mock_db.execute.return_value = mock_result

        mock_pkg = MagicMock()
        mock_pkg.information_architecture = None  # No IA

        with patch("app.api.v1.routers.projects._resolve_project", new_callable=AsyncMock, return_value=project), \
             patch("app.config.package_loader.get_package_loader") as mock_loader:
            mock_loader.return_value.get_document_type.return_value = mock_pkg
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v1/projects/HWCA-001/render?scope=project&format=md")

        assert resp.status_code == 200
