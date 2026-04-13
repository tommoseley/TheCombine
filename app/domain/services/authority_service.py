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
        - operator_corrections: [{origin_stage, text, authority_record_id}]
          All current corrections, project-scoped (no stage filtering).
          Sorted by pipeline order of origin stage, then created_at.
        - authority_record_ids: [UUID] for audit citation
        - authority_source: "durable_store" | "none"
        """
        records = await self.get_current_authority(project_id)

        if not records:
            return {
                "pgc_answers": {},
                "pgc_questions": [],
                "operator_corrections": [],
                "authority_record_ids": [],
                "authority_source": "none",
            }

        pgc_records = [r for r in records if r.authority_type == "pgc_answer"]
        correction_records = [r for r in records if r.authority_type == "operator_correction"]

        # Sort corrections by pipeline order, then created_at
        sorted_corrections = self._sort_corrections(correction_records)

        return {
            "pgc_answers": {r.key: r.value for r in pgc_records},
            "pgc_questions": [r.key for r in pgc_records],
            "operator_corrections": [
                {
                    "origin_stage": r.stage,
                    "text": r.value.get("text", "") if isinstance(r.value, dict) else "",
                    "authority_record_id": r.id,
                }
                for r in sorted_corrections
            ],
            "authority_record_ids": [r.id for r in records],
            "authority_source": "durable_store",
        }

    async def get_corrections_for_stage(
        self, project_id: UUID, stage: str
    ) -> List[AuthorityRecordDTO]:
        """Return current operator corrections applicable to a generated stage.

        A correction applies to a stage if:
        1. The correction's origin stage matches (record.stage == stage), OR
        2. The stage appears in the correction's applies_to_stages list

        Returns corrections sorted by pipeline order of origin stage,
        then by created_at. This is the stage-aware query — used by
        task node and binder (ADR-069 §3.4).
        """
        records = await self.get_current_authority(project_id)
        corrections = [r for r in records if r.authority_type == "operator_correction"]

        # Filter to applicable corrections
        applicable = []
        for r in corrections:
            applies_to = []
            if isinstance(r.value, dict):
                applies_to = r.value.get("applies_to_stages", [])
            if r.stage == stage or stage in applies_to:
                applicable.append(r)

        return self._sort_corrections(applicable)

    async def get_current_correction(
        self, project_id: UUID, stage: str
    ) -> Optional[AuthorityRecordDTO]:
        """Return the current correction for a specific originating stage.

        Looks up by key='correction:{stage}'. Used for pre-populating
        the rewind dialog on subsequent rewinds (ADR-069 §3.2).

        Returns None if no correction exists for this stage.
        """
        return await self._repo.get_current_by_project_type_key(
            project_id, "operator_correction", f"correction:{stage}"
        )

    @staticmethod
    def _sort_corrections(
        corrections: List[AuthorityRecordDTO],
    ) -> List[AuthorityRecordDTO]:
        """Sort corrections by pipeline order of origin stage, then created_at.

        Unknown stages sort after all known stages.
        """
        from app.domain.models.pipeline_stage import PipelineStage

        stage_order = {s.name: s.order for s in PipelineStage}

        def sort_key(r: AuthorityRecordDTO):
            order = stage_order.get(r.stage, 999)
            return (order, r.created_at)

        return sorted(corrections, key=sort_key)

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
