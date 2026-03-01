"""QA coverage service.

Provides QA coverage data extraction from workflow executions.
Used by both the API and web routes.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


async def get_qa_coverage(
    db: AsyncSession,
    execution_id: str,
) -> Optional[Dict[str, Any]]:
    """Get QA coverage data for a workflow execution.

    Args:
        db: Database session
        execution_id: Workflow execution ID

    Returns:
        Dict with execution info, constraint_lookup, qa_nodes, and summary.
        Returns None if execution not found.
    """
    # Get workflow execution
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.execution_id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        return None

    from app.api.services.service_pure import build_constraint_lookup, process_qa_nodes

    # Extract bound constraints from context_state for display
    context_state = execution.context_state or {}
    pgc_invariants = context_state.get("pgc_invariants", [])

    constraint_lookup = build_constraint_lookup(pgc_invariants)

    execution_log = execution.execution_log or []
    processed_qa_nodes, summary = process_qa_nodes(execution_log)

    return {
        "execution_id": execution_id,
        "workflow_id": execution.workflow_id,
        "document_type": execution.document_type,
        "constraint_lookup": constraint_lookup,
        "qa_nodes": processed_qa_nodes,
        "summary": summary,
    }
