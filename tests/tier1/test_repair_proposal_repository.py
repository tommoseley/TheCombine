"""Tier-1 tests for RepairProposal persistence (WS-REPAIR-001, ADR-065).

Pure unit tests using InMemoryRepairProposalRepository.
"""

import pytest
from uuid import uuid4

from app.domain.models.repair_proposal import RepairProposalDTO
from app.domain.repositories.repair_proposal_repository import (
    InMemoryRepairProposalRepository,
    PostgresRepairProposalRepository,
)


@pytest.fixture
def repo():
    return InMemoryRepairProposalRepository()


def _make_proposal(artifact_id=None, component="API Gateway", status="pending"):
    return RepairProposalDTO.create(
        artifact_id=artifact_id or uuid4(),
        artifact_type="TA",
        component_identifier=component,
        trigger_finding={"issue_type": "missing_owns", "component_name": component},
        proposed_payload={"name": component, "owns": ["src/api/"]},
        created_by="operator",
    )


class TestCreateAndRetrieve:
    @pytest.mark.asyncio
    async def test_add_and_get_by_id(self, repo):
        proposal = _make_proposal()
        await repo.add(proposal)
        retrieved = await repo.get_by_id(proposal.id)
        assert retrieved is not None
        assert retrieved.id == proposal.id
        assert retrieved.status == "pending"
        assert retrieved.artifact_type == "TA"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_factory_sets_defaults(self):
        proposal = _make_proposal()
        assert proposal.status == "pending"
        assert proposal.created_at is not None
        assert proposal.decision_at is None
        assert proposal.decision_by is None


class TestGetByArtifact:
    @pytest.mark.asyncio
    async def test_returns_proposals_for_artifact(self, repo):
        artifact_id = uuid4()
        p1 = _make_proposal(artifact_id=artifact_id, component="API")
        p2 = _make_proposal(artifact_id=artifact_id, component="Store")
        p3 = _make_proposal()  # different artifact
        await repo.add(p1)
        await repo.add(p2)
        await repo.add(p3)

        results = await repo.get_by_artifact(artifact_id)
        assert len(results) == 2
        assert {r.component_identifier for r in results} == {"API", "Store"}

    @pytest.mark.asyncio
    async def test_filter_by_status(self, repo):
        artifact_id = uuid4()
        p1 = _make_proposal(artifact_id=artifact_id, component="API")
        await repo.add(p1)
        await repo.update_status(p1.id, "accepted", "tom")

        pending = await repo.get_by_artifact(artifact_id, status="pending")
        assert len(pending) == 0
        accepted = await repo.get_by_artifact(artifact_id, status="accepted")
        assert len(accepted) == 1

    @pytest.mark.asyncio
    async def test_empty_artifact_returns_empty(self, repo):
        results = await repo.get_by_artifact(uuid4())
        assert results == []


class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_accept_proposal(self, repo):
        proposal = _make_proposal()
        await repo.add(proposal)
        updated = await repo.update_status(proposal.id, "accepted", "tom")
        assert updated.status == "accepted"
        assert updated.decision_by == "tom"
        assert updated.decision_at is not None

    @pytest.mark.asyncio
    async def test_reject_proposal(self, repo):
        proposal = _make_proposal()
        await repo.add(proposal)
        updated = await repo.update_status(proposal.id, "rejected", "tom")
        assert updated.status == "rejected"

    @pytest.mark.asyncio
    async def test_supersede_proposal(self, repo):
        proposal = _make_proposal()
        await repo.add(proposal)
        updated = await repo.update_status(proposal.id, "superseded", "system")
        assert updated.status == "superseded"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, repo):
        result = await repo.update_status(uuid4(), "accepted", "tom")
        assert result is None


class TestPostgresRepoContract:
    """Verify PostgresRepairProposalRepository follows the protocol."""

    def test_class_exists(self):
        assert PostgresRepairProposalRepository is not None

    def test_has_required_methods(self):
        for method in ("add", "get_by_id", "get_by_artifact", "update_status"):
            assert hasattr(PostgresRepairProposalRepository, method)

    def test_constructor_accepts_db(self):
        repo = PostgresRepairProposalRepository(db=None)
        assert repo._db is None
