"""PostgreSQL persistence for Document Workflow State.

Minimal implementation - stores only essential fields.
Everything else derived at runtime from execution_log.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)

logger = logging.getLogger(__name__)


class PgStatePersistence:
    """PostgreSQL-backed state persistence.

    Stores minimal state in workflow_executions table:
    - execution_id (PK)
    - current_node_id
    - execution_log (JSONB)
    - retry_counts (JSONB)
    - gate_outcome
    - terminal_outcome

    All other fields derived from execution_log at load time.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, state: DocumentWorkflowState) -> None:
        """Save workflow state to database."""
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

        # Upsert using INSERT ... ON CONFLICT
        await self._db.execute(
            text("""
                INSERT INTO workflow_executions
                    (execution_id, current_node_id, execution_log, retry_counts, gate_outcome, terminal_outcome)
                VALUES
                    (:execution_id, :current_node_id, :execution_log, :retry_counts, :gate_outcome, :terminal_outcome)
                ON CONFLICT (execution_id) DO UPDATE SET
                    current_node_id = EXCLUDED.current_node_id,
                    execution_log = EXCLUDED.execution_log,
                    retry_counts = EXCLUDED.retry_counts,
                    gate_outcome = EXCLUDED.gate_outcome,
                    terminal_outcome = EXCLUDED.terminal_outcome
            """),
            {
                "execution_id": state.execution_id,
                "current_node_id": state.current_node_id,
                "execution_log": json.dumps(execution_log),
                "retry_counts": json.dumps(state.retry_counts),
                "gate_outcome": state.gate_outcome,
                "terminal_outcome": state.terminal_outcome,
            },
        )
        await self._db.commit()

    async def load(self, execution_id: str) -> Optional[DocumentWorkflowState]:
        """Load workflow state by execution ID."""
        result = await self._db.execute(
            text("""
                SELECT execution_id, current_node_id, execution_log, retry_counts, gate_outcome, terminal_outcome
                FROM workflow_executions
                WHERE execution_id = :execution_id
            """),
            {"execution_id": execution_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_state(row)

    async def load_by_document(
        self, document_id: str, workflow_id: str
    ) -> Optional[DocumentWorkflowState]:
        """Load state by document and workflow ID.

        Scans execution_log for matching document_id/workflow_id in first entry.
        """
        # Query all and filter - not optimal but keeps schema minimal
        result = await self._db.execute(
            text("""
                SELECT execution_id, current_node_id, execution_log, retry_counts, gate_outcome, terminal_outcome
                FROM workflow_executions
                WHERE terminal_outcome IS NULL
            """)
        )

        for row in result.fetchall():
            state = self._row_to_state(row)
            if state.document_id == document_id and state.workflow_id == workflow_id:
                return state

        return None

    async def list_executions(
        self,
        status_filter: Optional[List[DocumentWorkflowStatus]] = None,
        limit: int = 100,
    ) -> List[DocumentWorkflowState]:
        """List executions, optionally filtered by status."""
        # Fetch all (up to limit) and filter in Python
        # Status is derived, so we can't filter in SQL efficiently
        result = await self._db.execute(
            text("""
                SELECT execution_id, current_node_id, execution_log, retry_counts, gate_outcome, terminal_outcome
                FROM workflow_executions
                ORDER BY execution_id DESC
                LIMIT :limit
            """),
            {"limit": limit * 2},  # Fetch extra to account for filtering
        )

        states = []
        for row in result.fetchall():
            state = self._row_to_state(row)

            # Apply status filter
            if status_filter and state.status not in status_filter:
                continue

            states.append(state)

            if len(states) >= limit:
                break

        return states

    def _row_to_state(self, row) -> DocumentWorkflowState:
        """Convert database row to DocumentWorkflowState.

        Derives document_id, workflow_id, status, timestamps from execution_log.
        """
        execution_log = row.execution_log if isinstance(row.execution_log, list) else json.loads(row.execution_log)
        retry_counts = row.retry_counts if isinstance(row.retry_counts, dict) else json.loads(row.retry_counts)

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

        # Derive fields from first log entry metadata
        first_entry = execution_log[0] if execution_log else {}
        first_meta = first_entry.get("metadata", {})

        document_id = first_meta.get("document_id", "unknown")
        document_type = first_meta.get("document_type", "unknown")
        workflow_id = first_meta.get("workflow_id", "unknown")

        # Derive timestamps
        created_at = datetime.fromisoformat(first_entry["timestamp"]) if execution_log else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(execution_log[-1]["timestamp"]) if execution_log else created_at

        # Derive status
        if row.terminal_outcome:
            status = DocumentWorkflowStatus.COMPLETED
        elif row.gate_outcome:
            status = DocumentWorkflowStatus.PAUSED
        else:
            status = DocumentWorkflowStatus.RUNNING

        return DocumentWorkflowState(
            execution_id=row.execution_id,
            document_id=document_id,
            document_type=document_type,
            workflow_id=workflow_id,
            current_node_id=row.current_node_id,
            status=status,
            node_history=node_history,
            retry_counts=retry_counts,
            gate_outcome=row.gate_outcome,
            terminal_outcome=row.terminal_outcome,
            created_at=created_at,
            updated_at=updated_at,
        )
