"""Tests for mockup_context_builder — multimodal content block generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.services.mockup_context_builder import (
    load_mockup_content_blocks,
    MOCKUP_FRAMING,
)


def _make_artifact(label="test mock", mime_type="image/png", stage_hints=None, content=b"\x89PNG"):
    """Create a mock ProjectArtifact."""
    art = MagicMock()
    art.id = uuid4()
    art.label = label
    art.mime_type = mime_type
    art.file_content = content
    hints = stage_hints if stage_hints is not None else ["project_discovery", "technical_architecture"]
    art.metadata_ = {"stage_hints": hints}
    return art


class TestLoadMockupContentBlocks:

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_artifacts(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        blocks, ids = await load_mockup_content_blocks(str(uuid4()), "project_discovery", db)
        assert blocks == []
        assert ids == []

    @pytest.mark.asyncio
    async def test_returns_blocks_for_matching_stage(self):
        art = _make_artifact(stage_hints=["project_discovery"])
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [art]
        db.execute.return_value = result_mock

        blocks, ids = await load_mockup_content_blocks(str(uuid4()), "project_discovery", db)

        assert len(blocks) == 3  # framing text + image + label text
        assert blocks[0]["type"] == "text"
        assert MOCKUP_FRAMING in blocks[0]["text"]
        assert blocks[1]["type"] == "image"
        assert blocks[1]["source"]["media_type"] == "image/png"
        assert blocks[2]["type"] == "text"
        assert "test mock" in blocks[2]["text"]
        assert len(ids) == 1
        assert ids[0] == str(art.id)

    @pytest.mark.asyncio
    async def test_filters_by_stage_hints(self):
        art = _make_artifact(stage_hints=["technical_architecture"])
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [art]
        db.execute.return_value = result_mock

        blocks, ids = await load_mockup_content_blocks(str(uuid4()), "project_discovery", db)
        assert blocks == []
        assert ids == []

    @pytest.mark.asyncio
    async def test_includes_all_when_no_stage_hints(self):
        art = _make_artifact(stage_hints=[])
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [art]
        db.execute.return_value = result_mock

        blocks, ids = await load_mockup_content_blocks(str(uuid4()), "anything", db)
        assert len(blocks) == 3
        assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_for_invalid_project_id(self):
        db = AsyncMock()
        blocks, ids = await load_mockup_content_blocks("not-a-uuid", "project_discovery", db)
        assert blocks == []
        assert ids == []

    @pytest.mark.asyncio
    async def test_pdf_gets_text_note_not_image_block(self):
        art = _make_artifact(label="spec.pdf", mime_type="application/pdf", content=b"%PDF")
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [art]
        db.execute.return_value = result_mock

        blocks, ids = await load_mockup_content_blocks(str(uuid4()), "project_discovery", db)
        assert len(blocks) == 2  # framing + text note (no image block)
        assert "Attached:" in blocks[1]["text"]
        assert len(ids) == 1  # PDF still tracked
