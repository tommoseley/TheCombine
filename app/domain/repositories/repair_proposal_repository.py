"""
Repair Proposal Repository (ADR-065).

Protocol + InMemory + Postgres implementations.
Follows authority_repository pattern.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from app.domain.models.repair_proposal import RepairProposalDTO

logger = logging.getLogger(__name__)


@runtime_checkable
class RepairProposalRepository(Protocol):
    """Repository protocol for repair proposal persistence."""

    async def add(self, proposal: RepairProposalDTO) -> None:
        """Persist a new repair proposal."""
        ...

    async def get_by_id(self, proposal_id: UUID) -> Optional[RepairProposalDTO]:
        """Get a proposal by ID."""
        ...

    async def get_by_artifact(
        self, artifact_id: UUID, status: Optional[str] = None
    ) -> List[RepairProposalDTO]:
        """Get proposals for an artifact, optionally filtered by status."""
        ...

    async def update_status(
        self,
        proposal_id: UUID,
        new_status: str,
        decision_by: str,
    ) -> Optional[RepairProposalDTO]:
        """Update proposal status. Returns updated proposal or None."""
        ...


class InMemoryRepairProposalRepository:
    """In-memory implementation for Tier-1 testing."""

    def __init__(self) -> None:
        self._proposals: List[RepairProposalDTO] = []

    async def add(self, proposal: RepairProposalDTO) -> None:
        self._proposals.append(proposal)

    async def get_by_id(self, proposal_id: UUID) -> Optional[RepairProposalDTO]:
        for p in self._proposals:
            if p.id == proposal_id:
                return p
        return None

    async def get_by_artifact(
        self, artifact_id: UUID, status: Optional[str] = None
    ) -> List[RepairProposalDTO]:
        result = [p for p in self._proposals if p.artifact_id == artifact_id]
        if status:
            result = [p for p in result if p.status == status]
        return sorted(result, key=lambda p: p.created_at, reverse=True)

    async def update_status(
        self,
        proposal_id: UUID,
        new_status: str,
        decision_by: str,
    ) -> Optional[RepairProposalDTO]:
        for i, p in enumerate(self._proposals):
            if p.id == proposal_id:
                from dataclasses import replace
                updated = replace(
                    p,
                    status=new_status,
                    decision_at=datetime.now(timezone.utc),
                    decision_by=decision_by,
                )
                self._proposals[i] = updated
                return updated
        return None


class PostgresRepairProposalRepository:
    """PostgreSQL implementation for runtime.

    Does NOT commit internally — caller owns transaction.
    """

    def __init__(self, db) -> None:
        self._db = db

    async def add(self, proposal: RepairProposalDTO) -> None:
        from app.api.models.repair_proposal import RepairProposal

        orm = RepairProposal(
            id=proposal.id,
            artifact_id=proposal.artifact_id,
            artifact_type=proposal.artifact_type,
            component_identifier=proposal.component_identifier,
            trigger_finding=proposal.trigger_finding,
            proposed_payload=proposal.proposed_payload,
            status=proposal.status,
            created_at=proposal.created_at,
            created_by=proposal.created_by,
            decision_at=proposal.decision_at,
            decision_by=proposal.decision_by,
        )
        self._db.add(orm)
        logger.info(f"Added repair proposal {proposal.id}")

    async def get_by_id(self, proposal_id: UUID) -> Optional[RepairProposalDTO]:
        from app.api.models.repair_proposal import RepairProposal
        from sqlalchemy import select

        result = await self._db.execute(
            select(RepairProposal).where(RepairProposal.id == proposal_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_dto(orm) if orm else None

    async def get_by_artifact(
        self, artifact_id: UUID, status: Optional[str] = None
    ) -> List[RepairProposalDTO]:
        from app.api.models.repair_proposal import RepairProposal
        from sqlalchemy import select

        stmt = select(RepairProposal).where(
            RepairProposal.artifact_id == artifact_id,
        )
        if status:
            stmt = stmt.where(RepairProposal.status == status)
        stmt = stmt.order_by(RepairProposal.created_at.desc())

        result = await self._db.execute(stmt)
        return [self._to_dto(orm) for orm in result.scalars().all()]

    async def update_status(
        self,
        proposal_id: UUID,
        new_status: str,
        decision_by: str,
    ) -> Optional[RepairProposalDTO]:
        from app.api.models.repair_proposal import RepairProposal
        from sqlalchemy import select

        result = await self._db.execute(
            select(RepairProposal).where(RepairProposal.id == proposal_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        orm.status = new_status
        orm.decision_at = datetime.now(timezone.utc)
        orm.decision_by = decision_by
        return self._to_dto(orm)

    @staticmethod
    def _to_dto(orm) -> RepairProposalDTO:
        return RepairProposalDTO(
            id=orm.id,
            artifact_id=orm.artifact_id,
            artifact_type=orm.artifact_type,
            component_identifier=orm.component_identifier,
            trigger_finding=orm.trigger_finding,
            proposed_payload=orm.proposed_payload,
            status=orm.status,
            created_at=orm.created_at,
            created_by=orm.created_by,
            decision_at=orm.decision_at,
            decision_by=orm.decision_by,
        )
