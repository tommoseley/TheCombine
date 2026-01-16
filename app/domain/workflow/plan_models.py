"""Typed models for Document Interaction Workflow Plans (ADR-039).

These dataclasses represent a validated workflow plan definition.
Created by PlanLoader after validation passes.

Distinct from models.py which represents linear workflow.v1 format.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    """Valid node types per ADR-039."""
    CONCIERGE = "concierge"
    TASK = "task"
    QA = "qa"
    GATE = "gate"
    END = "end"


class EdgeKind(str, Enum):
    """Edge transition kinds."""
    AUTO = "auto"
    USER_CHOICE = "user_choice"


class ConditionOperator(str, Enum):
    """Operators for edge conditions."""
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"


@dataclass
class EdgeCondition:
    """A condition that must be met for edge traversal."""
    type: str  # e.g., "retry_count", "state_value"
    operator: ConditionOperator
    value: Any

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EdgeCondition":
        """Create from raw dict."""
        return cls(
            type=raw["type"],
            operator=ConditionOperator(raw["operator"]),
            value=raw["value"],
        )


@dataclass
class Edge:
    """A directed edge between nodes in the workflow graph."""
    edge_id: str
    from_node_id: str
    to_node_id: Optional[str]  # None for non-advancing edges
    outcome: str
    label: str
    kind: EdgeKind
    conditions: List[EdgeCondition] = field(default_factory=list)
    escalation_options: List[str] = field(default_factory=list)
    non_advancing: bool = False

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Edge":
        """Create from raw dict."""
        conditions = [
            EdgeCondition.from_dict(c)
            for c in raw.get("conditions", [])
        ]
        return cls(
            edge_id=raw["edge_id"],
            from_node_id=raw["from_node_id"],
            to_node_id=raw.get("to_node_id"),
            outcome=raw["outcome"],
            label=raw.get("label", ""),
            kind=EdgeKind(raw.get("kind", "auto")),
            conditions=conditions,
            escalation_options=raw.get("escalation_options", []),
            non_advancing=raw.get("non_advancing", False),
        )


@dataclass
class Node:
    """A node in the workflow graph."""
    node_id: str
    type: NodeType
    description: str
    task_ref: Optional[str] = None
    produces: Optional[str] = None
    requires_consent: bool = False
    requires_qa: bool = False
    gate_outcomes: List[str] = field(default_factory=list)
    terminal_outcome: Optional[str] = None
    gate_outcome: Optional[str] = None
    non_advancing: bool = False

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Node":
        """Create from raw dict."""
        return cls(
            node_id=raw["node_id"],
            type=NodeType(raw["type"]),
            description=raw.get("description", ""),
            task_ref=raw.get("task_ref"),
            produces=raw.get("produces"),
            requires_consent=raw.get("requires_consent", False),
            requires_qa=raw.get("requires_qa", False),
            gate_outcomes=raw.get("gate_outcomes", []),
            terminal_outcome=raw.get("terminal_outcome"),
            gate_outcome=raw.get("gate_outcome"),
            non_advancing=raw.get("non_advancing", False),
        )


@dataclass
class OutcomeMapping:
    """Mapping from gate outcome to terminal outcome."""
    gate_outcome: str
    terminal_outcome: str

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OutcomeMapping":
        """Create from raw dict."""
        return cls(
            gate_outcome=raw["gate_outcome"],
            terminal_outcome=raw["terminal_outcome"],
        )


@dataclass
class ThreadOwnership:
    """Thread ownership configuration per ADR-035."""
    owns_thread: bool
    thread_purpose: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ThreadOwnership":
        """Create from raw dict."""
        return cls(
            owns_thread=raw.get("owns_thread", False),
            thread_purpose=raw.get("thread_purpose"),
        )


@dataclass
class CircuitBreaker:
    """Circuit breaker configuration per ADR-037."""
    max_retries: int
    applies_to: List[str] = field(default_factory=list)
    escalation_per_adr: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "CircuitBreaker":
        """Create from raw dict."""
        return cls(
            max_retries=raw["max_retries"],
            applies_to=raw.get("applies_to", []),
            escalation_per_adr=raw.get("escalation_per_adr"),
        )


@dataclass
class StalenessHandling:
    """Staleness handling configuration per ADR-036."""
    auto_reentry: bool
    refresh_option: Optional[str] = None
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "StalenessHandling":
        """Create from raw dict."""
        return cls(
            auto_reentry=raw.get("auto_reentry", False),
            refresh_option=raw.get("refresh_option"),
            description=raw.get("description", ""),
        )


@dataclass
class DownstreamRequirements:
    """Requirements for downstream document creation per ADR-025."""
    conditions: List[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DownstreamRequirements":
        """Create from raw dict."""
        return cls(
            conditions=raw.get("conditions", []),
            description=raw.get("description", ""),
        )


@dataclass
class Governance:
    """Governance configuration for the workflow plan."""
    adr_references: List[str] = field(default_factory=list)
    circuit_breaker: Optional[CircuitBreaker] = None
    staleness_handling: Optional[StalenessHandling] = None
    downstream_requirements: Optional[DownstreamRequirements] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Governance":
        """Create from raw dict."""
        circuit_breaker = None
        if "circuit_breaker" in raw:
            circuit_breaker = CircuitBreaker.from_dict(raw["circuit_breaker"])

        staleness_handling = None
        if "staleness_handling" in raw:
            staleness_handling = StalenessHandling.from_dict(raw["staleness_handling"])

        downstream_requirements = None
        if "downstream_requirements" in raw:
            downstream_requirements = DownstreamRequirements.from_dict(
                raw["downstream_requirements"]
            )

        return cls(
            adr_references=raw.get("adr_references", []),
            circuit_breaker=circuit_breaker,
            staleness_handling=staleness_handling,
            downstream_requirements=downstream_requirements,
        )


@dataclass
class WorkflowPlan:
    """A complete Document Interaction Workflow Plan (ADR-039).

    This represents a graph-based workflow for a single document type.
    """
    workflow_id: str
    version: str
    name: str
    description: str
    scope_type: str  # "document" per ADR-039
    document_type: str
    entry_node_ids: List[str]
    nodes: List[Node]
    edges: List[Edge]
    outcome_mapping: List[OutcomeMapping]
    thread_ownership: ThreadOwnership
    governance: Governance
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Computed indexes for efficient lookup
    _nodes_by_id: Dict[str, Node] = field(default_factory=dict, repr=False)
    _edges_by_from: Dict[str, List[Edge]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Build indexes after initialization."""
        self._build_indexes()

    def _build_indexes(self):
        """Build lookup indexes for nodes and edges."""
        self._nodes_by_id = {node.node_id: node for node in self.nodes}
        self._edges_by_from = {}
        for edge in self.edges:
            if edge.from_node_id not in self._edges_by_from:
                self._edges_by_from[edge.from_node_id] = []
            self._edges_by_from[edge.from_node_id].append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes_by_id.get(node_id)

    def get_edges_from(self, node_id: str) -> List[Edge]:
        """Get all edges originating from a node."""
        return self._edges_by_from.get(node_id, [])

    def get_entry_node(self) -> Optional[Node]:
        """Get the primary entry node (first in list)."""
        if self.entry_node_ids:
            return self.get_node(self.entry_node_ids[0])
        return None

    def get_end_nodes(self) -> List[Node]:
        """Get all end nodes."""
        return [n for n in self.nodes if n.type == NodeType.END]

    def map_gate_to_terminal(self, gate_outcome: str) -> Optional[str]:
        """Map gate outcome to terminal outcome.

        This is a pure function per invariants - no LLMs, no heuristics.
        """
        for mapping in self.outcome_mapping:
            if mapping.gate_outcome == gate_outcome:
                return mapping.terminal_outcome
        return None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "WorkflowPlan":
        """Create from raw dict."""
        nodes = [Node.from_dict(n) for n in raw.get("nodes", [])]
        edges = [Edge.from_dict(e) for e in raw.get("edges", [])]

        outcome_mapping = [
            OutcomeMapping.from_dict(m)
            for m in raw.get("outcome_mapping", {}).get("mappings", [])
        ]

        thread_ownership = ThreadOwnership.from_dict(
            raw.get("thread_ownership", {})
        )

        governance = Governance.from_dict(raw.get("governance", {}))

        return cls(
            workflow_id=raw["workflow_id"],
            version=raw.get("version", "1.0.0"),
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            scope_type=raw.get("scope_type", "document"),
            document_type=raw.get("document_type", ""),
            entry_node_ids=raw.get("entry_node_ids", []),
            nodes=nodes,
            edges=edges,
            outcome_mapping=outcome_mapping,
            thread_ownership=thread_ownership,
            governance=governance,
            metadata=raw.get("metadata", {}),
        )
