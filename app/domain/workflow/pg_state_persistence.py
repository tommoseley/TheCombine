"""PostgreSQL persistence for Document Workflow State via ORM.

Minimal implementation - stores only essential fields.
Everything else derived at runtime from execution_log.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)

logger = logging.getLogger(__name__)


class PgStatePersistence:
    """PostgreSQL-backed state persistence via ORM."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, state: DocumentWorkflowState) -> None:
        """Save workflow state to database via ORM."""
        # Lazy import to avoid circular dependency
        from app.api.models.workflow_execution import WorkflowExecution
        from app.api.models.project import Project
        from uuid import UUID as UUIDType

        # Serialize execution log
        execution_log = [
            {
                "node_id": ne.node_id,
                "outcome": ne.outcome,
                "timestamp": ne.timestamp.isoformat(),
                "metadata": ne.metadata,
            }
            for ne in state.node_history
        ]

        # Resolve project_id to UUID (for interrupt querying)
        project_uuid = None
        if state.project_id:
            try:
                project_uuid = UUIDType(state.project_id)
            except (ValueError, TypeError):
                # project_id is not a UUID, look up the project
                proj_result = await self._db.execute(
                    select(Project).where(Project.project_id == state.project_id)
                )
                project = proj_result.scalar_one_or_none()
                if project:
                    project_uuid = project.id

        # Check if exists
        result = await self._db.execute(
            select(WorkflowExecution).where(WorkflowExecution.execution_id == state.execution_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.current_node_id = state.current_node_id
            existing.execution_log = execution_log
            existing.retry_counts = state.retry_counts
            existing.gate_outcome = state.gate_outcome
            existing.terminal_outcome = state.terminal_outcome
            existing.status = state.status.value
            existing.pending_user_input = state.pending_user_input
            existing.pending_user_input_rendered = state.pending_user_input_rendered
            existing.pending_choices = state.pending_choices
            existing.pending_user_input_payload = state.pending_user_input_payload
            existing.pending_user_input_schema_ref = state.pending_user_input_schema_ref
            existing.thread_id = state.thread_id
            existing.context_state = state.context_state
            # Update project_id if not set
            if not existing.project_id and project_uuid:
                existing.project_id = project_uuid
        else:
            # Create new record
            user_uuid = None
            if state.user_id:
                try:
                    user_uuid = UUIDType(state.user_id) if isinstance(state.user_id, str) else state.user_id
                except (ValueError, TypeError):
                    user_uuid = None

            execution = WorkflowExecution(
                execution_id=state.execution_id,
                document_id=state.project_id,
                document_type=state.document_type,
                workflow_id=state.workflow_id,
                project_id=project_uuid,  # ADR-043: Set project_id for interrupt querying
                user_id=user_uuid,
                current_node_id=state.current_node_id,
                execution_log=execution_log,
                retry_counts=state.retry_counts,
                gate_outcome=state.gate_outcome,
                terminal_outcome=state.terminal_outcome,
                status=state.status.value,
                pending_user_input=state.pending_user_input,
                pending_user_input_rendered=state.pending_user_input_rendered,
                pending_choices=state.pending_choices,
                pending_user_input_payload=state.pending_user_input_payload,
                pending_user_input_schema_ref=state.pending_user_input_schema_ref,
                thread_id=state.thread_id,
                context_state=state.context_state,
            )
            self._db.add(execution)

        await self._db.commit()

    async def load(self, execution_id: str) -> Optional[DocumentWorkflowState]:
        """Load workflow state by execution ID via ORM."""
        from app.api.models.workflow_execution import WorkflowExecution

        # Expire any cached data to ensure we get fresh from DB
        await self._db.execute(select(WorkflowExecution).where(WorkflowExecution.execution_id == execution_id))
        self._db.expire_all()

        result = await self._db.execute(
            select(WorkflowExecution).where(WorkflowExecution.execution_id == execution_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            return None

        # Debug: log context_state keys
        context_keys = list((row.context_state or {}).keys())
        logger.debug(f"Loading execution {execution_id}: context_state keys = {context_keys}")

        return self._row_to_state(row)

    async def load_by_document(
        self, project_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load state by document and workflow ID via ORM."""
        from app.api.models.workflow_execution import WorkflowExecution
        
        result = await self._db.execute(
            select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.document_id == project_id,
                    WorkflowExecution.workflow_id == workflow_id,
                    WorkflowExecution.terminal_outcome.is_(None)
                )
            ).limit(1)
        )
        row = result.scalar_one_or_none()

        if not row:
            return None

        return self._row_to_state(row)

    async def list_executions(
        self,
        status_filter: Optional[List[DocumentWorkflowStatus]] = None,
        limit: int = 100,
    ) -> List[DocumentWorkflowState]:
        """List executions, optionally filtered by status via ORM."""
        from app.api.models.workflow_execution import WorkflowExecution
        
        query = select(WorkflowExecution)
        
        if status_filter:
            status_values = [s.value for s in status_filter]
            query = query.where(WorkflowExecution.status.in_(status_values))
        
        query = query.order_by(WorkflowExecution.execution_id.desc()).limit(limit)
        
        result = await self._db.execute(query)
        rows = result.scalars().all()

        return [self._row_to_state(row) for row in rows]

    def _row_to_state(self, row) -> DocumentWorkflowState:
        """Convert ORM object to DocumentWorkflowState."""
        execution_log = row.execution_log if isinstance(row.execution_log, list) else json.loads(row.execution_log or '[]')
        retry_counts = row.retry_counts if isinstance(row.retry_counts, dict) else json.loads(row.retry_counts or '{}')

        # Parse pending_choices if present
        pending_choices = None
        if row.pending_choices:
            pending_choices = row.pending_choices if isinstance(row.pending_choices, list) else json.loads(row.pending_choices)

        # Parse context_state
        context_state = {}
        if row.context_state:
            context_state = row.context_state if isinstance(row.context_state, dict) else json.loads(row.context_state)

        # Parse node history
        node_history = [
            NodeExecution(
                node_id=entry["node_id"],
                outcome=entry["outcome"],
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                metadata=entry.get("metadata", {}),
            )
            for entry in execution_log
        ]

        # Derive timestamps from execution log
        first_entry = execution_log[0] if execution_log else None
        created_at = datetime.fromisoformat(first_entry["timestamp"]) if first_entry else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(execution_log[-1]["timestamp"]) if execution_log else created_at

        # Use stored status
        status = DocumentWorkflowStatus(row.status) if row.status else DocumentWorkflowStatus.RUNNING

        return DocumentWorkflowState(
            execution_id=row.execution_id,
            project_id=row.document_id or "unknown",
            document_type=row.document_type or "unknown",
            workflow_id=row.workflow_id or "unknown",
            user_id=str(row.user_id) if row.user_id else None,
            current_node_id=row.current_node_id,
            status=status,
            node_history=node_history,
            retry_counts=retry_counts,
            gate_outcome=row.gate_outcome,
            terminal_outcome=row.terminal_outcome,
            thread_id=row.thread_id,
            context_state=context_state,
            pending_user_input=row.pending_user_input or False,
            pending_user_input_rendered=row.pending_user_input_rendered,
            pending_choices=pending_choices,
            pending_user_input_payload=row.pending_user_input_payload,
            pending_user_input_schema_ref=row.pending_user_input_schema_ref,
            created_at=created_at,
            updated_at=updated_at,
        )