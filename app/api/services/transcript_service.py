"""Transcript service.

Provides LLM conversation transcript data for workflow executions.
Used by both the API and web routes.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.project import Project
from app.domain.models.llm_logging import (
    LLMRun,
    LLMRunInputRef,
    LLMRunOutputRef,
    LLMContent,
)

logger = logging.getLogger(__name__)

# Default display timezone
DISPLAY_TZ = ZoneInfo("America/New_York")


async def _resolve_content_ref(db: AsyncSession, content_ref: str) -> Optional[str]:
    """Resolve a content_ref like 'db://llm_content/{uuid}' to actual content."""
    if not content_ref or not content_ref.startswith("db://llm_content/"):
        return None
    try:
        content_id = UUID(content_ref.replace("db://llm_content/", ""))
        result = await db.execute(select(LLMContent).where(LLMContent.id == content_id))
        content = result.scalar_one_or_none()
        return content.content_text if content else None
    except Exception:
        return None


async def _get_project_name(db: AsyncSession, project_id: Optional[UUID]) -> Optional[str]:
    """Get project name from ID."""
    if not project_id:
        return None
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project.name if project else None


async def _get_llm_run_inputs(db: AsyncSession, run_id: UUID) -> List[Dict[str, Any]]:
    """Get LLM run inputs with resolved content."""
    result = await db.execute(
        select(LLMRunInputRef).where(LLMRunInputRef.llm_run_id == run_id)
    )
    inputs = []
    for ref in result.scalars().all():
        content = await _resolve_content_ref(db, ref.content_ref)
        inputs.append({
            "kind": ref.kind,
            "content": content,
            "size": len(content.encode("utf-8")) if content else 0,
            "redacted": ref.content_redacted,
        })
    return inputs


async def _get_llm_run_outputs(db: AsyncSession, run_id: UUID) -> List[Dict[str, Any]]:
    """Get LLM run outputs with resolved content."""
    result = await db.execute(
        select(LLMRunOutputRef).where(LLMRunOutputRef.llm_run_id == run_id)
    )
    outputs = []
    for ref in result.scalars().all():
        content = await _resolve_content_ref(db, ref.content_ref)
        outputs.append({
            "kind": ref.kind,
            "content": content,
            "size": len(content.encode("utf-8")) if content else 0,
            "parse_status": ref.parse_status,
            "validation_status": ref.validation_status,
        })
    return outputs


async def get_execution_transcript(
    db: AsyncSession,
    execution_id: str,
) -> Optional[Dict[str, Any]]:
    """Get transcript data for a workflow execution.

    Args:
        db: Database session
        execution_id: Workflow execution ID

    Returns:
        Dict with execution info and transcript entries.
        Returns None if no LLM runs found.
    """
    # Get all LLM runs for this workflow execution
    result = await db.execute(
        select(LLMRun)
        .where(LLMRun.workflow_execution_id == execution_id)
        .order_by(LLMRun.started_at)
    )
    runs = list(result.scalars().all())

    if not runs:
        return None

    # Get project name from first run
    first_run = runs[0]
    project_name = await _get_project_name(db, first_run.project_id)

    from app.api.services.service_pure import (
        build_transcript_entry,
        compute_transcript_totals,
        format_transcript_timestamps,
    )

    # Build transcript entries
    transcript_entries = []

    for i, run in enumerate(runs, 1):
        # Get inputs and outputs (I/O -- not extractable)
        inputs = await _get_llm_run_inputs(db, run.id)
        outputs = await _get_llm_run_outputs(db, run.id)

        # Extract node_id and prompt_sources from metadata if available
        node_id = None
        prompt_sources = None
        if run.run_metadata and isinstance(run.run_metadata, dict):
            node_id = run.run_metadata.get("node_id")
            prompt_sources = run.run_metadata.get("prompt_sources")

        entry = build_transcript_entry(
            run_number=i,
            run_id=str(run.id),
            role=run.role,
            prompt_id=run.prompt_id,
            node_id=node_id,
            prompt_sources=prompt_sources,
            model_name=run.model_name,
            status=run.status,
            started_at=run.started_at,
            ended_at=run.ended_at,
            total_tokens=run.total_tokens,
            cost_usd=run.cost_usd,
            inputs=inputs,
            outputs=outputs,
            display_tz=DISPLAY_TZ,
        )
        transcript_entries.append(entry)

    total_tokens, total_cost = compute_transcript_totals(transcript_entries)

    timestamps = format_transcript_timestamps(
        started_at=runs[0].started_at,
        ended_at=runs[-1].ended_at,
        display_tz=DISPLAY_TZ,
    )

    return {
        "execution_id": execution_id,
        "project_id": str(first_run.project_id) if first_run.project_id else None,
        "project_name": project_name,
        "document_type": first_run.artifact_type,
        "transcript": transcript_entries,
        "total_runs": len(runs),
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        **timestamps,
    }
