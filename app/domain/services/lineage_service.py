"""
Lineage Service (ADR-063, WS-REWIND-006).

Records and queries rewind/regeneration lineage events.
Uses a repository protocol for testability (in-memory for Tier-1,
Postgres for runtime).
"""

import logging
from typing import List, Optional, Protocol
from uuid import UUID

from app.domain.models.lineage_event import LineageEvent

logger = logging.getLogger(__name__)


class LineageRepository(Protocol):
    """Repository protocol for lineage event persistence."""

    async def save(self, event: LineageEvent) -> None:
        """Persist a lineage event."""
        ...

    async def get_by_project(
        self, project_id: UUID, event_type: Optional[str] = None
    ) -> List[LineageEvent]:
        """Get lineage events for a project, optionally filtered by type."""
        ...

    async def get_by_id(self, event_id: UUID) -> Optional[LineageEvent]:
        """Get a single lineage event by ID."""
        ...


class InMemoryLineageRepository:
    """In-memory implementation for Tier-1 testing."""

    def __init__(self) -> None:
        self._events: List[LineageEvent] = []

    async def save(self, event: LineageEvent) -> None:
        self._events.append(event)

    async def get_by_project(
        self, project_id: UUID, event_type: Optional[str] = None
    ) -> List[LineageEvent]:
        result = [e for e in self._events if e.project_id == project_id]
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        return sorted(result, key=lambda e: e.created_at, reverse=True)

    async def get_by_id(self, event_id: UUID) -> Optional[LineageEvent]:
        for e in self._events:
            if e.id == event_id:
                return e
        return None


class PostgresLineageRepository:
    """PostgreSQL implementation for runtime persistence.

    Does NOT commit internally — caller owns transaction.
    """

    def __init__(self, db) -> None:
        self._db = db

    async def save(self, event: LineageEvent) -> None:
        from app.api.models.lineage_event import LineageEventModel

        orm = LineageEventModel(
            id=event.id,
            project_id=event.project_id,
            event_type=event.event_type,
            rewind_to_stage=event.rewind_to_stage,
            reason=event.reason,
            actor=event.actor,
            affected_document_ids=[str(uid) for uid in event.affected_document_ids],
            regeneration_event_id=event.regeneration_event_id,
            created_at=event.created_at,
        )
        self._db.add(orm)
        logger.info(f"Persisted lineage event {event.id} ({event.event_type})")

    async def get_by_project(
        self, project_id: UUID, event_type: Optional[str] = None
    ) -> List[LineageEvent]:
        from app.api.models.lineage_event import LineageEventModel
        from sqlalchemy import select

        stmt = select(LineageEventModel).where(
            LineageEventModel.project_id == project_id,
        )
        if event_type:
            stmt = stmt.where(LineageEventModel.event_type == event_type)
        stmt = stmt.order_by(LineageEventModel.created_at.desc())

        result = await self._db.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_id(self, event_id: UUID) -> Optional[LineageEvent]:
        from app.api.models.lineage_event import LineageEventModel
        from sqlalchemy import select

        result = await self._db.execute(
            select(LineageEventModel).where(LineageEventModel.id == event_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm) -> LineageEvent:
        """Convert ORM model to domain object."""
        doc_ids = [
            UUID(uid) if isinstance(uid, str) else uid
            for uid in (orm.affected_document_ids or [])
        ]
        return LineageEvent(
            id=orm.id,
            project_id=orm.project_id,
            event_type=orm.event_type,
            rewind_to_stage=orm.rewind_to_stage,
            reason=orm.reason,
            actor=orm.actor,
            affected_document_ids=doc_ids,
            created_at=orm.created_at,
            regeneration_event_id=orm.regeneration_event_id,
        )


class LineageService:
    """
    Application service for lineage event recording and retrieval.

    Answers: what changed, why, what became stale, what replaced it.
    """

    def __init__(self, repository: LineageRepository) -> None:
        self._repo = repository

    async def record_rewind(
        self,
        project_id: UUID,
        rewind_to_stage: str,
        reason: str,
        actor: str,
        affected_document_ids: List[UUID],
    ) -> LineageEvent:
        """Record a rewind event. Returns the created event."""
        event = LineageEvent.create_rewind_event(
            project_id=project_id,
            rewind_to_stage=rewind_to_stage,
            reason=reason,
            actor=actor,
            affected_document_ids=affected_document_ids,
        )
        await self._repo.save(event)
        logger.info(
            "Recorded rewind event %s: project=%s, stage=%s, affected=%d docs",
            event.id,
            project_id,
            rewind_to_stage,
            len(affected_document_ids),
        )
        return event

    async def record_regeneration(
        self,
        project_id: UUID,
        from_stage: str,
        reason: str,
        actor: str,
        new_document_ids: List[UUID],
    ) -> LineageEvent:
        """Record a regeneration event. Returns the created event."""
        event = LineageEvent.create_regeneration_event(
            project_id=project_id,
            from_stage=from_stage,
            reason=reason,
            actor=actor,
            new_document_ids=new_document_ids,
        )
        await self._repo.save(event)
        logger.info(
            "Recorded regeneration event %s: project=%s, stage=%s, new=%d docs",
            event.id,
            project_id,
            from_stage,
            len(new_document_ids),
        )
        return event

    async def get_project_history(
        self, project_id: UUID, event_type: Optional[str] = None
    ) -> List[LineageEvent]:
        """Get lineage history for a project, newest first."""
        return await self._repo.get_by_project(project_id, event_type)

    async def get_event(self, event_id: UUID) -> Optional[LineageEvent]:
        """Get a single event by ID."""
        return await self._repo.get_by_id(event_id)
