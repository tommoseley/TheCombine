"""Backlog Compilation Pipeline API router.

Endpoints:
- POST /api/v1/backlog-pipeline/run - Trigger full pipeline from intent_id
- GET /api/v1/backlog-pipeline/runs/{run_id} - Retrieve pipeline run metadata

WS-BCP-004.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.api.models.document import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backlog-pipeline", tags=["backlog-pipeline"])


# --- Request/Response Models ---


class RunPipelineRequest(BaseModel):
    """Request to trigger the Backlog Compilation Pipeline."""
    project_id: str = Field(..., description="Project UUID")
    intent_id: str = Field(..., description="IntentPacket document UUID")
    skip_explanation: bool = Field(False, description="Skip the explanation generation step")


class RunPipelineResponse(BaseModel):
    """Response from a pipeline run."""
    status: str
    run_id: str
    intent_id: str
    stage_reached: str
    backlog_hash: Optional[str] = None
    plan_id: Optional[str] = None
    explanation_id: Optional[str] = None
    errors: Optional[dict] = None
    metadata: Optional[dict] = None


# --- Endpoints ---


@router.post("/run", response_model=RunPipelineResponse)
async def run_pipeline(
    request: RunPipelineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> RunPipelineResponse:
    """Trigger the full Backlog Compilation Pipeline.

    Sequence: Load intent -> Generate backlog -> Validate graph ->
    Derive execution plan -> Generate explanation -> Store metadata.

    Failure at any stage (except explanation) halts the pipeline.
    """
    from app.domain.workflow.plan_executor import PlanExecutor
    from app.domain.workflow.pg_state_persistence import PgStatePersistence
    from app.domain.workflow.plan_registry import get_plan_registry
    from app.domain.workflow.nodes.llm_executors import create_llm_executors
    from app.domain.services.backlog_pipeline import BacklogPipelineService

    try:
        executors = await create_llm_executors(db)
        executor = PlanExecutor(
            persistence=PgStatePersistence(db),
            plan_registry=get_plan_registry(),
            executors=executors,
            db_session=db,
        )

        service = BacklogPipelineService(db_session=db, plan_executor=executor)
        result = await service.run(
            project_id=request.project_id,
            intent_id=request.intent_id,
            skip_explanation=request.skip_explanation,
        )

        await db.commit()

        status_code = 200 if result.status == "completed" else 422

        return RunPipelineResponse(
            status=result.status,
            run_id=result.run_id,
            intent_id=result.intent_id,
            stage_reached=result.stage_reached,
            backlog_hash=result.backlog_hash,
            plan_id=result.plan_id,
            explanation_id=result.explanation_id,
            errors=result.errors,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.get("/runs/{run_id}")
async def get_pipeline_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Retrieve pipeline run metadata by run_id."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "pipeline_run",
            Document.instance_id == run_id,
            Document.is_latest == True,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run not found: {run_id}",
        )

    return {
        "run_id": run_id,
        "project_id": str(doc.space_id),
        "content": doc.content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
