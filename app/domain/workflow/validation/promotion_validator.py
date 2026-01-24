"""Promotion validator for document workflow.

Runs deterministic validation BEFORE LLM-based QA to catch:
- Promotion violations (should/could answers becoming constraints)
- Internal contradictions (same concept in constraints and assumptions)
- Policy conformance (prohibited terms in unknowns)
- Grounding issues (guardrails not traceable to input)

Per WS-PGC-VALIDATION-001 Phase 1.
"""

import logging
from typing import Any, Dict, List

from app.domain.workflow.validation.validation_result import (
    PromotionValidationInput,
    PromotionValidationResult,
    ValidationIssue,
)
from app.domain.workflow.validation.rules import (
    check_promotion_validity,
    check_internal_contradictions,
    check_policy_conformance,
    check_grounding,
)

logger = logging.getLogger(__name__)


class PromotionValidator:
    """Validates documents for promotion violations and contradictions.

    This validator runs before LLM-based QA to catch issues that can be
    detected deterministically:

    1. Promotion Validity (WARNING): Constraints must trace to must-priority
       answers or explicit intake statements, not should/could answers.

    2. Internal Contradiction (ERROR): Same concept cannot appear in both
       constraints and assumptions.

    3. Policy Conformance (WARNING): Unknowns/stakeholder_questions must not
       contain prohibited terms (budget, authority).

    4. Grounding (WARNING): MVP guardrails must trace to explicit input.

    Errors cause validation to fail. Warnings are informational.
    """

    def validate(self, input_data: PromotionValidationInput) -> PromotionValidationResult:
        """Run all validation checks.

        Args:
            input_data: The validation input with PGC data and document

        Returns:
            PromotionValidationResult with passed status and all issues
        """
        all_issues: List[ValidationIssue] = []
        document = input_data.generated_document

        # Extract document sections
        constraints = self._extract_list(document, "known_constraints")
        assumptions = self._extract_list(document, "assumptions")
        guardrails = self._extract_list(document, "mvp_guardrails")

        logger.info(
            f"Running promotion validation: {len(constraints)} constraints, "
            f"{len(assumptions)} assumptions, {len(guardrails)} guardrails, "
            f"{len(input_data.pgc_questions)} PGC questions"
        )

        # Rule 1: Promotion Validity
        promotion_issues = check_promotion_validity(
            constraints=constraints,
            pgc_questions=input_data.pgc_questions,
            pgc_answers=input_data.pgc_answers,
            intake=input_data.intake,
        )
        all_issues.extend(promotion_issues)
        if promotion_issues:
            logger.info(f"Promotion check: {len(promotion_issues)} issues")

        # Rule 2: Internal Contradictions
        contradiction_issues = check_internal_contradictions(
            constraints=constraints,
            assumptions=assumptions,
        )
        all_issues.extend(contradiction_issues)
        if contradiction_issues:
            logger.warning(f"Contradiction check: {len(contradiction_issues)} errors")

        # Rule 3: Policy Conformance
        policy_issues = check_policy_conformance(document)
        all_issues.extend(policy_issues)
        if policy_issues:
            logger.info(f"Policy check: {len(policy_issues)} issues")

        # Rule 4: Grounding
        grounding_issues = check_grounding(
            guardrails=guardrails,
            pgc_questions=input_data.pgc_questions,
            pgc_answers=input_data.pgc_answers,
            intake=input_data.intake,
        )
        all_issues.extend(grounding_issues)
        if grounding_issues:
            logger.info(f"Grounding check: {len(grounding_issues)} issues")

        # Determine pass/fail (errors fail, warnings OK)
        errors = [i for i in all_issues if i.severity == "error"]
        passed = len(errors) == 0

        logger.info(
            f"Promotion validation {'PASSED' if passed else 'FAILED'}: "
            f"{len(errors)} errors, {len(all_issues) - len(errors)} warnings"
        )

        return PromotionValidationResult(
            passed=passed,
            issues=all_issues,
        )

    def _extract_list(
        self,
        document: Dict[str, Any],
        field_name: str,
    ) -> List[Dict[str, Any]]:
        """Extract a list field from document, handling various formats.

        Args:
            document: The document dict
            field_name: Name of the field to extract

        Returns:
            List of dicts, empty list if field missing or wrong type
        """
        value = document.get(field_name)

        if value is None:
            return []

        if isinstance(value, list):
            # Ensure all items are dicts
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.append(item)
                elif isinstance(item, str):
                    result.append({"text": item})
            return result

        if isinstance(value, dict):
            # Convert dict format to list
            return [{"id": k, **v} if isinstance(v, dict) else {"id": k, "text": str(v)}
                    for k, v in value.items()]

        return []
