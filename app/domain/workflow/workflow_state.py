"""Workflow state - track overall workflow execution progress.

Manages the complete state of a workflow execution including
step progress, iteration tracking, and acceptance decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.workflow.step_state import StepState


class WorkflowStatus(Enum):
    """Overall workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_ACCEPTANCE = "waiting_acceptance"
    WAITING_CLARIFICATION = "waiting_clarification"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class IterationProgress:
    """Track progress through an iteration."""
    step_id: str
    total: int
    completed: int
    current_index: int
    entity_ids: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        return self.completed >= self.total
    
    @property
    def remaining(self) -> int:
        return self.total - self.completed


@dataclass
class AcceptanceDecision:
    """Record of an acceptance decision."""
    doc_type: str
    scope_id: Optional[str]
    accepted: bool
    comment: Optional[str]
    decided_by: str
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "scope_id": self.scope_id,
            "accepted": self.accepted,
            "comment": self.comment,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcceptanceDecision":
        return cls(
            doc_type=data["doc_type"],
            scope_id=data.get("scope_id"),
            accepted=data["accepted"],
            comment=data.get("comment"),
            decided_by=data["decided_by"],
            decided_at=datetime.fromisoformat(data["decided_at"]),
        )


@dataclass
class WorkflowState:
    """Complete workflow execution state."""
    
    workflow_id: str
    project_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    
    # Step tracking
    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    step_states: Dict[str, StepState] = field(default_factory=dict)
    
    # Iteration tracking
    iteration_progress: Dict[str, IterationProgress] = field(default_factory=dict)
    
    # Acceptance tracking
    pending_acceptance: Optional[str] = None
    pending_acceptance_scope_id: Optional[str] = None
    acceptance_decisions: Dict[str, AcceptanceDecision] = field(default_factory=dict)
    
    # Clarification tracking
    pending_clarification_step_id: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error info
    error: Optional[str] = None
    
    def start(self) -> None:
        """Mark workflow as started."""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def fail(self, error: str) -> None:
        """Mark workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)
    
    def cancel(self) -> None:
        """Mark workflow as cancelled."""
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
    
    def wait_for_acceptance(self, doc_type: str, scope_id: Optional[str] = None) -> None:
        """Pause workflow for acceptance decision."""
        self.status = WorkflowStatus.WAITING_ACCEPTANCE
        self.pending_acceptance = doc_type
        self.pending_acceptance_scope_id = scope_id
    
    def wait_for_clarification(self, step_id: str) -> None:
        """Pause workflow for clarification answers."""
        self.status = WorkflowStatus.WAITING_CLARIFICATION
        self.pending_clarification_step_id = step_id
    
    def resume(self) -> None:
        """Resume workflow from waiting state."""
        self.status = WorkflowStatus.RUNNING
        self.pending_acceptance = None
        self.pending_acceptance_scope_id = None
        self.pending_clarification_step_id = None
    
    def mark_step_complete(self, step_id: str) -> None:
        """Mark a step as completed."""
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
    
    def is_step_complete(self, step_id: str) -> bool:
        """Check if step is complete."""
        return step_id in self.completed_steps
    
    def get_step_state(self, step_id: str) -> Optional[StepState]:
        """Get state for a specific step."""
        return self.step_states.get(step_id)
    
    def set_step_state(self, step_id: str, state: StepState) -> None:
        """Set state for a specific step."""
        self.step_states[step_id] = state
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "workflow_id": self.workflow_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "current_step_id": self.current_step_id,
            "completed_steps": self.completed_steps,
            "step_states": {k: v.to_dict() for k, v in self.step_states.items()},
            "iteration_progress": {
                k: {
                    "step_id": v.step_id,
                    "total": v.total,
                    "completed": v.completed,
                    "current_index": v.current_index,
                    "entity_ids": v.entity_ids,
                }
                for k, v in self.iteration_progress.items()
            },
            "pending_acceptance": self.pending_acceptance,
            "pending_acceptance_scope_id": self.pending_acceptance_scope_id,
            "acceptance_decisions": {k: v.to_dict() for k, v in self.acceptance_decisions.items()},
            "pending_clarification_step_id": self.pending_clarification_step_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Restore from dict."""
        state = cls(
            workflow_id=data["workflow_id"],
            project_id=data["project_id"],
            status=WorkflowStatus(data["status"]),
            current_step_id=data.get("current_step_id"),
            completed_steps=data.get("completed_steps", []),
            pending_acceptance=data.get("pending_acceptance"),
            pending_acceptance_scope_id=data.get("pending_acceptance_scope_id"),
            pending_clarification_step_id=data.get("pending_clarification_step_id"),
            error=data.get("error"),
        )
        
        # Restore step states
        for step_id, step_data in data.get("step_states", {}).items():
            state.step_states[step_id] = StepState.from_dict(step_data)
        
        # Restore iteration progress
        for key, prog_data in data.get("iteration_progress", {}).items():
            state.iteration_progress[key] = IterationProgress(
                step_id=prog_data["step_id"],
                total=prog_data["total"],
                completed=prog_data["completed"],
                current_index=prog_data["current_index"],
                entity_ids=prog_data.get("entity_ids", []),
            )
        
        # Restore acceptance decisions
        for key, dec_data in data.get("acceptance_decisions", {}).items():
            state.acceptance_decisions[key] = AcceptanceDecision.from_dict(dec_data)
        
        # Restore timestamps
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])
        
        return state
