"""Clarification Merger Handler.

Per WS-ADR-047-004 Phase 2: Specialized handler for merging PGC questions
with operator answers and deriving binding constraints.

This handler wraps the existing clarification_merger module logic,
making it available as a mechanical operation.
"""

import logging
from typing import Any, Dict

from app.api.services.mech_handlers.base import (
    ExecutionContext,
    MechHandler,
    MechResult,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


@register_handler
class ClarificationMergerHandler(MechHandler):
    """Handler for clarification_merger operations.

    Merges PGC questions with operator answers into clarifications
    with binding status, optionally extracting invariants.
    """

    operation_type = "clarification_merger"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the clarification merge operation.

        Args:
            config: Operation configuration with:
                - extract_invariants: bool (default True)
                - normalize_answers: bool (default True)
            context: Execution context with inputs:
                - questions: List of PGC question objects
                - answers: Dict mapping question ID to answer

        Returns:
            MechResult with output containing:
                - clarifications: List of merged clarification objects
                - invariants: List of binding invariants (if extract_invariants)
        """
        # Get inputs
        questions = context.get_input("questions")
        answers = context.get_input("answers")

        if questions is None:
            return MechResult.fail(
                error="Missing required input: questions",
                error_code="missing_input",
            )

        if answers is None:
            return MechResult.fail(
                error="Missing required input: answers",
                error_code="missing_input",
            )

        if not isinstance(questions, list):
            return MechResult.fail(
                error="Input 'questions' must be a list",
                error_code="invalid_input",
            )

        if not isinstance(answers, dict):
            return MechResult.fail(
                error="Input 'answers' must be a dict",
                error_code="invalid_input",
            )

        # Get config options
        extract_invariants = config.get("extract_invariants", True)

        try:
            # Import and use existing logic
            from app.domain.workflow.clarification_merger import (
                merge_clarifications,
                extract_invariants as extract_invariants_func,
            )

            # Merge questions with answers
            clarifications = merge_clarifications(questions, answers)

            # Build output
            output = {"clarifications": clarifications}

            # Optionally extract invariants
            if extract_invariants:
                invariants = extract_invariants_func(clarifications)
                output["invariants"] = invariants
                logger.info(
                    f"Clarification merge complete: {len(clarifications)} clarifications, "
                    f"{len(invariants)} binding invariants"
                )
            else:
                logger.info(
                    f"Clarification merge complete: {len(clarifications)} clarifications"
                )

            return MechResult.ok(output=output)

        except Exception as e:
            logger.exception(f"Clarification merge failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="execution_error",
            )
