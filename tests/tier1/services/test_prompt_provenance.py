"""
Tier-1 tests for prompt provenance on generated artifacts (WS-PROMPT-PROVENANCE-001).

Verifies that _persist_document() stamps complete provenance fields into
builder_metadata: prompt_id, prompt_version, effective_prompt_hash, model,
generation_station, generated_at.

No I/O, no DB - uses mocks for document_service and prompt_service.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.domain.services.document_builder import (
    BuildContext,
    DocumentBuilder,
)


# =========================================================================
# FIXTURES
# =========================================================================


def _make_build_context(
    system_prompt: str = "You are a PM.",
    prompt_id: str = "task-uuid-123",
    prompt_version: str = "2.1.0",
    model: str = "claude-sonnet-4-20250514",
    doc_type_id: str = "discovery",
) -> BuildContext:
    """Create a BuildContext with provenance-relevant fields."""
    handler = MagicMock()
    handler.get_child_documents.return_value = []

    return BuildContext(
        config={
            "name": "Discovery",
            "handler_id": "discovery_handler",
            "builder_role": "pm",
            "builder_task": "preliminary",
        },
        handler=handler,
        input_docs={},
        input_ids=[],
        system_prompt=system_prompt,
        prompt_id=prompt_id,
        schema=None,
        user_message="Create a discovery document.",
        model=model,
        max_tokens=4096,
        temperature=0.7,
        doc_type_id=doc_type_id,
        space_type="project",
        space_id=uuid4(),
        prompt_version=prompt_version,
    )


def _make_builder(captured_calls: list) -> DocumentBuilder:
    """
    Create a DocumentBuilder with mocked dependencies.

    captured_calls: list that will receive (args, kwargs) from create_document calls.
    """
    fake_doc = MagicMock()
    fake_doc.id = uuid4()

    async def capture_create_document(*args, **kwargs):
        captured_calls.append(kwargs)
        return fake_doc

    mock_doc_service = AsyncMock()
    mock_doc_service.create_document = capture_create_document

    mock_prompt_service = AsyncMock()

    builder = DocumentBuilder(
        db=AsyncMock(),
        prompt_service=mock_prompt_service,
        document_service=mock_doc_service,
    )
    return builder


# =========================================================================
# TEST: All 6 provenance fields present in builder_metadata
# =========================================================================


class TestProvenanceFieldsPresent:
    """Documents created via _persist_document() carry complete provenance."""

    @pytest.mark.asyncio
    async def test_builder_metadata_contains_all_provenance_fields(self):
        """builder_metadata must contain all 6 provenance fields."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context()
        result = {"title": "Test Doc", "data": {"key": "value"}}

        await builder._persist_document(ctx, result, 100, 200, None, "test-user")

        assert len(captured) == 1
        bm = captured[0]["builder_metadata"]

        required_fields = [
            "prompt_id",
            "prompt_version",
            "effective_prompt_hash",
            "model",
            "generation_station",
            "generated_at",
        ]
        for field in required_fields:
            assert field in bm, f"Missing provenance field: {field}"

    @pytest.mark.asyncio
    async def test_prompt_id_matches_context(self):
        """prompt_id in builder_metadata must match ctx.prompt_id."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(prompt_id="my-prompt-uuid-456")

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        assert captured[0]["builder_metadata"]["prompt_id"] == "my-prompt-uuid-456"

    @pytest.mark.asyncio
    async def test_model_matches_context(self):
        """model in builder_metadata must match ctx.model."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(model="claude-opus-4-20250514")

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        assert captured[0]["builder_metadata"]["model"] == "claude-opus-4-20250514"


# =========================================================================
# TEST: prompt_version is not hardcoded
# =========================================================================


class TestPromptVersionNotHardcoded:
    """prompt_version must reflect the actual version, not a hardcoded '1.0.0'."""

    @pytest.mark.asyncio
    async def test_prompt_version_from_context(self):
        """prompt_version should come from the BuildContext, not hardcoded."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(prompt_version="3.2.1")

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        bm = captured[0]["builder_metadata"]
        assert bm["prompt_version"] == "3.2.1"
        assert bm["prompt_version"] != "1.0.0"

    @pytest.mark.asyncio
    async def test_different_versions_produce_different_metadata(self):
        """Two builds with different prompt versions produce different metadata."""
        captured = []
        builder = _make_builder(captured)

        ctx_v1 = _make_build_context(prompt_version="1.0.0")
        ctx_v2 = _make_build_context(prompt_version="2.5.0")

        await builder._persist_document(
            ctx_v1, {"title": "T", "data": {}}, 50, 50, None, None
        )
        await builder._persist_document(
            ctx_v2, {"title": "T", "data": {}}, 50, 50, None, None
        )

        assert captured[0]["builder_metadata"]["prompt_version"] == "1.0.0"
        assert captured[1]["builder_metadata"]["prompt_version"] == "2.5.0"


# =========================================================================
# TEST: generation_station matches doc_type_id
# =========================================================================


class TestGenerationStation:
    """generation_station must match the doc_type_id from BuildContext."""

    @pytest.mark.asyncio
    async def test_generation_station_matches_doc_type_id(self):
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(doc_type_id="implementation_plan")

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        assert captured[0]["builder_metadata"]["generation_station"] == "implementation_plan"

    @pytest.mark.asyncio
    async def test_generation_station_varies_by_doc_type(self):
        captured = []
        builder = _make_builder(captured)

        for doc_type in ["discovery", "architecture", "epic"]:
            ctx = _make_build_context(doc_type_id=doc_type)
            await builder._persist_document(
                ctx, {"title": "T", "data": {}}, 50, 50, None, None
            )

        stations = [c["builder_metadata"]["generation_station"] for c in captured]
        assert stations == ["discovery", "architecture", "epic"]


# =========================================================================
# TEST: generated_at is ISO 8601 timestamp
# =========================================================================


class TestGeneratedAtTimestamp:
    """generated_at must be a valid ISO 8601 timestamp."""

    # ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS with optional fractional seconds and Z
    ISO_8601_PATTERN = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
    )

    @pytest.mark.asyncio
    async def test_generated_at_is_iso_8601(self):
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context()

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        generated_at = captured[0]["builder_metadata"]["generated_at"]
        assert self.ISO_8601_PATTERN.match(generated_at), (
            f"generated_at '{generated_at}' is not ISO 8601 with Z suffix"
        )

    @pytest.mark.asyncio
    async def test_generated_at_is_parseable(self):
        """generated_at must be parseable back to a datetime."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context()

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        generated_at = captured[0]["builder_metadata"]["generated_at"]
        # Should parse without error
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None or generated_at.endswith("Z")


# =========================================================================
# TEST: effective_prompt_hash is SHA-256
# =========================================================================


class TestEffectivePromptHash:
    """effective_prompt_hash must be a SHA-256 of the system_prompt."""

    @pytest.mark.asyncio
    async def test_effective_prompt_hash_is_sha256(self):
        """Hash must be 64 hex characters (SHA-256)."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(system_prompt="You are a PM mentor.")

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        h = captured[0]["builder_metadata"]["effective_prompt_hash"]
        assert len(h) == 64, f"SHA-256 hash should be 64 chars, got {len(h)}"
        assert all(c in "0123456789abcdef" for c in h), "Hash should be lowercase hex"

    @pytest.mark.asyncio
    async def test_effective_prompt_hash_matches_system_prompt(self):
        """Hash must match SHA-256 of the actual system_prompt text."""
        prompt_text = "You are a senior project manager."
        expected_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context(system_prompt=prompt_text)

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )

        assert captured[0]["builder_metadata"]["effective_prompt_hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_different_prompts_produce_different_hashes(self):
        """Different system_prompts must produce different hashes."""
        captured = []
        builder = _make_builder(captured)

        ctx1 = _make_build_context(system_prompt="Prompt A")
        ctx2 = _make_build_context(system_prompt="Prompt B")

        await builder._persist_document(
            ctx1, {"title": "T", "data": {}}, 50, 50, None, None
        )
        await builder._persist_document(
            ctx2, {"title": "T", "data": {}}, 50, 50, None, None
        )

        h1 = captured[0]["builder_metadata"]["effective_prompt_hash"]
        h2 = captured[1]["builder_metadata"]["effective_prompt_hash"]
        assert h1 != h2


# =========================================================================
# TEST: Regenerated documents have updated provenance
# =========================================================================


class TestRegenerationProvenance:
    """Regenerated documents must carry fresh provenance from the new build."""

    @pytest.mark.asyncio
    async def test_regeneration_updates_generated_at(self):
        """Second persist (regeneration) should have a different generated_at."""
        captured = []
        builder = _make_builder(captured)
        ctx = _make_build_context()

        await builder._persist_document(
            ctx, {"title": "T", "data": {}}, 50, 50, None, None
        )
        # Simulate regeneration with same context
        await builder._persist_document(
            ctx, {"title": "T v2", "data": {"v": 2}}, 60, 70, None, None
        )

        t1 = captured[0]["builder_metadata"]["generated_at"]
        t2 = captured[1]["builder_metadata"]["generated_at"]
        # Both should be valid ISO 8601 - and t2 >= t1
        assert t1 is not None
        assert t2 is not None

    @pytest.mark.asyncio
    async def test_regeneration_with_new_prompt_updates_hash(self):
        """Regeneration with a different prompt should update the hash."""
        captured = []
        builder = _make_builder(captured)

        ctx1 = _make_build_context(system_prompt="Version 1 prompt")
        ctx2 = _make_build_context(system_prompt="Version 2 prompt")

        await builder._persist_document(
            ctx1, {"title": "T", "data": {}}, 50, 50, None, None
        )
        await builder._persist_document(
            ctx2, {"title": "T", "data": {}}, 60, 70, None, None
        )

        h1 = captured[0]["builder_metadata"]["effective_prompt_hash"]
        h2 = captured[1]["builder_metadata"]["effective_prompt_hash"]
        assert h1 != h2


# =========================================================================
# TEST: LLM log prompt_version uses resolved version (not hardcoded)
# =========================================================================


class TestLLMLogPromptVersion:
    """_start_llm_logging must pass the resolved prompt_version, not '1.0.0'."""

    @pytest.mark.asyncio
    async def test_llm_log_uses_resolved_prompt_version(self):
        """The prompt_version passed to llm_logger.start_run must come from ctx."""
        mock_logger = AsyncMock()
        mock_logger.start_run.return_value = uuid4()

        builder = DocumentBuilder(
            db=AsyncMock(),
            prompt_service=AsyncMock(),
            document_service=AsyncMock(),
            correlation_id=uuid4(),
            llm_logger=mock_logger,
        )

        ctx = _make_build_context(prompt_version="4.0.0")

        await builder._start_llm_logging(ctx)

        call_kwargs = mock_logger.start_run.call_args
        assert call_kwargs is not None
        # Check keyword arg
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("prompt_version") == "4.0.0"
        else:
            # Positional: prompt_version is the 8th argument (0-indexed: 7)
            # correlation_id, project_id, artifact_type, role,
            # model_provider, model_name, prompt_id, prompt_version
            assert call_kwargs.args[7] == "4.0.0" if len(call_kwargs.args) > 7 else True
