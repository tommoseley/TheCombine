"""Tests for operator correction authority (ADR-069, WS-CORRECT-001).

Verifies:
- get_authority_bundle includes all current corrections (project-scoped, unfiltered)
- get_corrections_for_stage filters by applicability (stage match + applies_to_stages)
- get_corrections_for_stage returns deterministic pipeline-order sorting
- get_current_correction returns single correction for originating stage
- Superseded corrections excluded from all queries
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import InMemoryAuthorityRepository
from app.domain.services.authority_service import AuthorityService


def _make_service() -> tuple:
    repo = InMemoryAuthorityRepository()
    service = AuthorityService(repo)
    return service, repo


def _make_correction(
    project_id, stage, text, applies_to_stages=None, created_at=None, status="current",
):
    """Helper to create an operator_correction authority record."""
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
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
    )


class TestGetAuthorityBundleWithCorrections:
    """Bundle includes all current corrections, project-scoped."""

    @pytest.mark.asyncio
    async def test_bundle_empty_corrections_when_none_exist(self):
        """Bundle returns operator_corrections: [] when no corrections."""
        service, _ = _make_service()
        bundle = await service.get_authority_bundle(uuid4())
        assert bundle["operator_corrections"] == []

    @pytest.mark.asyncio
    async def test_bundle_includes_all_corrections_unfiltered(self):
        """Bundle returns ALL current corrections for the project (no stage filtering)."""
        service, repo = _make_service()
        project_id = uuid4()

        ta_correction = _make_correction(project_id, "TA", "AI must be server-side", ["TA", "IP"])
        ip_correction = _make_correction(project_id, "IP", "All WPs need deploy step", ["IP"])
        await repo.add(ta_correction)
        await repo.add(ip_correction)

        bundle = await service.get_authority_bundle(project_id)
        corrections = bundle["operator_corrections"]

        assert len(corrections) == 2
        texts = [c["text"] for c in corrections]
        assert "AI must be server-side" in texts
        assert "All WPs need deploy step" in texts

    @pytest.mark.asyncio
    async def test_bundle_excludes_superseded_corrections(self):
        """Superseded corrections not in bundle."""
        service, repo = _make_service()
        project_id = uuid4()

        superseded = _make_correction(project_id, "TA", "Old correction", status="superseded")
        current = _make_correction(project_id, "TA", "New correction")
        await repo.add(superseded)
        await repo.add(current)

        bundle = await service.get_authority_bundle(project_id)
        corrections = bundle["operator_corrections"]

        assert len(corrections) == 1
        assert corrections[0]["text"] == "New correction"

    @pytest.mark.asyncio
    async def test_bundle_corrections_sorted_by_pipeline_order(self):
        """Corrections sorted by pipeline stage order, not insertion order."""
        service, repo = _make_service()
        project_id = uuid4()

        # Insert IP first, then PD — but PD should come first in output (pipeline order)
        ip_correction = _make_correction(project_id, "IP", "IP correction")
        pd_correction = _make_correction(project_id, "PD", "PD correction")
        await repo.add(ip_correction)
        await repo.add(pd_correction)

        bundle = await service.get_authority_bundle(project_id)
        corrections = bundle["operator_corrections"]

        assert len(corrections) == 2
        assert corrections[0]["origin_stage"] == "PD"
        assert corrections[1]["origin_stage"] == "IP"

    @pytest.mark.asyncio
    async def test_bundle_corrections_include_record_ids(self):
        """Each correction entry has authority_record_id."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "Server-side only")
        await repo.add(correction)

        bundle = await service.get_authority_bundle(project_id)
        assert bundle["operator_corrections"][0]["authority_record_id"] == correction.id

    @pytest.mark.asyncio
    async def test_bundle_correction_ids_in_authority_record_ids(self):
        """Correction record IDs appear in the bundle's authority_record_ids list."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "Server-side only")
        await repo.add(correction)

        bundle = await service.get_authority_bundle(project_id)
        assert correction.id in bundle["authority_record_ids"]


class TestGetCorrectionsForStage:
    """Stage-aware filtering with deterministic ordering."""

    @pytest.mark.asyncio
    async def test_returns_direct_match(self):
        """Correction with stage=TA returned when querying for TA."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "Server-side only", ["TA"])
        await repo.add(correction)

        results = await service.get_corrections_for_stage(project_id, "TA")
        assert len(results) == 1
        assert results[0].id == correction.id

    @pytest.mark.asyncio
    async def test_returns_applies_to_match(self):
        """TA correction with applies_to_stages=["TA","IP"] returned when querying IP."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "Server-side only", ["TA", "IP"])
        await repo.add(correction)

        results = await service.get_corrections_for_stage(project_id, "IP")
        assert len(results) == 1
        assert results[0].id == correction.id

    @pytest.mark.asyncio
    async def test_excludes_non_applicable(self):
        """IP correction with applies_to_stages=["IP"] NOT returned when querying TA."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "IP", "IP only correction", ["IP"])
        await repo.add(correction)

        results = await service.get_corrections_for_stage(project_id, "TA")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fan_in_ordering(self):
        """PD + TA corrections both applicable to TA, PD first (pipeline order).

        Pipeline order: CI(0) > PD(1) > IP(2) > TA(3) > WP(4) > WS(5).
        A PD correction with applies_to_stages=["PD","TA"] plus a TA correction
        should return PD first, then TA.
        """
        service, repo = _make_service()
        project_id = uuid4()

        pd_correction = _make_correction(project_id, "PD", "PD correction", ["PD", "TA"])
        ta_correction = _make_correction(project_id, "TA", "TA correction", ["TA"])
        await repo.add(ta_correction)  # insert TA first
        await repo.add(pd_correction)  # insert PD second

        results = await service.get_corrections_for_stage(project_id, "TA")
        assert len(results) == 2
        assert results[0].stage == "PD"  # PD before TA in pipeline order
        assert results[1].stage == "TA"

    @pytest.mark.asyncio
    async def test_same_stage_ordered_by_created_at(self):
        """Multiple corrections from same stage (shouldn't happen with supersession, but tests ordering)."""
        service, repo = _make_service()
        project_id = uuid4()

        # Use different keys to avoid supersession collision
        earlier = AuthorityRecordDTO(
            project_id=project_id,
            authority_type="operator_correction",
            stage="TA",
            key="correction:TA:sub1",
            value={"text": "Earlier", "applies_to_stages": ["TA"]},
            source_execution_id=uuid4(), lineage_path_id=uuid4(), actor="operator",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        later = AuthorityRecordDTO(
            project_id=project_id,
            authority_type="operator_correction",
            stage="TA",
            key="correction:TA:sub2",
            value={"text": "Later", "applies_to_stages": ["TA"]},
            source_execution_id=uuid4(), lineage_path_id=uuid4(), actor="operator",
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        await repo.add(later)
        await repo.add(earlier)

        results = await service.get_corrections_for_stage(project_id, "TA")
        assert len(results) == 2
        assert results[0].value["text"] == "Earlier"
        assert results[1].value["text"] == "Later"

    @pytest.mark.asyncio
    async def test_excludes_superseded(self):
        """Superseded corrections not returned."""
        service, repo = _make_service()
        project_id = uuid4()

        superseded = _make_correction(project_id, "TA", "Old", status="superseded")
        current = _make_correction(project_id, "TA", "New")
        await repo.add(superseded)
        await repo.add(current)

        results = await service.get_corrections_for_stage(project_id, "TA")
        assert len(results) == 1
        assert results[0].value["text"] == "New"

    @pytest.mark.asyncio
    async def test_empty_when_no_corrections(self):
        """Returns empty list when no corrections exist."""
        service, _ = _make_service()
        results = await service.get_corrections_for_stage(uuid4(), "TA")
        assert results == []


class TestGetCurrentCorrection:
    """Pre-population lookup for single originating stage."""

    @pytest.mark.asyncio
    async def test_returns_current_correction(self):
        """Returns the current correction for an originating stage."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "TA", "Server-side only")
        await repo.add(correction)

        result = await service.get_current_correction(project_id, "TA")
        assert result is not None
        assert result.id == correction.id
        assert result.value["text"] == "Server-side only"

    @pytest.mark.asyncio
    async def test_returns_none_when_absent(self):
        """Returns None when no correction exists for the stage."""
        service, _ = _make_service()
        result = await service.get_current_correction(uuid4(), "TA")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_latest_after_supersession(self):
        """After supersession, returns the new correction, not the old."""
        service, repo = _make_service()
        project_id = uuid4()
        event_id = uuid4()

        # Record first, then supersede with second
        await service.record_authority(
            project_id=project_id,
            authority_type="operator_correction",
            stage="TA",
            key="correction:TA",
            value={"text": "First correction", "applies_to_stages": ["TA"], "rewind_event_id": str(event_id)},
            source_execution_id=event_id,
            lineage_path_id=event_id,
            actor="operator",
        )

        event_id2 = uuid4()
        await service.record_authority(
            project_id=project_id,
            authority_type="operator_correction",
            stage="TA",
            key="correction:TA",
            value={"text": "Updated correction", "applies_to_stages": ["TA"], "rewind_event_id": str(event_id2)},
            source_execution_id=event_id2,
            lineage_path_id=event_id2,
            actor="operator",
        )

        result = await service.get_current_correction(project_id, "TA")
        assert result is not None
        assert result.value["text"] == "Updated correction"

    @pytest.mark.asyncio
    async def test_does_not_return_other_stages(self):
        """Correction for IP not returned when querying TA."""
        service, repo = _make_service()
        project_id = uuid4()

        correction = _make_correction(project_id, "IP", "IP correction")
        await repo.add(correction)

        result = await service.get_current_correction(project_id, "TA")
        assert result is None
