"""Authority Repository (ADR-064, WS-AUTH-002).

Protocol, InMemory, and PostgreSQL implementations for
authority record persistence.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""

from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID
import logging

from app.domain.models.authority_record import AuthorityRecordDTO

logger = logging.getLogger(__name__)


@runtime_checkable
class AuthorityRepository(Protocol):
    """Protocol for authority record persistence.

    All methods async. No commits — caller owns transactions.
    """

    async def add(self, record: AuthorityRecordDTO) -> None:
        """Persist a new authority record."""
        ...

    async def get_current_by_project(self, project_id: UUID) -> List[AuthorityRecordDTO]:
        """Return all current authority records for a project."""
        ...

    async def get_current_by_project_type_key(
        self, project_id: UUID, authority_type: str, key: str
    ) -> Optional[AuthorityRecordDTO]:
        """Return the current authority record for a (project, type, key) triple."""
        ...

    async def get_by_lineage_path(self, lineage_path_id: UUID) -> List[AuthorityRecordDTO]:
        """Return all records on a lineage path regardless of status."""
        ...

    async def update_status(
        self, record_id: UUID, new_status: str, superseded_by: Optional[UUID] = None
    ) -> Optional[AuthorityRecordDTO]:
        """Update a record's status. Returns updated record or None if not found."""
        ...


class InMemoryAuthorityRepository:
    """In-memory implementation for Tier-1 tests.

    Implements AuthorityRepository protocol.
    """

    def __init__(self) -> None:
        self._records: List[AuthorityRecordDTO] = []

    async def add(self, record: AuthorityRecordDTO) -> None:
        self._records.append(record)

    async def get_current_by_project(self, project_id: UUID) -> List[AuthorityRecordDTO]:
        return [
            r for r in self._records
            if r.project_id == project_id and r.status == "current"
        ]

    async def get_current_by_project_type_key(
        self, project_id: UUID, authority_type: str, key: str
    ) -> Optional[AuthorityRecordDTO]:
        for r in self._records:
            if (
                r.project_id == project_id
                and r.authority_type == authority_type
                and r.key == key
                and r.status == "current"
            ):
                return r
        return None

    async def get_by_lineage_path(self, lineage_path_id: UUID) -> List[AuthorityRecordDTO]:
        return [r for r in self._records if r.lineage_path_id == lineage_path_id]

    async def update_status(
        self, record_id: UUID, new_status: str, superseded_by: Optional[UUID] = None
    ) -> Optional[AuthorityRecordDTO]:
        for r in self._records:
            if r.id == record_id:
                r.status = new_status
                if superseded_by is not None:
                    r.superseded_by = superseded_by
                return r
        return None


class PostgresAuthorityRepository:
    """PostgreSQL implementation for runtime.

    Does NOT commit internally — caller owns transaction.
    """

    def __init__(self, db) -> None:
        self._db = db

    async def add(self, record: AuthorityRecordDTO) -> None:
        from app.api.models.authority_record import AuthorityRecord
        orm = AuthorityRecord(
            id=record.id,
            project_id=record.project_id,
            authority_type=record.authority_type,
            stage=record.stage,
            key=record.key,
            value=record.value,
            source_execution_id=record.source_execution_id,
            lineage_path_id=record.lineage_path_id,
            actor=record.actor,
            status=record.status,
            superseded_by=record.superseded_by,
            created_at=record.created_at,
        )
        self._db.add(orm)
        logger.info(f"Added authority record {record.id} for project {record.project_id}")

    async def get_current_by_project(self, project_id: UUID) -> List[AuthorityRecordDTO]:
        from app.api.models.authority_record import AuthorityRecord
        from sqlalchemy import select

        result = await self._db.execute(
            select(AuthorityRecord).where(
                AuthorityRecord.project_id == project_id,
                AuthorityRecord.status == "current",
            )
        )
        return [self._to_dto(orm) for orm in result.scalars().all()]

    async def get_current_by_project_type_key(
        self, project_id: UUID, authority_type: str, key: str
    ) -> Optional[AuthorityRecordDTO]:
        from app.api.models.authority_record import AuthorityRecord
        from sqlalchemy import select

        result = await self._db.execute(
            select(AuthorityRecord).where(
                AuthorityRecord.project_id == project_id,
                AuthorityRecord.authority_type == authority_type,
                AuthorityRecord.key == key,
                AuthorityRecord.status == "current",
            )
        )
        orm = result.scalar_one_or_none()
        return self._to_dto(orm) if orm else None

    async def get_by_lineage_path(self, lineage_path_id: UUID) -> List[AuthorityRecordDTO]:
        from app.api.models.authority_record import AuthorityRecord
        from sqlalchemy import select

        result = await self._db.execute(
            select(AuthorityRecord).where(
                AuthorityRecord.lineage_path_id == lineage_path_id,
            )
        )
        return [self._to_dto(orm) for orm in result.scalars().all()]

    async def update_status(
        self, record_id: UUID, new_status: str, superseded_by: Optional[UUID] = None
    ) -> Optional[AuthorityRecordDTO]:
        from app.api.models.authority_record import AuthorityRecord
        from sqlalchemy import select

        result = await self._db.execute(
            select(AuthorityRecord).where(AuthorityRecord.id == record_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        orm.status = new_status
        if superseded_by is not None:
            orm.superseded_by = superseded_by
        return self._to_dto(orm)

    @staticmethod
    def _to_dto(orm) -> AuthorityRecordDTO:
        return AuthorityRecordDTO(
            id=orm.id,
            project_id=orm.project_id,
            authority_type=orm.authority_type,
            stage=orm.stage,
            key=orm.key,
            value=orm.value,
            source_execution_id=orm.source_execution_id,
            lineage_path_id=orm.lineage_path_id,
            actor=orm.actor,
            status=orm.status,
            superseded_by=orm.superseded_by,
            created_at=orm.created_at,
        )
