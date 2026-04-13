"""Tests for MockupStorageService.

Tier-1 tests (no real DB):
- save: validates mime type
- save: validates size limits
- save: generates thumbnail for images
- save: skips thumbnail for PDFs
- save: applies default stage_hints
- load_as_base64: returns correct encoding
"""

import base64
import io

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.services.mockup_storage_service import MockupStorageService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _png_bytes(width=64, height=64):
    """Generate a minimal valid PNG image."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(width=64, height=64):
    """Generate a minimal valid JPEG image."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _pdf_bytes():
    """Generate a minimal valid PDF."""
    return b"%PDF-1.4 minimal pdf content for testing"


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestValidation:

    @pytest.mark.asyncio
    async def test_rejects_unsupported_mime_type(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        with pytest.raises(ValueError, match="Unsupported mime type"):
            await svc.save(
                project_id=MagicMock(),
                file_content=b"hello",
                mime_type="text/plain",
                label="test",
            )

    @pytest.mark.asyncio
    async def test_rejects_oversized_image(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        big_content = b"x" * (MockupStorageService.MAX_IMAGE_SIZE + 1)
        with pytest.raises(ValueError, match="Image too large"):
            await svc.save(
                project_id=MagicMock(),
                file_content=big_content,
                mime_type="image/png",
                label="test",
            )

    @pytest.mark.asyncio
    async def test_rejects_oversized_pdf(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        big_content = b"x" * (MockupStorageService.MAX_PDF_SIZE + 1)
        with pytest.raises(ValueError, match="PDF too large"):
            await svc.save(
                project_id=MagicMock(),
                file_content=big_content,
                mime_type="application/pdf",
                label="test",
            )

    @pytest.mark.asyncio
    async def test_accepts_valid_png(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _png_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/png",
            label="dashboard mock",
        )
        assert artifact.mime_type == "image/png"
        assert artifact.file_size_bytes == len(content)
        assert artifact.label == "dashboard mock"

    @pytest.mark.asyncio
    async def test_accepts_valid_jpeg(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _jpeg_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/jpeg",
            label="photo",
        )
        assert artifact.mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_accepts_valid_pdf(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _pdf_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="application/pdf",
            label="spec doc",
        )
        assert artifact.mime_type == "application/pdf"


# ---------------------------------------------------------------------------
# Thumbnail tests
# ---------------------------------------------------------------------------

class TestThumbnail:

    @pytest.mark.asyncio
    async def test_generates_thumbnail_for_png(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _png_bytes(512, 512)
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/png",
            label="big image",
        )
        assert artifact.thumbnail_content is not None
        assert len(artifact.thumbnail_content) > 0

    @pytest.mark.asyncio
    async def test_generates_thumbnail_for_jpeg(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _jpeg_bytes(512, 512)
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/jpeg",
            label="big jpeg",
        )
        assert artifact.thumbnail_content is not None

    @pytest.mark.asyncio
    async def test_skips_thumbnail_for_pdf(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _pdf_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="application/pdf",
            label="spec",
        )
        assert artifact.thumbnail_content is None


# ---------------------------------------------------------------------------
# Stage hints tests
# ---------------------------------------------------------------------------

class TestStageHints:

    @pytest.mark.asyncio
    async def test_default_stage_hints(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _png_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/png",
            label="test",
        )
        assert artifact.metadata_["stage_hints"] == [
            "project_discovery",
            "technical_architecture",
        ]

    @pytest.mark.asyncio
    async def test_custom_stage_hints(self):
        db = _mock_db()
        svc = MockupStorageService(db)
        content = _png_bytes()
        artifact = await svc.save(
            project_id=MagicMock(),
            file_content=content,
            mime_type="image/png",
            label="test",
            stage_hints=["design_review"],
        )
        assert artifact.metadata_["stage_hints"] == ["design_review"]


# ---------------------------------------------------------------------------
# Base64 encoding test
# ---------------------------------------------------------------------------

class TestBase64:

    @pytest.mark.asyncio
    async def test_load_as_base64_returns_correct_encoding(self):
        db = _mock_db()
        svc = MockupStorageService(db)

        raw_content = _png_bytes()

        # Mock the load method to return known content
        mock_artifact = MagicMock()
        mock_artifact.file_content = raw_content
        mock_artifact.mime_type = "image/png"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_artifact
        db.execute.return_value = mock_result

        encoded, mime = await svc.load_as_base64(MagicMock(), MagicMock())
        assert mime == "image/png"
        assert base64.b64decode(encoded) == raw_content
