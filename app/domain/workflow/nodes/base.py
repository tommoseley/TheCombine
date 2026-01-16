"""Base classes for node executors (ADR-039).

Defines the NodeExecutor protocol and shared types used by all node executors.

INVARIANTS (WS-INTAKE-ENGINE-001):

All Node Executors MUST NOT:
- Inspect or select outgoing edges
- Mutate workflow control state (current_node_id, retry_counts)
- Infer routing decisions
- Access other nodes in the plan

All routing decisions are performed EXCLUSIVELY by the EdgeRouter.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class DocumentWorkflowStatus(str, Enum):
    """Status of a document workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class NodeResult:
    """Result of executing a node.

    This is the output contract between a NodeExecutor and the EdgeRouter.
    The outcome string is used by EdgeRouter to select the next edge.
    """
    outcome: str  # e.g., "success", "failed", "qualified", "needs_user_input"
    produced_document: Optional[Dict[str, Any]] = None
    requires_user_input: bool = False
    user_prompt: Optional[str] = None
    user_choices: Optional[List[str]] = None  # For gate nodes
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        produced_document: Optional[Dict[str, Any]] = None,
        **metadata: Any,
    ) -> "NodeResult":
        """Create a success result."""
        return cls(
            outcome="success",
            produced_document=produced_document,
            metadata=metadata,
        )

    @classmethod
    def failed(cls, reason: str, **metadata: Any) -> "NodeResult":
        """Create a failed result."""
        return cls(
            outcome="failed",
            metadata={"failure_reason": reason, **metadata},
        )

    @classmethod
    def needs_user_input(
        cls,
        prompt: str,
        choices: Optional[List[str]] = None,
        **metadata: Any,
    ) -> "NodeResult":
        """Create a result that requires user input."""
        return cls(
            outcome="needs_user_input",
            requires_user_input=True,
            user_prompt=prompt,
            user_choices=choices,
            metadata=metadata,
        )


@dataclass
class DocumentWorkflowContext:
    """Context for document workflow execution.

    Contains the document being created, thread reference, and
    any context accumulated during execution.
    """
    document_id: str
    document_type: str
    thread_id: Optional[str] = None

    # Document content being built
    document_content: Dict[str, Any] = field(default_factory=dict)

    # Conversation context (for concierge nodes)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Input documents from upstream
    input_documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # User responses collected during execution
    user_responses: Dict[str, Any] = field(default_factory=dict)

    # Additional context data
    extra: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
        })

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message from conversation history."""
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "assistant":
                return msg.get("content")
        return None

    def set_user_response(self, key: str, value: Any) -> None:
        """Set a user response value."""
        self.user_responses[key] = value

    def get_user_response(self, key: str, default: Any = None) -> Any:
        """Get a user response value."""
        return self.user_responses.get(key, default)


class NodeExecutor(ABC):
    """Abstract base class for node executors.

    Each node type (concierge, task, qa, gate, end) has a dedicated
    executor that implements this interface.

    BOUNDARY CONSTRAINTS:
    - execute() returns a NodeResult with an outcome
    - The outcome is used by EdgeRouter to select the next edge
    - Executors MUST NOT access edges or make routing decisions
    """

    @abstractmethod
    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute the node and return a result.

        Args:
            node_id: The ID of the node being executed
            node_config: The node's configuration from the plan
            context: The workflow context with document and conversation state
            state_snapshot: Read-only snapshot of workflow state (for inspection only)

        Returns:
            NodeResult indicating the outcome of execution

        Note:
            state_snapshot is READ-ONLY. Executors MUST NOT mutate workflow state.
            State mutations are performed by the PlanExecutor after execution.
        """
        pass

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        raise NotImplementedError("Subclass must implement get_supported_node_type")


class LLMService(Protocol):
    """Protocol for LLM service dependency injection."""

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a completion from messages."""
        ...


class PromptLoader(Protocol):
    """Protocol for prompt loader dependency injection."""

    def load_task_prompt(self, task_ref: str) -> str:
        """Load a task prompt by reference."""
        ...

    def load_role_prompt(self, role_ref: str) -> str:
        """Load a role prompt by reference."""
        ...
