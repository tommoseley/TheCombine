"""Tests for correction context builder (ADR-069, WS-CORRECT-004).

Verifies:
- build_correction_text renders numbered list with provenance tags
- Multi-correction fan-in produces correct ordering
- Empty corrections returns empty string and empty list
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import InMemoryAuthorityRepository
from app.domain.services.authority_service import AuthorityService
from app.domain.services.correction_context_builder import build_correction_text


def _make_correction(project_id, stage, text, applies_to_stages=None):
    event_id = uuid4()
    return AuthorityRecordDTO(
        project_id=project_id,
        authority_type="operator_correction",
        stage=stage,
        key=f"correction:{stage}",
        value={
            "text": text,
            "applies_to_stages": applies_to_stages or [stage],
            "rewind_event_id": str(event_id),
        },
        source_execution_id=event_id,
        lineage_path_id=event_id,
        actor="operator",
        created_at=datetime.now(timezone.utc),
    )


class TestBuildCorrectionText:

    @pytest.mark.asyncio
    async def test_single_correction(self):
        """One TA correction renders as numbered item with provenance."""
        repo = InMemoryAuthorityRepository()
        service = AuthorityService(repo)
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "AI must be server-side")
        await repo.add(correction)

        text, record_ids = await build_correction_text(
            project_id=str(project_id),
            stage="TA",
            authority_service=service,
        )

        assert "1." in text
        assert "[From TA rewind]" in text
        assert "AI must be server-side" in text
        assert len(record_ids) == 1
        assert record_ids[0] == str(correction.id)

    @pytest.mark.asyncio
    async def test_multi_correction_fan_in(self):
        """PD + TA corrections for TA stage, PD first in pipeline order."""
        repo = InMemoryAuthorityRepository()
        service = AuthorityService(repo)
        project_id = uuid4()

        pd_correction = _make_correction(project_id, "PD", "Must support Python 3.12", ["PD", "TA"])
        ta_correction = _make_correction(project_id, "TA", "AI must be server-side", ["TA"])
        await repo.add(ta_correction)
        await repo.add(pd_correction)

        text, record_ids = await build_correction_text(
            project_id=str(project_id),
            stage="TA",
            authority_service=service,
        )

        assert "1." in text
        assert "2." in text
        # PD should come first (pipeline order)
        pd_pos = text.index("[From PD rewind]")
        ta_pos = text.index("[From TA rewind]")
        assert pd_pos < ta_pos
        assert len(record_ids) == 2

    @pytest.mark.asyncio
    async def test_no_corrections_returns_empty(self):
        """No corrections returns empty string and empty list."""
        repo = InMemoryAuthorityRepository()
        service = AuthorityService(repo)

        text, record_ids = await build_correction_text(
            project_id=str(uuid4()),
            stage="TA",
            authority_service=service,
        )

        assert text == ""
        assert record_ids == []

    @pytest.mark.asyncio
    async def test_non_applicable_corrections_excluded(self):
        """IP correction not returned when building for TA."""
        repo = InMemoryAuthorityRepository()
        service = AuthorityService(repo)
        project_id = uuid4()

        ip_correction = _make_correction(project_id, "IP", "IP only", ["IP"])
        await repo.add(ip_correction)

        text, record_ids = await build_correction_text(
            project_id=str(project_id),
            stage="TA",
            authority_service=service,
        )

        assert text == ""
        assert record_ids == []
