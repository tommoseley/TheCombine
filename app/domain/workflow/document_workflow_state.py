"""Document workflow execution state (ADR-039).

Tracks the state of a document workflow execution including:
- Current node position
- Node execution history
- Retry counts for circuit breaker
- Terminal outcomes

INVARIANTS (WS-INTAKE-ENGINE-001):
- State is persisted after every node completion
- State mutations are performed only by PlanExecutor
- Retry counter is scoped to (document_id, generating_node_id)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class DocumentWorkflowStatus(str, Enum):
    """Status of a document workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"         # Waiting for user input
    COMPLETED = "completed"   # Reached terminal node
    FAILED = "failed"         # Execution error


@dataclass
class NodeExecution:
    """Record of a single node execution."""
    node_id: str
    outcome: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "node_id": self.node_id,
            "outcome": self.outcome,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeExecution":
        """Deserialize from dict."""
        return cls(
            node_id=data["node_id"],
            outcome=data["outcome"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DocumentWorkflowState:
    """State of a document workflow execution.

    This is the authoritative record of execution progress.
    It is persisted after every node completion.
    """
    # Identity
    execution_id: str
    workflow_id: str  # ID of the workflow plan
    document_id: str
    document_type: str

    # Current position
    current_node_id: str
    status: DocumentWorkflowStatus

    # User who initiated this execution
    user_id: Optional[str] = None

    # Execution history (ordered)
    node_history: List[NodeExecution] = field(default_factory=list)

    # Retry tracking per (generating_node_id)
    # Key: node_id, Value: retry count
    # Only QA failures increment retries for the upstream generating node
    retry_counts: Dict[str, int] = field(default_factory=dict)

    # Track which node generated content being QA'd (for retry routing)
    generating_node_id: Optional[str] = None

    # Outcomes (set when reaching terminal)
    gate_outcome: Optional[str] = None
    terminal_outcome: Optional[str] = None

    # Thread reference (ADR-035)
    thread_id: Optional[str] = None

    # Structured context state (ADR-040)
    # This is the ONLY source of continuity for LLM invocations.
    # Contains governed data derived from prior turns, NOT raw transcripts.
    # Example: {"intake_summary": "...", "known_constraints": [], "open_gaps": []}
    context_state: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Pause state
    pending_user_input: bool = False
    pending_prompt: Optional[str] = None
    pending_choices: Optional[List[str]] = None

    # Escalation (when circuit breaker trips)
    escalation_active: bool = False
    escalation_options: List[str] = field(default_factory=list)

    def record_execution(
        self,
        node_id: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a node execution.

        Args:
            node_id: The executed node ID
            outcome: The execution outcome
            metadata: Optional execution metadata
        """
        self.node_history.append(NodeExecution(
            node_id=node_id,
            outcome=outcome,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        ))
        self.updated_at = datetime.utcnow()

    def increment_retry(self, generating_node_id: str) -> int:
        """Increment retry count for a generating node.

        Per WS-INTAKE-ENGINE-001:
        - Retry counter is scoped to (document_id, generating_node_id)
        - Only QA failures increment retries

        Args:
            generating_node_id: The node that generated the content being QA'd

        Returns:
            The new retry count
        """
        current = self.retry_counts.get(generating_node_id, 0)
        self.retry_counts[generating_node_id] = current + 1
        self.updated_at = datetime.utcnow()
        return self.retry_counts[generating_node_id]

    def get_retry_count(self, node_id: str) -> int:
        """Get retry count for a node.

        Args:
            node_id: The node ID

        Returns:
            Current retry count (0 if never retried)
        """
        return self.retry_counts.get(node_id, 0)

    def set_paused(
        self,
        prompt: Optional[str] = None,
        choices: Optional[List[str]] = None,
    ) -> None:
        """Set state to paused waiting for user input.

        Args:
            prompt: Optional prompt to show user
            choices: Optional list of choices
        """
        self.status = DocumentWorkflowStatus.PAUSED
        self.pending_user_input = True
        self.pending_prompt = prompt
        self.pending_choices = choices
        self.updated_at = datetime.utcnow()

    def clear_pause(self) -> None:
        """Clear pause state and resume running."""
        self.status = DocumentWorkflowStatus.RUNNING
        self.pending_user_input = False
        self.pending_prompt = None
        self.pending_choices = None
        self.updated_at = datetime.utcnow()

    def set_escalation(self, options: List[str]) -> None:
        """Set escalation state (circuit breaker tripped).

        Args:
            options: Available escalation options
        """
        self.escalation_active = True
        self.escalation_options = options
        self.status = DocumentWorkflowStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def clear_escalation(self) -> None:
        """Clear escalation state."""
        self.escalation_active = False
        self.escalation_options = []
        self.updated_at = datetime.utcnow()

    def update_context_state(self, delta: Dict[str, Any]) -> None:
        """Update context state with delta from node execution.

        Per ADR-040: context_state is the ONLY source of continuity for LLM
        invocations. It contains structured, governed data — NOT transcripts.

        Args:
            delta: State updates to merge. Keys are replaced, not deep-merged.
        """
        self.context_state.update(delta)
        self.updated_at = datetime.utcnow()

    def set_completed(
        self,
        terminal_outcome: str,
        gate_outcome: Optional[str] = None,
    ) -> None:
        """Set state to completed with outcomes.

        Args:
            terminal_outcome: The terminal outcome (stabilized, blocked, abandoned)
            gate_outcome: Optional gate outcome (qualified, not_ready, etc.)
        """
        self.status = DocumentWorkflowStatus.COMPLETED
        self.terminal_outcome = terminal_outcome
        self.gate_outcome = gate_outcome
        self.updated_at = datetime.utcnow()

    def set_failed(self, reason: str) -> None:
        """Set state to failed.

        Args:
            reason: Failure reason
        """
        self.status = DocumentWorkflowStatus.FAILED
        self.record_execution(
            node_id=self.current_node_id,
            outcome="failed",
            metadata={"failure_reason": reason},
        )
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for persistence."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "user_id": self.user_id,
            "current_node_id": self.current_node_id,
            "status": self.status.value,
            "node_history": [n.to_dict() for n in self.node_history],
            "retry_counts": self.retry_counts,
            "gate_outcome": self.gate_outcome,
            "terminal_outcome": self.terminal_outcome,
            "thread_id": self.thread_id,
            "context_state": self.context_state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "pending_user_input": self.pending_user_input,
            "pending_prompt": self.pending_prompt,
            "pending_choices": self.pending_choices,
            "escalation_active": self.escalation_active,
            "escalation_options": self.escalation_options,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentWorkflowState":
        """Deserialize from dict."""
        return cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            document_id=data["document_id"],
            document_type=data["document_type"],
            user_id=data.get("user_id"),
            current_node_id=data["current_node_id"],
            status=DocumentWorkflowStatus(data["status"]),
            node_history=[
                NodeExecution.from_dict(n) for n in data.get("node_history", [])
            ],
            retry_counts=data.get("retry_counts", {}),
            gate_outcome=data.get("gate_outcome"),
            terminal_outcome=data.get("terminal_outcome"),
            thread_id=data.get("thread_id"),
            context_state=data.get("context_state", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            pending_user_input=data.get("pending_user_input", False),
            pending_prompt=data.get("pending_prompt"),
            pending_choices=data.get("pending_choices"),
            escalation_active=data.get("escalation_active", False),
            escalation_options=data.get("escalation_options", []),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DocumentWorkflowState":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
