"""Validator for Document Interaction Workflow Plans (ADR-039).

Validates both schema structure and semantic integrity of workflow plans.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set


class PlanValidationErrorCode(str, Enum):
    """Error codes for plan validation failures."""
    # Schema errors
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    INVALID_ENUM_VALUE = "INVALID_ENUM_VALUE"

    # Graph integrity errors
    EDGE_TARGET_NOT_FOUND = "EDGE_TARGET_NOT_FOUND"
    EDGE_SOURCE_NOT_FOUND = "EDGE_SOURCE_NOT_FOUND"
    ENTRY_NODE_NOT_FOUND = "ENTRY_NODE_NOT_FOUND"
    NO_OUTBOUND_EDGES = "NO_OUTBOUND_EDGES"
    ORPHAN_NODE = "ORPHAN_NODE"

    # Outcome mapping errors
    MISSING_OUTCOME_MAPPING = "MISSING_OUTCOME_MAPPING"
    INCOMPLETE_OUTCOME_MAPPING = "INCOMPLETE_OUTCOME_MAPPING"

    # Governance errors
    INVALID_CIRCUIT_BREAKER = "INVALID_CIRCUIT_BREAKER"
    INVALID_GOVERNANCE = "INVALID_GOVERNANCE"


@dataclass
class PlanValidationError:
    """A single validation error."""
    code: PlanValidationErrorCode
    message: str
    path: str = ""  # JSON path to the error location
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanValidationResult:
    """Result of plan validation."""
    valid: bool
    errors: List[PlanValidationError] = field(default_factory=list)
    warnings: List[PlanValidationError] = field(default_factory=list)


class PlanValidator:
    """Validates workflow plan structure and semantics.

    Validation Rules:
    1. All edge targets exist as nodes (or null for non-advancing)
    2. All edge sources exist as nodes
    3. Entry nodes exist
    4. Non-end nodes have outbound edges
    5. Outcome mapping covers all gate outcomes from gate nodes
    6. No orphan nodes (unreachable from entry)
    """

    VALID_NODE_TYPES = {"concierge", "intake_gate", "task", "qa", "gate", "end", "pgc"}
    VALID_EDGE_KINDS = {"auto", "user_choice"}
    VALID_CONDITION_OPERATORS = {"eq", "ne", "lt", "lte", "gt", "gte"}
    REQUIRED_TOP_LEVEL_FIELDS = {
        "workflow_id", "nodes", "edges", "entry_node_ids"
    }

    def validate(self, raw: Dict[str, Any]) -> PlanValidationResult:
        """Validate a workflow plan.

        Args:
            raw: Raw plan dict (e.g., from JSON)

        Returns:
            PlanValidationResult with validation status and any errors
        """
        errors: List[PlanValidationError] = []
        warnings: List[PlanValidationError] = []

        # Phase 1: Schema validation
        self._validate_schema(raw, errors)

        # If schema is invalid, stop here
        if errors:
            return PlanValidationResult(valid=False, errors=errors)

        # Phase 2: Graph integrity
        self._validate_graph_integrity(raw, errors, warnings)

        # Phase 3: Outcome mapping
        self._validate_outcome_mapping(raw, errors, warnings)

        # Phase 4: Governance
        self._validate_governance(raw, errors, warnings)

        return PlanValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_schema(
        self,
        raw: Dict[str, Any],
        errors: List[PlanValidationError],
    ) -> None:
        """Validate basic schema structure."""
        # Check required top-level fields
        for field_name in self.REQUIRED_TOP_LEVEL_FIELDS:
            if field_name not in raw:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message=f"Missing required field: {field_name}",
                    path=f"$.{field_name}",
                ))

        # Validate nodes array
        if "nodes" in raw:
            if not isinstance(raw["nodes"], list):
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_FIELD_TYPE,
                    message="'nodes' must be an array",
                    path="$.nodes",
                ))
            else:
                for i, node in enumerate(raw["nodes"]):
                    self._validate_node_schema(node, i, errors)

        # Validate edges array
        if "edges" in raw:
            if not isinstance(raw["edges"], list):
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_FIELD_TYPE,
                    message="'edges' must be an array",
                    path="$.edges",
                ))
            else:
                for i, edge in enumerate(raw["edges"]):
                    self._validate_edge_schema(edge, i, errors)

        # Validate entry_node_ids
        if "entry_node_ids" in raw:
            if not isinstance(raw["entry_node_ids"], list):
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_FIELD_TYPE,
                    message="'entry_node_ids' must be an array",
                    path="$.entry_node_ids",
                ))
            elif len(raw["entry_node_ids"]) == 0:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message="'entry_node_ids' must have at least one entry",
                    path="$.entry_node_ids",
                ))

    def _validate_node_schema(
        self,
        node: Dict[str, Any],
        index: int,
        errors: List[PlanValidationError],
    ) -> None:
        """Validate individual node schema."""
        path = f"$.nodes[{index}]"

        # Required fields
        if "node_id" not in node:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message="Node missing required field: node_id",
                path=path,
            ))

        if "type" not in node:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message="Node missing required field: type",
                path=path,
            ))
        elif node["type"] not in self.VALID_NODE_TYPES:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.INVALID_ENUM_VALUE,
                message=f"Invalid node type: {node['type']}. "
                        f"Valid types: {self.VALID_NODE_TYPES}",
                path=f"{path}.type",
                context={"value": node["type"]},
            ))

        # End nodes must have terminal_outcome
        if node.get("type") == "end" and "terminal_outcome" not in node:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                message="End node missing required field: terminal_outcome",
                path=path,
            ))

    def _validate_edge_schema(
        self,
        edge: Dict[str, Any],
        index: int,
        errors: List[PlanValidationError],
    ) -> None:
        """Validate individual edge schema."""
        path = f"$.edges[{index}]"

        # Required fields
        for field_name in ["edge_id", "from_node_id", "outcome"]:
            if field_name not in edge:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message=f"Edge missing required field: {field_name}",
                    path=path,
                ))

        # Validate kind if present
        if "kind" in edge and edge["kind"] not in self.VALID_EDGE_KINDS:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.INVALID_ENUM_VALUE,
                message=f"Invalid edge kind: {edge['kind']}. "
                        f"Valid kinds: {self.VALID_EDGE_KINDS}",
                path=f"{path}.kind",
            ))

        # Validate conditions if present
        if "conditions" in edge:
            for j, condition in enumerate(edge["conditions"]):
                self._validate_condition_schema(condition, index, j, errors)

    def _validate_condition_schema(
        self,
        condition: Dict[str, Any],
        edge_index: int,
        condition_index: int,
        errors: List[PlanValidationError],
    ) -> None:
        """Validate edge condition schema."""
        path = f"$.edges[{edge_index}].conditions[{condition_index}]"

        for field_name in ["type", "operator", "value"]:
            if field_name not in condition:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message=f"Condition missing required field: {field_name}",
                    path=path,
                ))

        if "operator" in condition:
            if condition["operator"] not in self.VALID_CONDITION_OPERATORS:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_ENUM_VALUE,
                    message=f"Invalid condition operator: {condition['operator']}",
                    path=f"{path}.operator",
                ))

    def _validate_graph_integrity(
        self,
        raw: Dict[str, Any],
        errors: List[PlanValidationError],
        warnings: List[PlanValidationError],
    ) -> None:
        """Validate graph structure integrity."""
        # Build node index
        node_ids: Set[str] = {node["node_id"] for node in raw.get("nodes", [])}
        end_node_ids: Set[str] = {
            node["node_id"]
            for node in raw.get("nodes", [])
            if node.get("type") == "end"
        }

        # Track nodes with outbound edges
        nodes_with_outbound: Set[str] = set()

        # Validate edges
        for i, edge in enumerate(raw.get("edges", [])):
            from_id = edge.get("from_node_id")
            to_id = edge.get("to_node_id")

            # Validate source exists
            if from_id and from_id not in node_ids:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.EDGE_SOURCE_NOT_FOUND,
                    message=f"Edge '{edge.get('edge_id')}' references "
                            f"non-existent source node: {from_id}",
                    path=f"$.edges[{i}].from_node_id",
                    context={"node_id": from_id},
                ))
            else:
                nodes_with_outbound.add(from_id)

            # Validate target exists (null is valid for non-advancing)
            if to_id is not None and to_id not in node_ids:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.EDGE_TARGET_NOT_FOUND,
                    message=f"Edge '{edge.get('edge_id')}' references "
                            f"non-existent target node: {to_id}",
                    path=f"$.edges[{i}].to_node_id",
                    context={"node_id": to_id},
                ))

        # Validate entry nodes exist
        for entry_id in raw.get("entry_node_ids", []):
            if entry_id not in node_ids:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.ENTRY_NODE_NOT_FOUND,
                    message=f"Entry node not found: {entry_id}",
                    path="$.entry_node_ids",
                    context={"node_id": entry_id},
                ))

        # Check non-end nodes have outbound edges
        for node in raw.get("nodes", []):
            node_id = node["node_id"]
            if node.get("type") != "end" and node_id not in nodes_with_outbound:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.NO_OUTBOUND_EDGES,
                    message=f"Non-end node '{node_id}' has no outbound edges",
                    path="$.nodes",
                    context={"node_id": node_id},
                ))

        # Check for orphan nodes (unreachable from entry)
        reachable = self._find_reachable_nodes(raw)
        for node in raw.get("nodes", []):
            node_id = node["node_id"]
            if node_id not in reachable:
                warnings.append(PlanValidationError(
                    code=PlanValidationErrorCode.ORPHAN_NODE,
                    message=f"Node '{node_id}' is unreachable from entry nodes",
                    path="$.nodes",
                    context={"node_id": node_id},
                ))

    def _find_reachable_nodes(self, raw: Dict[str, Any]) -> Set[str]:
        """Find all nodes reachable from entry nodes via BFS."""
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {}
        for edge in raw.get("edges", []):
            from_id = edge.get("from_node_id")
            to_id = edge.get("to_node_id")
            if from_id not in adjacency:
                adjacency[from_id] = []
            if to_id is not None:
                adjacency[from_id].append(to_id)

        # BFS from entry nodes
        reachable: Set[str] = set()
        queue = list(raw.get("entry_node_ids", []))
        reachable.update(queue)

        while queue:
            current = queue.pop(0)
            for neighbor in adjacency.get(current, []):
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        return reachable

    def _validate_outcome_mapping(
        self,
        raw: Dict[str, Any],
        errors: List[PlanValidationError],
        warnings: List[PlanValidationError],
    ) -> None:
        """Validate outcome mapping completeness."""
        # Collect all gate outcomes from gate nodes
        gate_outcomes: Set[str] = set()
        for node in raw.get("nodes", []):
            if node.get("type") == "gate":
                outcomes = node.get("gate_outcomes", [])
                gate_outcomes.update(outcomes)

        # Check outcome_mapping exists and covers all gate outcomes
        outcome_mapping = raw.get("outcome_mapping", {})
        if not outcome_mapping:
            if gate_outcomes:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.MISSING_OUTCOME_MAPPING,
                    message="Plan has gate nodes but no outcome_mapping",
                    path="$.outcome_mapping",
                ))
            return

        mappings = outcome_mapping.get("mappings", [])
        mapped_outcomes = {m["gate_outcome"] for m in mappings}

        # Check for unmapped gate outcomes
        unmapped = gate_outcomes - mapped_outcomes
        if unmapped:
            errors.append(PlanValidationError(
                code=PlanValidationErrorCode.INCOMPLETE_OUTCOME_MAPPING,
                message=f"Gate outcomes not mapped: {unmapped}",
                path="$.outcome_mapping.mappings",
                context={"unmapped": list(unmapped)},
            ))

    def _validate_governance(
        self,
        raw: Dict[str, Any],
        errors: List[PlanValidationError],
        warnings: List[PlanValidationError],
    ) -> None:
        """Validate governance configuration."""
        governance = raw.get("governance", {})

        # Validate circuit breaker if present
        circuit_breaker = governance.get("circuit_breaker")
        if circuit_breaker:
            if "max_retries" not in circuit_breaker:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_CIRCUIT_BREAKER,
                    message="circuit_breaker missing required field: max_retries",
                    path="$.governance.circuit_breaker",
                ))
            elif not isinstance(circuit_breaker["max_retries"], int):
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_CIRCUIT_BREAKER,
                    message="circuit_breaker.max_retries must be an integer",
                    path="$.governance.circuit_breaker.max_retries",
                ))
            elif circuit_breaker["max_retries"] < 1:
                errors.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_CIRCUIT_BREAKER,
                    message="circuit_breaker.max_retries must be >= 1",
                    path="$.governance.circuit_breaker.max_retries",
                ))

        # Validate staleness_handling if present
        staleness = governance.get("staleness_handling")
        if staleness:
            if "auto_reentry" not in staleness:
                warnings.append(PlanValidationError(
                    code=PlanValidationErrorCode.INVALID_GOVERNANCE,
                    message="staleness_handling should specify auto_reentry",
                    path="$.governance.staleness_handling",
                ))
