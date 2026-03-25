"""Tests for Regeneration Service precondition validation (WS-REWIND-011)."""

import pytest
from uuid import uuid4

from app.domain.models.pipeline_stage import PipelineStage
from app.domain.services.lineage_service import (
    InMemoryLineageRepository,
    LineageService,
)
from app.domain.services.regeneration_service import (
    RegenerationRequest,
    RegenerationService,
)
from app.persistence.models import DocumentStatus, StoredDocument
from app.persistence.repositories import InMemoryDocumentRepository


@pytest.fixture
def doc_repo():
    return InMemoryDocumentRepository()


@pytest.fixture
def lineage_service():
    return LineageService(repository=InMemoryLineageRepository())


@pytest.fixture
def service(doc_repo, lineage_service):
    return RegenerationService(doc_repo, lineage_service)


@pytest.fixture
def project_id():
    return uuid4()


def _make_doc(project_id, doc_type, status=DocumentStatus.ACTIVE):
    return StoredDocument.create(
        document_type=doc_type,
        scope_type="project",
        scope_id=str(project_id),
        title=f"Test {doc_type}",
        content={},
        status=status,
    )


class TestPreconditionValidation:
    """Preconditions: stale at stage + current upstream."""

    @pytest.mark.asyncio
    async def test_valid_preconditions_pass(self, service, doc_repo, project_id):
        # CI, PD, IP are current, TA is stale → regenerate from TA
        ci = _make_doc(project_id, "concierge_intake")
        pd = _make_doc(project_id, "project_discovery")
        ip = _make_doc(project_id, "implementation_plan")
        ta = _make_doc(project_id, "technical_architecture", DocumentStatus.STALE)
        ta.is_latest = False
        for doc in [ci, pd, ip, ta]:
            await doc_repo.save(doc)

        result = await service.validate_preconditions(
            RegenerationRequest(project_id, PipelineStage.TA, "user:tom")
        )
        assert result.success
        assert result.precondition_errors == []

    @pytest.mark.asyncio
    async def test_no_stale_artifacts_fails(self, service, doc_repo, project_id):
        # All current, no stale → can't regenerate
        ci = _make_doc(project_id, "concierge_intake")
        pd = _make_doc(project_id, "project_discovery")
        ta = _make_doc(project_id, "technical_architecture")
        for doc in [ci, pd, ta]:
            await doc_repo.save(doc)

        result = await service.validate_preconditions(
            RegenerationRequest(project_id, PipelineStage.TA, "user:tom")
        )
        assert not result.success
        assert any("No stale artifacts" in e for e in result.precondition_errors)

    @pytest.mark.asyncio
    async def test_missing_upstream_fails(self, service, doc_repo, project_id):
        # TA is stale but PD doesn't exist → upstream missing
        ci = _make_doc(project_id, "concierge_intake")
        ta = _make_doc(project_id, "technical_architecture", DocumentStatus.STALE)
        ta.is_latest = False
        await doc_repo.save(ci)
        await doc_repo.save(ta)

        result = await service.validate_preconditions(
            RegenerationRequest(project_id, PipelineStage.TA, "user:tom")
        )
        assert not result.success
        assert any("No current artifact" in e for e in result.precondition_errors)
        assert any("PD" in e for e in result.precondition_errors)

    @pytest.mark.asyncio
    async def test_stale_upstream_fails(self, service, doc_repo, project_id):
        # Both PD and TA stale → can't regenerate from TA (PD not current)
        ci = _make_doc(project_id, "concierge_intake")
        pd = _make_doc(project_id, "project_discovery", DocumentStatus.STALE)
        pd.is_latest = False
        ta = _make_doc(project_id, "technical_architecture", DocumentStatus.STALE)
        ta.is_latest = False
        for doc in [ci, pd, ta]:
            await doc_repo.save(doc)

        result = await service.validate_preconditions(
            RegenerationRequest(project_id, PipelineStage.TA, "user:tom")
        )
        assert not result.success
        assert any("PD" in e for e in result.precondition_errors)

    @pytest.mark.asyncio
    async def test_regenerate_from_ci_needs_nothing_upstream(
        self, service, doc_repo, project_id
    ):
        # Regenerate from CI — no upstream to check
        ci = _make_doc(project_id, "concierge_intake", DocumentStatus.STALE)
        ci.is_latest = False
        await doc_repo.save(ci)

        result = await service.validate_preconditions(
            RegenerationRequest(project_id, PipelineStage.CI, "user:tom")
        )
        assert result.success
