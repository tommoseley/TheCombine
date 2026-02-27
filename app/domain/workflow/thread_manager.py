"""Thread Manager for Document Interaction Workflows (ADR-035, ADR-039).

Manages durable conversation threads for workflows that declare thread ownership.
Bridges the workflow executor with the thread execution service.

Key Responsibilities:
- Create threads when workflows start (if plan.thread_ownership.owns_thread)
- Persist conversation turns to thread ledger
- Load conversation history when resuming interrupted workflows

INVARIANTS (WS-ADR-025 Phase 3):
- Thread ID is stored in DocumentWorkflowState.thread_id
- Conversation messages are persisted as ledger entries (type: conversation_turn)
- Thread status mirrors workflow status (running/complete/failed)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class ThreadManager:
    """Manages conversation threads for Document Interaction Workflows.

    Per ADR-035 and ADR-039:
    - Threads are durable containers for user intent and conversation
    - Conversation turns are recorded in the ledger for audit
    - Threads can be resumed if workflow is interrupted
    """

    # Custom ledger entry type for conversation turns
    CONVERSATION_TURN_TYPE = "conversation_turn"

    def __init__(self, db: AsyncSession):
        """Initialize thread manager.

        Args:
            db: Database session
        """
        # Deferred import to avoid circular dependency
        from app.domain.services.thread_execution_service import ThreadExecutionService as TES

        self.db = db
        self._service = TES(db)

    async def create_workflow_thread(
        self,
        workflow_id: str,
        project_id: str,
        document_type: str,
        execution_id: str,
        thread_purpose: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """Create a new thread for a workflow execution.

        Args:
            workflow_id: The workflow plan ID
            project_id: The document being processed
            document_type: Type of document
            execution_id: The workflow execution ID
            thread_purpose: Optional thread purpose (from plan)
            created_by: Optional creator identifier

        Returns:
            The created thread ID as string
        """
        # Build idempotency key from semantic identity
        idempotency_key = self._service.make_idempotency_key(
            operation="workflow_thread",
            space_type="document",
            space_id=UUID(int=0),  # Placeholder - could use project ID
            target_doc_type=document_type,
            target_id=project_id,
        )

        # Build target reference
        target_ref = {
            "project_id": project_id,
            "document_type": document_type,
            "execution_id": execution_id,
            "thread_purpose": thread_purpose,
        }

        # Create or get thread
        thread, created = await self._service.get_or_create_thread(
            kind=f"workflow:{workflow_id}",
            space_type="document",
            space_id=UUID(int=0),  # Placeholder - could use project ID
            target_ref=target_ref,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        if created:
            logger.info(
                f"Created workflow thread {thread.id} for execution {execution_id}"
            )
        else:
            logger.info(
                f"Resuming existing thread {thread.id} for execution {execution_id}"
            )

        return str(thread.id)

    async def start_thread(self, thread_id: str) -> None:
        """Mark thread as running.

        Args:
            thread_id: The thread ID
        """
        await self._service.start_thread(UUID(thread_id))

    async def complete_thread(self, thread_id: str) -> None:
        """Mark thread as complete.

        Args:
            thread_id: The thread ID
        """
        await self._service.complete_thread(UUID(thread_id))

    async def fail_thread(self, thread_id: str) -> None:
        """Mark thread as failed.

        Args:
            thread_id: The thread ID
        """
        await self._service.fail_thread(UUID(thread_id))

    async def record_conversation_turn(
        self,
        thread_id: str,
        role: str,
        content: str,
        node_id: Optional[str] = None,
        turn_number: Optional[int] = None,
    ) -> None:
        """Record a conversation turn to the thread ledger.

        Args:
            thread_id: The thread ID
            role: Message role (user, assistant, system)
            content: Message content
            node_id: Optional node ID where turn occurred
            turn_number: Optional turn number for ordering
        """
        # Create a work item for the turn (or reuse existing)
        work_item = await self._service.create_work_item(
            thread_id=UUID(thread_id),
            lock_scope=None,
        )

        # Build turn payload
        payload = {
            "type": self.CONVERSATION_TURN_TYPE,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if node_id:
            payload["node_id"] = node_id
        if turn_number is not None:
            payload["turn_number"] = turn_number

        # Record to ledger based on role
        if role == "user":
            await self._service.record_prompt(
                thread_id=UUID(thread_id),
                work_item_id=work_item.id,
                prompt_data=payload,
            )
        else:
            await self._service.record_response(
                thread_id=UUID(thread_id),
                work_item_id=work_item.id,
                response_data=payload,
            )

        logger.debug(f"Recorded {role} turn to thread {thread_id}")

    async def load_conversation_history(
        self,
        thread_id: str,
    ) -> List[Dict[str, Any]]:
        """Load conversation history from thread ledger.

        Args:
            thread_id: The thread ID

        Returns:
            List of message dicts with role and content, ordered by timestamp
        """
        entries = await self._service.get_ledger_entries(UUID(thread_id))

        # Filter to conversation turns and extract messages
        messages = []
        for entry in entries:
            payload = entry.payload
            if payload.get("type") == self.CONVERSATION_TURN_TYPE:
                messages.append({
                    "role": payload.get("role"),
                    "content": payload.get("content"),
                    "timestamp": payload.get("timestamp"),
                    "node_id": payload.get("node_id"),
                })

        # Sort by timestamp
        messages.sort(key=lambda m: m.get("timestamp", ""))

        # Return simplified format (just role and content)
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

    async def get_thread_status(self, thread_id: str) -> Optional[str]:
        """Get thread status.

        Args:
            thread_id: The thread ID

        Returns:
            Thread status string or None if not found
        """
        thread = await self._service.get_thread(UUID(thread_id))
        if thread:
            return thread.status.value
        return None


def should_create_thread(plan_config: Dict[str, Any]) -> bool:
    """Check if a workflow plan declares thread ownership.

    Args:
        plan_config: The workflow plan configuration

    Returns:
        True if the plan owns threads
    """
    thread_ownership = plan_config.get("thread_ownership", {})
    return thread_ownership.get("owns_thread", False)


def get_thread_purpose(plan_config: Dict[str, Any]) -> Optional[str]:
    """Get the thread purpose from a workflow plan.

    Args:
        plan_config: The workflow plan configuration

    Returns:
        Thread purpose string or None
    """
    thread_ownership = plan_config.get("thread_ownership", {})
    return thread_ownership.get("thread_purpose")
