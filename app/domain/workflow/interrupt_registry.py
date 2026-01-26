"""Operator Interrupt Registry (ADR-043 Phase 5 & 8).

Tracks pending operator interrupts across workflow executions.
Provides a unified view for the Production Line UI.

Interrupt types:
- clarification: PGC node awaiting user answers
- audit_review: QA failure requiring operator decision
- constraint_conflict: Constraint violation requiring resolution
- escalation: Circuit breaker tripped, requires operator decision

Phase 8 additions:
- EscalationResolution: Acknowledge halt without fixing underlying issue
- escalate(): Move document from Halted to Escalated state
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.api.models.project import Project
    from app.api.models.workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


InterruptType = Literal["clarification", "audit_review", "constraint_conflict", "escalation"]


@dataclass
class OperatorInterrupt:
    """A pending operator interrupt requiring resolution.

    Maps to a paused workflow execution that needs user input.
    """

    id: str  # Same as execution_id for simplicity
    execution_id: str
    project_id: str
    document_type: str
    interrupt_type: InterruptType
    payload: Dict[str, Any]  # Questions, halt details, etc.
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[Dict[str, Any]] = None

    # Additional context
    current_node_id: Optional[str] = None
    workflow_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API responses."""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "project_id": self.project_id,
            "document_type": self.document_type,
            "interrupt_type": self.interrupt_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "current_node_id": self.current_node_id,
            "workflow_id": self.workflow_id,
        }


@dataclass
class EscalationResolution:
    """Resolution for acknowledging a halt without fixing the underlying issue.

    Per ADR-043 Phase 8: Allows operator to acknowledge and continue
    without resolving the root cause. Logged for compliance review.
    """

    acknowledged_by: str  # User ID or name who acknowledged
    acknowledged_at: datetime
    notes: Optional[str] = None  # Operator notes explaining the decision

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for audit logging."""
        return {
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat(),
            "notes": self.notes,
        }


def _determine_interrupt_type(execution: Any) -> InterruptType:
    """Determine interrupt type from execution state.

    Args:
        execution: The paused workflow execution (WorkflowExecution)

    Returns:
        The interrupt type based on current node and state
    """
    current_node = (execution.current_node_id or "").lower()
    context_state = execution.context_state or {}

    # Check for escalation (circuit breaker tripped)
    if context_state.get("escalation_active"):
        return "escalation"

    # Check for constraint conflicts
    if context_state.get("constraint_conflict"):
        return "constraint_conflict"

    # PGC nodes trigger clarification
    if "pgc" in current_node:
        return "clarification"

    # QA nodes that paused typically need audit review
    if "qa" in current_node:
        return "audit_review"

    # Default to clarification for other pauses
    return "clarification"


def _build_interrupt_payload(execution: Any) -> Dict[str, Any]:
    """Build interrupt payload from execution state.

    Args:
        execution: The paused workflow execution (WorkflowExecution)

    Returns:
        Structured payload with questions, choices, etc.
    """
    payload: Dict[str, Any] = {}

    # Include rendered prompt if available
    if execution.pending_user_input_rendered:
        payload["prompt"] = execution.pending_user_input_rendered

    # Include choices if available
    if execution.pending_choices:
        payload["choices"] = execution.pending_choices

    # Include structured payload if available
    if execution.pending_user_input_payload:
        payload["data"] = execution.pending_user_input_payload

    # Include schema reference for validation
    if execution.pending_user_input_schema_ref:
        payload["schema_ref"] = execution.pending_user_input_schema_ref

    # Include escalation options if applicable
    context_state = execution.context_state or {}
    if context_state.get("escalation_options"):
        payload["escalation_options"] = context_state["escalation_options"]

    return payload


class InterruptRegistry:
    """Registry for tracking and resolving operator interrupts.

    Provides a project-scoped view of all paused workflow executions
    that require operator input.

    Usage:
        registry = InterruptRegistry(db)
        interrupts = await registry.get_pending(project_id)
        await registry.resolve(interrupt_id, resolution)
    """

    def __init__(self, db: AsyncSession):
        """Initialize registry with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_pending(self, project_id: str) -> List[OperatorInterrupt]:
        """Get all pending interrupts for a project.

        Args:
            project_id: Project ID (UUID string or project_id)

        Returns:
            List of pending OperatorInterrupt objects
        """
        # Lazy import to avoid circular dependency
        from app.api.models.project import Project
        from app.api.models.workflow_execution import WorkflowExecution

        # Resolve project UUID
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            result = await self.db.execute(
                select(Project).where(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                return []
            project_uuid = project.id

        # Query paused executions for this project
        result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.project_id == project_uuid)
            .where(WorkflowExecution.pending_user_input == True)
            .where(WorkflowExecution.status == "paused")
        )
        executions = result.scalars().all()

        # Map to OperatorInterrupt objects
        interrupts = []
        for ex in executions:
            interrupt = OperatorInterrupt(
                id=ex.execution_id,
                execution_id=ex.execution_id,
                project_id=str(project_uuid),
                document_type=ex.document_type or "unknown",
                interrupt_type=_determine_interrupt_type(ex),
                payload=_build_interrupt_payload(ex),
                created_at=datetime.now(timezone.utc),  # TODO: Add created_at to execution
                current_node_id=ex.current_node_id,
                workflow_id=ex.workflow_id,
            )
            interrupts.append(interrupt)

        logger.info(f"Found {len(interrupts)} pending interrupts for project {project_id}")
        return interrupts

    async def get_interrupt(self, interrupt_id: str) -> Optional[OperatorInterrupt]:
        """Get a specific interrupt by ID.

        Args:
            interrupt_id: The interrupt ID (same as execution_id)

        Returns:
            OperatorInterrupt or None if not found/not pending
        """
        # Lazy import to avoid circular dependency
        from app.api.models.workflow_execution import WorkflowExecution

        result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.execution_id == interrupt_id)
            .where(WorkflowExecution.pending_user_input == True)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            return None

        return OperatorInterrupt(
            id=execution.execution_id,
            execution_id=execution.execution_id,
            project_id=str(execution.project_id) if execution.project_id else "",
            document_type=execution.document_type or "unknown",
            interrupt_type=_determine_interrupt_type(execution),
            payload=_build_interrupt_payload(execution),
            created_at=datetime.now(timezone.utc),
            current_node_id=execution.current_node_id,
            workflow_id=execution.workflow_id,
        )

    async def resolve(
        self,
        interrupt_id: str,
        resolution: Dict[str, Any],
    ) -> bool:
        """Resolve an interrupt and resume execution.

        This clears the pause state and updates context_state with the resolution.
        The PlanExecutor will re-run the paused node on next tick.

        Args:
            interrupt_id: The interrupt ID to resolve
            resolution: Resolution data (answers, decision, etc.)

        Returns:
            True if resolved successfully, False if interrupt not found
        """
        # Lazy import to avoid circular dependency
        from app.api.models.workflow_execution import WorkflowExecution

        result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.execution_id == interrupt_id)
            .where(WorkflowExecution.pending_user_input == True)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            logger.warning(f"Interrupt not found or already resolved: {interrupt_id}")
            return False

        # Clear pause state
        execution.pending_user_input = False
        execution.pending_user_input_rendered = None
        execution.pending_choices = None
        execution.pending_user_input_payload = None
        execution.pending_user_input_schema_ref = None
        execution.status = "running"

        # Update context_state with resolution
        context_state = execution.context_state or {}
        context_state["last_resolution"] = resolution
        context_state["resolution_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Store answers in context_state for PGC resolution
        if "answers" in resolution:
            existing_answers = context_state.get("pgc_answers", {})
            existing_answers.update(resolution["answers"])
            context_state["pgc_answers"] = existing_answers

        execution.context_state = context_state

        await self.db.flush()

        logger.info(
            f"Resolved interrupt {interrupt_id} for {execution.document_type}, "
            f"resuming execution"
        )
        return True

    async def register(
        self,
        execution_id: str,
        interrupt_type: InterruptType,
        payload: Dict[str, Any],
    ) -> str:
        """Register a new interrupt for an execution.

        This is called by PlanExecutor when a node returns needs_user_input.
        The interrupt is stored as pause state on the WorkflowExecution.

        Args:
            execution_id: The workflow execution ID
            interrupt_type: Type of interrupt
            payload: Interrupt payload (questions, choices, etc.)

        Returns:
            The interrupt ID (same as execution_id)
        """
        # Lazy import to avoid circular dependency
        from app.api.models.workflow_execution import WorkflowExecution

        result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.execution_id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")

        # Set pause state
        execution.pending_user_input = True
        execution.pending_user_input_rendered = payload.get("prompt")
        execution.pending_choices = payload.get("choices")
        execution.pending_user_input_payload = payload.get("data")
        execution.pending_user_input_schema_ref = payload.get("schema_ref")
        execution.status = "paused"

        # Store interrupt type in context_state
        context_state = execution.context_state or {}
        context_state["interrupt_type"] = interrupt_type
        context_state["interrupt_created_at"] = datetime.now(timezone.utc).isoformat()
        execution.context_state = context_state

        await self.db.flush()

        logger.info(
            f"Registered {interrupt_type} interrupt for execution {execution_id}"
        )
        return execution_id

    async def escalate(
        self,
        interrupt_id: str,
        escalation: EscalationResolution,
    ) -> bool:
        """Escalate an interrupt without resolving the underlying issue.

        Per ADR-043 Phase 8: Allows operator to acknowledge a halt and
        continue without fixing the root cause. The document moves from
        Halted to Escalated state.

        This is logged for compliance review.

        Args:
            interrupt_id: The interrupt ID to escalate
            escalation: EscalationResolution with acknowledgment details

        Returns:
            True if escalated successfully, False if interrupt not found
        """
        # Lazy import to avoid circular dependency
        from app.api.models.workflow_execution import WorkflowExecution

        result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.execution_id == interrupt_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            logger.warning(f"Execution not found for escalation: {interrupt_id}")
            return False

        # Clear pause state
        execution.pending_user_input = False
        execution.pending_user_input_rendered = None
        execution.pending_choices = None
        execution.pending_user_input_payload = None
        execution.pending_user_input_schema_ref = None

        # Set terminal outcome to escalated
        execution.status = "completed"
        execution.terminal_outcome = "escalated"

        # Update context_state with escalation details for audit
        context_state = execution.context_state or {}
        context_state["escalation"] = escalation.to_dict()
        context_state["escalated_at"] = datetime.now(timezone.utc).isoformat()
        execution.context_state = context_state

        await self.db.flush()

        # Audit log for compliance
        logger.warning(
            f"ESCALATION: Interrupt {interrupt_id} for {execution.document_type} "
            f"escalated by {escalation.acknowledged_by}. "
            f"Notes: {escalation.notes or 'None provided'}"
        )

        return True
