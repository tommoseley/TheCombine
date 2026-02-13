"""Edge router for Document Interaction Workflow Plans (ADR-039).

Evaluates edges and conditions to determine the next node in workflow execution.

INVARIANTS (WS-INTAKE-ENGINE-001):
- Router performs control, not work
- Edge selection is deterministic given (current_node, outcome, state)
- Conditions are evaluated in order; first matching edge wins
- No LLMs, no heuristics in routing decisions
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.domain.workflow.plan_models import (
    ConditionOperator,
    Edge,
    EdgeCondition,
    WorkflowPlan,
)
from app.domain.workflow.document_workflow_state import DocumentWorkflowState

logger = logging.getLogger(__name__)


class EdgeRoutingError(Exception):
    """Error during edge routing."""
    pass


class EdgeRouter:
    """Routes workflow execution by evaluating edges and conditions.

    The EdgeRouter is the ONLY component that makes routing decisions.
    Node executors return outcomes; EdgeRouter decides what happens next.

    INVARIANT: Routing is deterministic. Given the same inputs, the same
    edge is always selected.
    """

    def __init__(self, plan: WorkflowPlan):
        """Initialize router with a workflow plan.

        Args:
            plan: The WorkflowPlan containing nodes and edges
        """
        self.plan = plan

    def get_next_node(
        self,
        current_node_id: str,
        outcome: str,
        state: DocumentWorkflowState,
    ) -> Tuple[Optional[str], Optional[Edge]]:
        """Determine the next node based on outcome and state.

        This is the main routing function. It:
        1. Finds all edges from current_node_id
        2. Filters by outcome match
        3. Evaluates conditions
        4. Returns the first matching edge's target

        Args:
            current_node_id: The node that just executed
            outcome: The execution outcome
            state: Current workflow state (for condition evaluation)

        Returns:
            Tuple of (next_node_id, matched_edge)
            - next_node_id is None for non-advancing edges or no match
            - matched_edge is None if no edge matched

        Raises:
            EdgeRoutingError: If routing fails unexpectedly
        """
        edges = self.plan.get_edges_from(current_node_id)

        if not edges:
            logger.warning(f"No edges from node {current_node_id}")
            return None, None

        # Find matching edges
        matching_edges = self._find_matching_edges(edges, outcome, state)

        if not matching_edges:
            logger.warning(
                f"No matching edge from {current_node_id} with outcome '{outcome}'"
            )
            return None, None

        # First matching edge wins (deterministic)
        selected_edge = matching_edges[0]

        logger.info(
            f"Routing: {current_node_id} --[{outcome}]--> "
            f"{selected_edge.to_node_id or '(non-advancing)'}"
        )

        return selected_edge.to_node_id, selected_edge

    def _find_matching_edges(
        self,
        edges: List[Edge],
        outcome: str,
        state: DocumentWorkflowState,
    ) -> List[Edge]:
        """Find all edges that match the outcome and pass conditions.

        Args:
            edges: Candidate edges from current node
            outcome: The execution outcome
            state: Current workflow state

        Returns:
            List of matching edges (may be empty)
        """
        matching = []

        for edge in edges:
            # Check outcome match
            if edge.outcome != outcome:
                continue

            # Check conditions (all must pass)
            if edge.conditions:
                if not self._evaluate_conditions(edge.conditions, state):
                    continue

            matching.append(edge)

        return matching

    def _evaluate_conditions(
        self,
        conditions: List[EdgeCondition],
        state: DocumentWorkflowState,
    ) -> bool:
        """Evaluate edge conditions against state.

        All conditions must pass (AND logic).

        Args:
            conditions: List of conditions to evaluate
            state: Current workflow state

        Returns:
            True if ALL conditions pass
        """
        for condition in conditions:
            if not self._evaluate_condition(condition, state):
                return False
        return True

    def _evaluate_condition(
        self,
        condition: EdgeCondition,
        state: DocumentWorkflowState,
    ) -> bool:
        """Evaluate a single condition.

        Args:
            condition: The condition to evaluate
            state: Current workflow state

        Returns:
            True if condition passes
        """
        # Get the value to compare
        actual_value = self._get_condition_value(condition.type, state)

        # Compare based on operator
        return self._compare(actual_value, condition.operator, condition.value)

    def _get_condition_value(
        self,
        condition_type: str,
        state: DocumentWorkflowState,
    ) -> Any:
        """Get the actual value for a condition type.

        Args:
            condition_type: Type of condition (e.g., "retry_count")
            state: Current workflow state

        Returns:
            The value to compare
        """
        if condition_type == "retry_count":
            # Get retry count for the generating node (not current node)
            # Per WS-INTAKE-ENGINE-001: retry counter scoped to generating_node_id
            # When QA fails, retry is incremented for the generating node, so
            # edge conditions should check that same counter
            node_id = getattr(state, 'generating_node_id', None) or state.current_node_id
            return state.get_retry_count(node_id)

        if condition_type == "status":
            return state.status.value

        if condition_type == "escalation_active":
            return state.escalation_active

        # Default: try to get from state's execution history or metadata
        logger.warning(f"Unknown condition type: {condition_type}")
        return None

    def _compare(
        self,
        actual: Any,
        operator: ConditionOperator,
        expected: Any,
    ) -> bool:
        """Compare actual value against expected using operator.

        Args:
            actual: The actual value
            operator: Comparison operator
            expected: Expected value

        Returns:
            True if comparison passes
        """
        if actual is None:
            return False

        try:
            if operator == ConditionOperator.EQ:
                return actual == expected
            elif operator == ConditionOperator.NE:
                return actual != expected
            elif operator == ConditionOperator.LT:
                return actual < expected
            elif operator == ConditionOperator.LTE:
                return actual <= expected
            elif operator == ConditionOperator.GT:
                return actual > expected
            elif operator == ConditionOperator.GTE:
                return actual >= expected
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except TypeError:
            logger.warning(f"Type error comparing {actual} {operator} {expected}")
            return False

    def get_escalation_options(self, edge: Edge) -> List[str]:
        """Get escalation options from an edge (for circuit breaker).

        Args:
            edge: The edge (typically a circuit-breaker edge)

        Returns:
            List of escalation option strings
        """
        return edge.escalation_options

    def is_terminal_node(self, node_id: str) -> bool:
        """Check if a node is a terminal (end) node.

        Args:
            node_id: The node ID to check

        Returns:
            True if node is an end node
        """
        node = self.plan.get_node(node_id)
        if not node:
            return False
        return node.type.value == "end"

    def get_terminal_outcome(self, node_id: str) -> Optional[str]:
        """Get the terminal outcome for an end node.

        Args:
            node_id: The end node ID

        Returns:
            The terminal outcome or None if not an end node
        """
        node = self.plan.get_node(node_id)
        if not node or node.type.value != "end":
            return None
        return node.terminal_outcome

    def get_gate_outcome(self, node_id: str) -> Optional[str]:
        """Get the gate outcome for an end node.

        Args:
            node_id: The end node ID

        Returns:
            The gate outcome or None if not defined
        """
        node = self.plan.get_node(node_id)
        if not node or node.type.value != "end":
            return None
        return node.gate_outcome

    def validate_outcome(
        self,
        current_node_id: str,
        outcome: str,
    ) -> bool:
        """Validate that an outcome has at least one matching edge.

        Args:
            current_node_id: The current node ID
            outcome: The outcome to validate

        Returns:
            True if there's at least one edge with this outcome
        """
        edges = self.plan.get_edges_from(current_node_id)
        return any(e.outcome == outcome for e in edges)
