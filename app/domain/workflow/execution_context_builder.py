"""Execution context assembly extracted from PlanExecutor.

Builds DocumentWorkflowContext for node execution.
Extracted in second-pass decomposition of plan_executor.py.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.nodes.base import DocumentWorkflowContext
from app.domain.workflow.plan_models import WorkflowPlan
from app.domain.workflow.thread_manager import ThreadManager

logger = logging.getLogger(__name__)


async def build_context(
    state: DocumentWorkflowState,
    plan: WorkflowPlan,
    user_input: Optional[Any],
    user_choice: Optional[str],
    db_session: Optional[AsyncSession] = None,
    thread_manager: Optional[ThreadManager] = None,
) -> DocumentWorkflowContext:
    """Build execution context for a node.

    Args:
        state: Current execution state
        plan: Workflow plan
        user_input: Optional user input
        user_choice: Optional user choice
        db_session: Optional database session (for authority lookups)
        thread_manager: Optional thread manager (for conversation history)

    Returns:
        DocumentWorkflowContext for node execution
    """
    # Build extra context with execution metadata
    extra = {
        "execution_id": state.execution_id,
        "workflow_id": state.workflow_id,
        "project_id": state.project_id,
        "retry_count": state.get_retry_count(state.current_node_id),
    }
    # Pass db_session for authority lookups in PGC gates (ADR-064)
    if db_session:
        extra["db_session"] = db_session
    if user_input:
        extra["user_input"] = user_input
    if user_choice:
        extra["user_choice"] = user_choice

    # Load conversation history from thread if available
    conversation_history = []
    if state.thread_id and thread_manager:
        try:
            conversation_history = await thread_manager.load_conversation_history(
                state.thread_id
            )
            logger.debug(
                f"Loaded {len(conversation_history)} messages from thread {state.thread_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")

    # Load produced documents from context_state
    document_content = {}
    for key, value in state.context_state.items():
        if key.startswith("document_") and isinstance(value, dict):
            # Extract document type from key (e.g., "document_discovery" -> "discovery")
            doc_type = key[len("document_"):]
            document_content[doc_type] = value

    # Also include last_produced_document for easy access
    if state.context_state.get("last_produced_document"):
        document_content["_last"] = state.context_state["last_produced_document"]

    logger.debug(f"Loaded {len(document_content)} documents from context_state")

    return DocumentWorkflowContext(
        project_id=state.project_id,
        document_type=state.document_type,
        thread_id=state.thread_id,
        document_content=document_content,
        conversation_history=conversation_history,
        input_documents=state.context_state.get("input_documents", {}),
        user_responses={},
        extra=extra,
        context_state=state.context_state,
    )
