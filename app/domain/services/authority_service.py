"""Authority Service (ADR-064, WS-AUTH-003).

Business logic for durable authority records:
- Record new authority (with type-scoped supersession)
- Resolve current authority for a project
- Build authority bundles for execution context
- Mark path records as historical
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import AuthorityRepository

logger = logging.getLogger(__name__)


class AuthorityService:
    """Manages durable authority records per ADR-064.

    Constructor takes AuthorityRepository (Protocol) — no concrete dependency.
    Does NOT commit transactions — caller owns that.
    """

    def __init__(self, repository: AuthorityRepository) -> None:
        self._repo = repository

    async def record_authority(
        self,
        project_id: UUID,
        authority_type: str,
        stage: str,
        key: str,
        value: Any,
        source_execution_id: UUID,
        lineage_path_id: UUID,
        actor: str,
    ) -> AuthorityRecordDTO:
        """Persist a new authority record.

        Supersession is type-scoped: if a current record exists for the
        same (project_id, authority_type, key), it is superseded.
        A pgc_answer never collides with a bound_constraint sharing the same key.
        """
        # Check for existing current record with same (project, type, key)
        existing = await self._repo.get_current_by_project_type_key(
            project_id, authority_type, key
        )

        new_record = AuthorityRecordDTO(
            project_id=project_id,
            authority_type=authority_type,
            stage=stage,
            key=key,
            value=value,
            source_execution_id=source_execution_id,
            lineage_path_id=lineage_path_id,
            actor=actor,
        )

        if existing is not None:
            await self._repo.update_status(
                existing.id, "superseded", superseded_by=new_record.id
            )
            logger.info(
                "Superseded authority record",
                extra={
                    "old_record_id": str(existing.id),
                    "new_record_id": str(new_record.id),
                    "project_id": str(project_id),
                    "authority_type": authority_type,
                    "key": key,
                },
            )

        await self._repo.add(new_record)
        return new_record

    async def get_current_authority(self, project_id: UUID) -> List[AuthorityRecordDTO]:
        """Return all current authority records for a project."""
        return await self._repo.get_current_by_project(project_id)

    async def get_authority_bundle(self, project_id: UUID) -> Dict[str, Any]:
        """Build a structured authority bundle for execution context injection.

        Returns canonical keys consumed by WS-AUTH-005 (hydration)
        and WS-AUTH-006 (QA):
        - pgc_answers: {key: value} for pgc_answer records
        - pgc_questions: [key] for pgc_answer records
        - authority_record_ids: [UUID] for audit citation
        - authority_source: "durable_store" | "none"
        """
        records = await self.get_current_authority(project_id)

        if not records:
            return {
                "pgc_answers": {},
                "pgc_questions": [],
                "authority_record_ids": [],
                "authority_source": "none",
            }

        pgc_records = [r for r in records if r.authority_type == "pgc_answer"]

        return {
            "pgc_answers": {r.key: r.value for r in pgc_records},
            "pgc_questions": [r.key for r in pgc_records],
            "authority_record_ids": [r.id for r in records],
            "authority_source": "durable_store",
        }

    async def supersede_record(
        self, old_record_id: UUID, new_record_id: UUID
    ) -> Optional[AuthorityRecordDTO]:
        """Mark old record as superseded, linking to replacement."""
        return await self._repo.update_status(
            old_record_id, "superseded", superseded_by=new_record_id
        )

    async def mark_path_historical(self, lineage_path_id: UUID) -> int:
        """Mark all records on a lineage path as historical.

        Returns count of records marked.
        """
        records = await self._repo.get_by_lineage_path(lineage_path_id)
        count = 0
        for r in records:
            if r.status != "historical":
                await self._repo.update_status(r.id, "historical")
                count += 1
        if count > 0:
            logger.info(
                "Marked authority records as historical",
                extra={
                    "lineage_path_id": str(lineage_path_id),
                    "count": count,
                },
            )
        return count
