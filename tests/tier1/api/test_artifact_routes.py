"""Tests for artifact API routes.

Tier-1 tests (no real DB, AsyncMock for session):
- Upload: valid file returns metadata
- Upload: wrong mime type returns 400
- Upload: too large returns 400
- List: returns metadata without binary content
- Download: returns correct content-type and bytes
- Thumbnail: returns thumbnail bytes
- Delete: removes artifact
- PATCH: updates label and stage_hints
"""

import io
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.artifacts import router
from app.core.database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _png_bytes(width=32, height=32):
    """Generate a minimal valid PNG image."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mock_artifact(
    project_id=None,
    label="dashboard mock",
    mime_type="image/png",
    file_content=None,
    thumbnail_content=None,
):
    a = MagicMock()
    a.id = uuid4()
    a.project_id = project_id or uuid4()
    a.label = label
    a.artifact_type = "mockup"
    a.mime_type = mime_type
    a.file_size_bytes = len(file_content) if file_content else 1024
    a.file_content = file_content or b"fake-content"
    a.thumbnail_content = thumbnail_content
    a.uploaded_by = None
    a.created_at = datetime(2026, 4, 2, tzinfo=timezone.utc)
    a.metadata_ = {"stage_hints": ["project_discovery", "technical_architecture"]}
    a.to_dict.return_value = {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "label": a.label,
        "artifact_type": a.artifact_type,
        "mime_type": a.mime_type,
        "file_size_bytes": a.file_size_bytes,
        "created_at": a.created_at.isoformat(),
        "uploaded_by": a.uploaded_by,
        "metadata": a.metadata_,
    }
    return a


def _create_test_app(mock_db=None, project_exists=True):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    if mock_db is None:
        mock_db = AsyncMock()
        # Default: project lookup returns a mock project (or None)
        project_result = MagicMock()
        project_result.scalars.return_value.first.return_value = MagicMock() if project_exists else None
        mock_db.execute.return_value = project_result

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return app, mock_db


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------

class TestUploadArtifact:

    @pytest.mark.asyncio
    async def test_upload_valid_file_returns_metadata(self):
        """Valid PNG upload returns 201 with metadata."""
        app, mock_db = _create_test_app()
        mock_db.add = MagicMock()
        png = _png_bytes()

        artifact = _mock_artifact(file_content=png, mime_type="image/png")

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.save.return_value = artifact
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/projects/{uuid4()}/artifacts",
                    files={"file": ("mock.png", png, "image/png")},
                    data={"label": "dashboard mock"},
                )

            assert resp.status_code == 201
            body = resp.json()
            assert body["label"] == "dashboard mock"
            assert body["mime_type"] == "image/png"
            assert "id" in body

    @pytest.mark.asyncio
    async def test_upload_wrong_mime_type_returns_400(self):
        """Upload with unsupported mime type returns 400."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.save.side_effect = ValueError("Unsupported mime type")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/projects/{uuid4()}/artifacts",
                    files={"file": ("test.txt", b"hello", "text/plain")},
                    data={"label": "bad file"},
                )

            assert resp.status_code == 400
            assert "Unsupported mime type" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_too_large_returns_400(self):
        """Upload with oversized file returns 400."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.save.side_effect = ValueError("Image too large")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/projects/{uuid4()}/artifacts",
                    files={"file": ("big.png", b"x" * 100, "image/png")},
                    data={"label": "too big"},
                )

            assert resp.status_code == 400
            assert "too large" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------

class TestListArtifacts:

    @pytest.mark.asyncio
    async def test_list_returns_metadata_without_binary(self):
        """List endpoint returns metadata dicts without file_content."""
        app, mock_db = _create_test_app()
        pid = uuid4()
        artifacts = [_mock_artifact(project_id=pid), _mock_artifact(project_id=pid)]

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.list_for_project.return_value = artifacts
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/projects/{pid}/artifacts")

            assert resp.status_code == 200
            body = resp.json()
            assert len(body) == 2
            for item in body:
                assert "id" in item
                assert "file_content" not in item
                assert "label" in item


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------

class TestDownloadArtifact:

    @pytest.mark.asyncio
    async def test_download_returns_correct_content_type(self):
        """Download serves file with correct Content-Type."""
        app, mock_db = _create_test_app()
        png = _png_bytes()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.load.return_value = (png, "image/png")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}"
                )

            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/png"
            assert resp.content == png

    @pytest.mark.asyncio
    async def test_download_not_found_returns_404(self):
        """Download of nonexistent artifact returns 404."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.load.side_effect = ValueError("not found")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}"
                )

            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Thumbnail tests
# ---------------------------------------------------------------------------

class TestThumbnail:

    @pytest.mark.asyncio
    async def test_thumbnail_returns_jpeg_bytes(self):
        """Thumbnail endpoint returns JPEG content."""
        app, mock_db = _create_test_app()
        thumb_bytes = b"fake-jpeg-thumbnail"

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.load_thumbnail.return_value = (thumb_bytes, "image/jpeg")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}/thumbnail"
                )

            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/jpeg"
            assert resp.content == thumb_bytes

    @pytest.mark.asyncio
    async def test_thumbnail_not_found_returns_404(self):
        """Thumbnail of nonexistent artifact returns 404."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.load_thumbnail.side_effect = ValueError("no thumbnail")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}/thumbnail"
                )

            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------

class TestDeleteArtifact:

    @pytest.mark.asyncio
    async def test_delete_returns_204(self):
        """Successful delete returns 204 No Content."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.delete.return_value = None
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}"
                )

            assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self):
        """Delete of nonexistent artifact returns 404."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.delete.side_effect = ValueError("not found")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}"
                )

            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH tests
# ---------------------------------------------------------------------------

class TestPatchArtifact:

    @pytest.mark.asyncio
    async def test_patch_updates_label_and_stage_hints(self):
        """PATCH updates label and stage_hints, returns updated metadata."""
        app, mock_db = _create_test_app()
        artifact = _mock_artifact(label="updated label")
        artifact.metadata_ = {"stage_hints": ["design_review"]}
        artifact.to_dict.return_value["label"] = "updated label"
        artifact.to_dict.return_value["metadata"] = {"stage_hints": ["design_review"]}

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.update.return_value = artifact
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}",
                    json={"label": "updated label", "stage_hints": ["design_review"]},
                )

            assert resp.status_code == 200
            body = resp.json()
            assert body["label"] == "updated label"
            assert body["metadata"]["stage_hints"] == ["design_review"]

    @pytest.mark.asyncio
    async def test_patch_not_found_returns_404(self):
        """PATCH of nonexistent artifact returns 404."""
        app, mock_db = _create_test_app()

        with patch(
            "app.api.v1.routers.artifacts.MockupStorageService"
        ) as MockSvc:
            svc_instance = AsyncMock()
            svc_instance.update.side_effect = ValueError("not found")
            MockSvc.return_value = svc_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    f"/api/v1/projects/{uuid4()}/artifacts/{uuid4()}",
                    json={"label": "new label"},
                )

            assert resp.status_code == 404
