"""Constraint drift validator for document workflow (Layer 1 - Mechanical).

Validates generated artifacts against bound constraints (pgc_invariants)
to detect constraint drift per ADR-042.

Layer 1 QA Check IDs (Mechanical):
- QA-PGC-001 (ERROR): Artifact must not contradict resolved clarifications
- QA-PGC-003 (WARNING): Bound constraints must be stated or implied in artifact
- QA-PGC-004 (WARNING): Bound constraints should be traceable in known_constraints

Layer 2 QA Check (Semantic - handled by qa.py._run_semantic_qa):
- QA-PGC-002: Resolved clarifications must not appear as open decisions
  (Requires LLM-based semantic understanding to distinguish follow-up vs reopening)

Per ADR-042, WS-ADR-042-001, and WS-SEMANTIC-QA-001.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.domain.workflow.validation.validation_result import (
    DriftViolation,
    DriftValidationResult,
)

logger = logging.getLogger(__name__)

# Patterns that indicate contradiction
CONTRADICTION_PATTERNS = [
    r"(instead of|rather than|not .+? but)",
    r"(alternative(ly)?|could also|might consider)",
    r"(override|bypass|ignore)",
]


class ConstraintDriftValidator:
    """Validates artifacts against bound constraints from PGC (Layer 1 - Mechanical).

    This validator runs as part of QA to detect when generated artifacts
    drift from user-provided binding constraints using mechanical checks.

    Layer 1 drift detection includes:
    - Direct contradiction of bound values (QA-PGC-001)
    - Silently omitting bound constraints (QA-PGC-003)
    - Missing traceability in known_constraints (QA-PGC-004)

    Note: QA-PGC-002 (reopened decisions) requires semantic understanding
    and is handled by Layer 2 semantic QA in qa.py._run_semantic_qa().
    """

    def validate(
        self,
        artifact: Dict[str, Any],
        invariants: List[Dict[str, Any]],
    ) -> DriftValidationResult:
        """Validate artifact against bound constraints.

        Args:
            artifact: The generated artifact as a parsed dict
            invariants: List of merged clarification objects where binding=true

        Returns:
            DriftValidationResult with pass/fail and all violations
        """
        violations: List[DriftViolation] = []

        if not invariants:
            logger.debug("ADR-042: No invariants to validate against")
            return DriftValidationResult(passed=True, violations=[])

        logger.info(f"ADR-042: Validating artifact against {len(invariants)} binding invariants")

        # Serialize artifact for text search
        artifact_text = json.dumps(artifact, indent=2).lower()

        # Extract known_constraints for traceability check
        known_constraints = self._extract_constraints(artifact)

        for invariant in invariants:
            # QA-PGC-001: Check for contradictions (mechanical)
            contradiction = self._check_contradiction(
                artifact=artifact,
                artifact_text=artifact_text,
                invariant=invariant,
            )
            if contradiction:
                violations.append(contradiction)

            # QA-PGC-002: HANDLED BY LAYER 2 SEMANTIC QA
            # Keyword matching cannot distinguish:
            # - "How many family members?" (valid follow-up)
            # - "Should we target classroom instead of family?" (reopening)
            # See qa.py._run_semantic_qa() and WS-SEMANTIC-QA-001

            # QA-PGC-003: Check constraint is stated (mechanical)
            omission = self._check_constraint_stated(
                artifact_text=artifact_text,
                invariant=invariant,
            )
            if omission:
                violations.append(omission)

            # QA-PGC-004: Check traceability in known_constraints (mechanical)
            traceability = self._check_traceability(
                known_constraints=known_constraints,
                invariant=invariant,
            )
            if traceability:
                violations.append(traceability)

        # Determine pass/fail (errors fail, warnings OK)
        errors = [v for v in violations if v.severity == "ERROR"]
        passed = len(errors) == 0

        logger.info(
            f"ADR-042: Drift validation {'PASSED' if passed else 'FAILED'}: "
            f"{len(errors)} errors, {len(violations) - len(errors)} warnings"
        )

        return DriftValidationResult(passed=passed, violations=violations)

    def _check_contradiction(
        self,
        artifact: Dict[str, Any],
        artifact_text: str,
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-001: Check if artifact contradicts a bound constraint."""
        clarification_id = invariant.get("id", "UNKNOWN")
        constraint_kind = invariant.get("constraint_kind", "selection")
        user_answer = invariant.get("user_answer")
        user_answer_label = invariant.get("user_answer_label", "")
        choices = invariant.get("choices", [])

        # For exclusions, check if excluded value appears positively
        if constraint_kind == "exclusion":
            excluded_label = user_answer_label.lower() if user_answer_label else str(user_answer).lower()
            for pattern in CONTRADICTION_PATTERNS:
                matches = re.findall(f"{excluded_label}.*{pattern}|{pattern}.*{excluded_label}", artifact_text)
                if matches:
                    return DriftViolation(
                        check_id="QA-PGC-001",
                        severity="ERROR",
                        clarification_id=clarification_id,
                        message=f"Artifact suggests '{excluded_label}' which was explicitly excluded",
                        remediation="Remove references to the excluded option and respect the user's exclusion.",
                    )

            if f"recommend {excluded_label}" in artifact_text or f"use {excluded_label}" in artifact_text:
                return DriftViolation(
                    check_id="QA-PGC-001",
                    severity="ERROR",
                    clarification_id=clarification_id,
                    message=f"Artifact recommends '{excluded_label}' which was explicitly excluded",
                    remediation="Remove the recommendation and respect the user's exclusion.",
                )

        # For selections, check if a different choice is stated as the selection
        if constraint_kind == "selection" and choices:
            selected_value = str(user_answer).lower() if user_answer else ""
            selected_label = user_answer_label.lower() if user_answer_label else selected_value
            other_options = []
            for choice in choices:
                choice_id = (choice.get("id") or choice.get("value", "")).lower()
                choice_label = choice.get("label", "").lower()
                if choice_id != selected_value and choice_label != selected_label:
                    other_options.extend([choice_id, choice_label])

            for other in other_options:
                if not other:
                    continue
                if f"platform is {other}" in artifact_text or f"using {other}" in artifact_text:
                    return DriftViolation(
                        check_id="QA-PGC-001",
                        severity="ERROR",
                        clarification_id=clarification_id,
                        message=f"Artifact states '{other}' but user selected '{selected_label}'",
                        remediation=f"Correct the artifact to reflect the user's selection: {selected_label}",
                    )

        return None

    def _check_constraint_stated(
        self,
        artifact_text: str,
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-003: Check if bound constraint is stated or implied in artifact."""
        clarification_id = invariant.get("id", "UNKNOWN")
        user_answer = invariant.get("user_answer")
        user_answer_label = invariant.get("user_answer_label") or str(user_answer or "")

        if not user_answer_label:
            return None

        if user_answer_label.lower() in artifact_text:
            return None
        if user_answer and str(user_answer).lower() in artifact_text:
            return None

        return DriftViolation(
            check_id="QA-PGC-003",
            severity="WARNING",
            clarification_id=clarification_id,
            message=f"Bound constraint '{clarification_id}' ({user_answer_label}) not stated in artifact",
            remediation="Reference this constraint in known_constraints or summary.",
        )

    def _check_traceability(
        self,
        known_constraints: List[Dict[str, Any]],
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-004: Check if bound constraint is traceable in known_constraints."""
        clarification_id = invariant.get("id", "UNKNOWN")
        user_answer_label = invariant.get("user_answer_label") or str(invariant.get("user_answer", ""))

        if not known_constraints:
            return DriftViolation(
                check_id="QA-PGC-004",
                severity="WARNING",
                clarification_id=clarification_id,
                message=f"Bound constraint '{clarification_id}' not traceable - no known_constraints section",
                remediation="Add a known_constraints section with bound constraints.",
            )

        constraints_text = json.dumps(known_constraints).lower()
        answer_lower = user_answer_label.lower() if user_answer_label else ""

        if clarification_id.lower() in constraints_text or answer_lower in constraints_text:
            return None

        return DriftViolation(
            check_id="QA-PGC-004",
            severity="WARNING",
            clarification_id=clarification_id,
            message=f"Bound constraint '{clarification_id}' ({user_answer_label}) not found in known_constraints",
            remediation="Add this constraint to known_constraints for traceability.",
        )

    def _extract_constraints(self, artifact: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract known_constraints section from artifact."""
        constraints = artifact.get("known_constraints", [])
        if isinstance(constraints, list):
            return constraints
        if isinstance(constraints, dict):
            return [{"id": k, **v} if isinstance(v, dict) else {"id": k, "text": str(v)}
                    for k, v in constraints.items()]
        return []
