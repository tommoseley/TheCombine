"""Node executors for Document Interaction Workflow Plans (ADR-039).

Each node type has a dedicated executor that implements the NodeExecutor protocol.

Separation Invariant (WS-INTAKE-ENGINE-001):
- Executors perform work, not control
- Executors MUST NOT inspect edges, mutate control state, or infer routing
- All routing decisions are performed exclusively by the EdgeRouter
"""

from app.domain.workflow.nodes.base import (
    NodeExecutor,
    NodeResult,
    DocumentWorkflowContext,
)
from app.domain.workflow.nodes.task import TaskNodeExecutor
from app.domain.workflow.nodes.gate import GateNodeExecutor
from app.domain.workflow.nodes.qa import QANodeExecutor
from app.domain.workflow.nodes.end import EndNodeExecutor

__all__ = [
    "NodeExecutor",
    "NodeResult",
    "DocumentWorkflowContext",
    "TaskNodeExecutor",
    "GateNodeExecutor",
    "QANodeExecutor",
    "EndNodeExecutor",
]
