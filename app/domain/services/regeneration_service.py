"""
Regeneration Service (ADR-063, WS-REWIND-011).

Restarts document generation from the active rewind stage, producing
new current artifacts that supersede the stale ones.

MVP: service contract and validation. Full pipeline integration
deferred to WP-REWIND-003 wiring phase.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from app.domain.models.pipeline_stage import PipelineStage
from app.domain.services.lineage_service import LineageService
from app.persistence.models import DocumentStatus
from app.persistence.repositories import DocumentRepository

logger = logging.getLogger(__name__)


@dataclass
class RegenerationRequest:
    """Request to regenerate from a pipeline stage."""

    project_id: UUID
    from_stage: PipelineStage
    actor: str


@dataclass
class RegenerationResult:
    """Result of a regeneration operation."""

    success: bool
    from_stage: str
    precondition_errors: List[str]
    message: str


class RegenerationService:
    """
    Service for regenerating pipeline artifacts from a rewind point.

    Validates preconditions:
    1. Stale artifacts must exist at the requested stage
    2. All upstream stages must have current artifacts
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        lineage_service: LineageService,
    ) -> None:
        self._doc_repo = document_repo
        self._lineage = lineage_service

    async def validate_preconditions(
        self, request: RegenerationRequest
    ) -> RegenerationResult:
        """
        Check whether regeneration can proceed.

        Validates:
        - Stale artifacts exist at the requested stage
        - Upstream stages have current artifacts
        """
        errors: List[str] = []

        # Get all project documents
        all_docs = await self._doc_repo.list_by_scope(
            scope_type="project",
            scope_id=str(request.project_id),
        )

        # Check: stale artifacts exist at requested stage
        stage_doc_type = request.from_stage.doc_type_id
        stale_at_stage = [
            d
            for d in all_docs
            if d.document_type == stage_doc_type
            and d.status == DocumentStatus.STALE
        ]
        if not stale_at_stage:
            errors.append(
                f"No stale artifacts found at stage {request.from_stage.name} "
                f"(doc_type: {stage_doc_type})"
            )

        # Check: upstream stages have current artifacts
        for upstream in PipelineStage.all_stages_ordered():
            if upstream.order >= request.from_stage.order:
                break  # only check stages before the rewind point
            upstream_docs = [
                d
                for d in all_docs
                if d.document_type == upstream.doc_type_id
                and d.is_latest
                and d.status not in (DocumentStatus.STALE, DocumentStatus.ARCHIVED)
            ]
            if not upstream_docs:
                errors.append(
                    f"No current artifact at upstream stage "
                    f"{upstream.name} ({upstream.doc_type_id})"
                )

        if errors:
            return RegenerationResult(
                success=False,
                from_stage=request.from_stage.name,
                precondition_errors=errors,
                message="Regeneration blocked: preconditions not met",
            )

        return RegenerationResult(
            success=True,
            from_stage=request.from_stage.name,
            precondition_errors=[],
            message=(
                f"Preconditions met. Ready to regenerate from "
                f"{request.from_stage.name}."
            ),
        )
