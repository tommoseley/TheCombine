"""Tests for Rewind Service (WS-REWIND-004)."""

import pytest
from uuid import uuid4

from app.domain.models.pipeline_stage import PipelineStage
from app.domain.services.lineage_service import (
    InMemoryLineageRepository,
    LineageService,
)
from app.domain.services.rewind_service import (
    RewindRequest,
    RewindService,
)
from app.persistence.models import DocumentStatus, StoredDocument
from app.persistence.repositories import InMemoryDocumentRepository


@pytest.fixture
def doc_repo():
    return InMemoryDocumentRepository()


@pytest.fixture
def lineage_repo():
    return InMemoryLineageRepository()


@pytest.fixture
def lineage_service(lineage_repo):
    return LineageService(repository=lineage_repo)


@pytest.fixture
def service(doc_repo, lineage_service):
    return RewindService(
        document_repo=doc_repo,
        lineage_service=lineage_service,
    )


@pytest.fixture
def project_id():
    return uuid4()


def _make_doc(project_id, doc_type, title="Test", status=DocumentStatus.ACTIVE):
    """Helper to create a stored document."""
    return StoredDocument.create(
        document_type=doc_type,
        scope_type="project",
        scope_id=str(project_id),
        title=title,
        content={"test": True},
        status=status,
    )


class TestRewindAtTA:
    """Rewind at TA should mark TA, IP, WP, WS documents stale."""

    @pytest.mark.asyncio
    async def test_marks_downstream_documents_stale(
        self, service, doc_repo, project_id
    ):
        # Create documents at each stage
        ci = _make_doc(project_id, "concierge_intake")
        pd = _make_doc(project_id, "project_discovery")
        ta = _make_doc(project_id, "technical_architecture")
        ip = _make_doc(project_id, "implementation_plan")
        wp = _make_doc(project_id, "work_package")
        ws = _make_doc(project_id, "work_statement")

        for doc in [ci, pd, ta, ip, wp, ws]:
            await doc_repo.save(doc)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="TA content updated",
                actor="user:tom",
            )
        )

        assert result.success
        assert result.affected_document_count == 3  # TA, WP, WS (IP is upstream of TA)
        assert result.rewind_to_stage == "TA"
        assert set(result.affected_stages) == {"TA", "WP", "WS"}

    @pytest.mark.asyncio
    async def test_preserves_upstream_documents(self, service, doc_repo, project_id):
        ci = _make_doc(project_id, "concierge_intake")
        pd = _make_doc(project_id, "project_discovery")
        ta = _make_doc(project_id, "technical_architecture")
        for doc in [ci, pd, ta]:
            await doc_repo.save(doc)

        await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="test",
                actor="test",
            )
        )

        # CI and PD should remain active
        ci_after = await doc_repo.get(ci.document_id)
        pd_after = await doc_repo.get(pd.document_id)
        assert ci_after.status == DocumentStatus.ACTIVE
        assert pd_after.status == DocumentStatus.ACTIVE


class TestRewindAtCI:
    """Rewind at CI should mark everything stale."""

    @pytest.mark.asyncio
    async def test_full_pipeline_rewind(self, service, doc_repo, project_id):
        docs = [
            _make_doc(project_id, "concierge_intake"),
            _make_doc(project_id, "project_discovery"),
            _make_doc(project_id, "technical_architecture"),
        ]
        for doc in docs:
            await doc_repo.save(doc)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.CI,
                reason="start over",
                actor="user:tom",
            )
        )

        assert result.affected_document_count == 3
        assert len(result.affected_stages) == 6  # all stages listed


class TestRewindWithNoDocuments:
    """Rewind on empty project should succeed with 0 affected."""

    @pytest.mark.asyncio
    async def test_empty_project(self, service, project_id):
        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="nothing to rewind",
                actor="test",
            )
        )
        assert result.success
        assert result.affected_document_count == 0
        assert result.stale_document_ids == []


class TestRewindSkipsAlreadyStale:
    """Already-stale documents should not be re-processed."""

    @pytest.mark.asyncio
    async def test_skips_stale_documents(self, service, doc_repo, project_id):
        active_ta = _make_doc(project_id, "technical_architecture")
        stale_ip = _make_doc(
            project_id, "implementation_plan", status=DocumentStatus.STALE
        )
        stale_ip.is_latest = False

        await doc_repo.save(active_ta)
        await doc_repo.save(stale_ip)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="test",
                actor="test",
            )
        )

        # Only the active TA should be marked stale, not the already-stale IP
        assert result.affected_document_count == 1
        assert active_ta.document_id in result.stale_document_ids


class TestLineageRecording:
    """Rewind must record a lineage event."""

    @pytest.mark.asyncio
    async def test_records_lineage_event(
        self, service, lineage_repo, project_id, doc_repo
    ):
        ta = _make_doc(project_id, "technical_architecture")
        await doc_repo.save(ta)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="TA updated",
                actor="user:tom",
            )
        )

        events = await lineage_repo.get_by_project(project_id)
        assert len(events) == 1
        assert events[0].id == result.lineage_event_id
        assert events[0].event_type == "rewind"
        assert events[0].rewind_to_stage == "TA"
        assert events[0].reason == "TA updated"
        assert events[0].actor == "user:tom"

    @pytest.mark.asyncio
    async def test_lineage_event_contains_affected_ids(
        self, service, lineage_repo, project_id, doc_repo
    ):
        ta = _make_doc(project_id, "technical_architecture")
        wp = _make_doc(project_id, "work_package")
        await doc_repo.save(ta)
        await doc_repo.save(wp)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="test",
                actor="test",
            )
        )

        events = await lineage_repo.get_by_project(project_id)
        assert set(events[0].affected_document_ids) == set(
            result.stale_document_ids
        )


class TestRewindResult:
    """RewindResult contains all required fields."""

    @pytest.mark.asyncio
    async def test_result_has_all_fields(self, service, doc_repo, project_id):
        ta = _make_doc(project_id, "technical_architecture")
        await doc_repo.save(ta)

        result = await service.execute_rewind(
            RewindRequest(
                project_id=project_id,
                rewind_to_stage=PipelineStage.TA,
                reason="test reason",
                actor="test actor",
            )
        )

        assert result.success is True
        assert result.rewind_to_stage == "TA"
        assert isinstance(result.affected_stages, list)
        assert isinstance(result.affected_document_count, int)
        assert isinstance(result.stale_document_ids, list)
        assert result.lineage_event_id is not None
