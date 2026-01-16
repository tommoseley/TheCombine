"""Outcome mapper for Document Interaction Workflow Plans (ADR-039).

Maps gate outcomes (governance vocabulary) to terminal outcomes (execution vocabulary).

INVARIANTS (WS-INTAKE-ENGINE-001):

OutcomeMapper is a PURE FUNCTION:
- Given (gate_outcome) → returns fixed terminal_outcome
- No LLM calls
- No heuristics
- No "best guess" inference
- No external state consultation

The mapping table is defined in the plan and is the single source of truth.
"""

from typing import Dict, List, Optional

from app.domain.workflow.plan_models import OutcomeMapping, WorkflowPlan


class OutcomeMapperError(Exception):
    """Error during outcome mapping."""
    pass


class OutcomeMapper:
    """Maps gate outcomes to terminal outcomes.

    This is a pure, deterministic function. Given a gate outcome,
    it returns the corresponding terminal outcome as defined in the
    workflow plan's outcome_mapping section.

    INVARIANT: This mapper makes NO decisions. It performs lookup only.
    """

    def __init__(self, mappings: List[OutcomeMapping]):
        """Initialize with mappings from workflow plan.

        Args:
            mappings: List of OutcomeMapping from plan
        """
        # Build lookup dict for O(1) access
        self._mapping: Dict[str, str] = {
            m.gate_outcome: m.terminal_outcome
            for m in mappings
        }

    @classmethod
    def from_plan(cls, plan: WorkflowPlan) -> "OutcomeMapper":
        """Create mapper from a workflow plan.

        Args:
            plan: The WorkflowPlan containing outcome_mapping

        Returns:
            OutcomeMapper instance
        """
        return cls(plan.outcome_mapping)

    def map(self, gate_outcome: str) -> str:
        """Map a gate outcome to terminal outcome.

        This is a PURE FUNCTION. No side effects, no external calls.

        Args:
            gate_outcome: The gate outcome (e.g., "qualified", "not_ready")

        Returns:
            The terminal outcome (e.g., "stabilized", "blocked")

        Raises:
            OutcomeMapperError: If gate_outcome is not in mapping
        """
        if gate_outcome not in self._mapping:
            raise OutcomeMapperError(
                f"Unknown gate outcome: '{gate_outcome}'. "
                f"Valid outcomes: {list(self._mapping.keys())}"
            )
        return self._mapping[gate_outcome]

    def map_optional(self, gate_outcome: str) -> Optional[str]:
        """Map a gate outcome to terminal outcome, returning None if not found.

        This is a PURE FUNCTION. No side effects, no external calls.

        Args:
            gate_outcome: The gate outcome

        Returns:
            The terminal outcome or None if not found
        """
        return self._mapping.get(gate_outcome)

    def is_valid_gate_outcome(self, gate_outcome: str) -> bool:
        """Check if a gate outcome is valid.

        Args:
            gate_outcome: The gate outcome to check

        Returns:
            True if valid (has mapping)
        """
        return gate_outcome in self._mapping

    def list_gate_outcomes(self) -> List[str]:
        """List all valid gate outcomes.

        Returns:
            List of gate outcome strings
        """
        return list(self._mapping.keys())

    def list_terminal_outcomes(self) -> List[str]:
        """List all unique terminal outcomes.

        Returns:
            List of unique terminal outcome strings
        """
        return list(set(self._mapping.values()))

    def get_mapping_table(self) -> Dict[str, str]:
        """Get the full mapping table (read-only copy).

        Returns:
            Dict mapping gate outcomes to terminal outcomes
        """
        return dict(self._mapping)
