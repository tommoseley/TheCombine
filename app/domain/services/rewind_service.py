"""
Rewind Service (ADR-063, WS-REWIND-004).

Orchestrates pipeline rewind: evaluates impact, marks documents stale,
records lineage. Manual trigger only (no automatic rewind).
"""

import logging
from dataclasses import dataclass
from typing import List
from uuid import UUID

from app.domain.models.artifact_status import (
    ArtifactStatus,
    IllegalTransitionError,
    validate_transition,
)
from app.domain.models.pipeline_stage import PipelineStage
from app.domain.services.lineage_service import LineageService
from app.domain.services.rewind_impact_evaluator import (
    evaluate_rewind_impact,
    get_affected_doc_type_ids,
)
from app.persistence.models import DocumentStatus
from app.persistence.repositories import DocumentRepository

logger = logging.getLogger(__name__)


@dataclass
class RewindRequest:
    """Request to rewind a project pipeline."""

    project_id: UUID
    rewind_to_stage: PipelineStage
    reason: str
    actor: str


@dataclass
class RewindResult:
    """Result of a rewind operation."""

    success: bool
    rewind_to_stage: str
    affected_stages: List[str]
    affected_document_count: int
    stale_document_ids: List[UUID]
    lineage_event_id: UUID
    error: str = ""


class RewindService:
    """
    Orchestrates pipeline rewind per ADR-063.

    1. Evaluate impact (which stages/docs are affected)
    2. Mark affected documents stale
    3. Record lineage event
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        lineage_service: LineageService,
    ) -> None:
        self._doc_repo = document_repo
        self._lineage = lineage_service

    async def execute_rewind(self, request: RewindRequest) -> RewindResult:
        """
        Execute a pipeline rewind.

        Args:
            request: RewindRequest with project, stage, reason, actor.

        Returns:
            RewindResult with affected documents and lineage event.
        """
        # Step 1: Evaluate impact
        affected_stages = evaluate_rewind_impact(request.rewind_to_stage)
        affected_doc_type_ids = get_affected_doc_type_ids(request.rewind_to_stage)

        logger.info(
            "Rewind requested: project=%s, stage=%s, affected_stages=%s",
            request.project_id,
            request.rewind_to_stage.name,
            [s.name for s in affected_stages],
        )

        # Step 2: Find affected documents
        all_docs = await self._doc_repo.list_by_scope(
            scope_type="project",
            scope_id=str(request.project_id),
        )

        # Filter to affected doc types that are currently 'current' (active/draft)
        affected_docs = [
            doc
            for doc in all_docs
            if doc.document_type in affected_doc_type_ids
            and doc.is_latest
            and doc.status not in (DocumentStatus.STALE, DocumentStatus.ARCHIVED)
        ]

        # Step 3: Mark affected documents stale
        stale_ids: List[UUID] = []
        for doc in affected_docs:
            doc.status = DocumentStatus.STALE
            doc.is_latest = False
            await self._doc_repo.save(doc)
            stale_ids.append(doc.document_id)

        logger.info(
            "Marked %d documents stale for rewind at %s",
            len(stale_ids),
            request.rewind_to_stage.name,
        )

        # Step 4: Record lineage event
        event = await self._lineage.record_rewind(
            project_id=request.project_id,
            rewind_to_stage=request.rewind_to_stage.name,
            reason=request.reason,
            actor=request.actor,
            affected_document_ids=stale_ids,
        )

        return RewindResult(
            success=True,
            rewind_to_stage=request.rewind_to_stage.name,
            affected_stages=[s.name for s in affected_stages],
            affected_document_count=len(stale_ids),
            stale_document_ids=stale_ids,
            lineage_event_id=event.id,
        )
