"""Constraint drift validator for document workflow.

Validates generated artifacts against bound constraints (pgc_invariants)
to detect constraint drift per ADR-042.

QA Check IDs:
- QA-PGC-001 (ERROR): Artifact must not contradict resolved clarifications
- QA-PGC-002 (ERROR): Resolved clarifications must not appear as open decisions
- QA-PGC-003 (WARNING): Bound constraints must be stated or implied in artifact
- QA-PGC-004 (WARNING): Bound constraints should be traceable in known_constraints

Per ADR-042 and WS-ADR-042-001 Phase 5.
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

# Patterns that indicate reopening a decision
REOPEN_PATTERNS = [
    r"(needs? to be decided|still needs? clarification)",
    r"(decision required|requires? decision)",
    r"(to be determined|tbd)",
    r"(open question|unresolved)",
    r"(consider (whether|if)|should we)",
    r"(option[s]? include|alternatives? (are|include))",
    r"(pending (decision|input))",
]

# Patterns that indicate contradiction
CONTRADICTION_PATTERNS = [
    r"(instead of|rather than|not .+? but)",
    r"(alternative(ly)?|could also|might consider)",
    r"(override|bypass|ignore)",
]


class ConstraintDriftValidator:
    """Validates artifacts against bound constraints from PGC.

    This validator runs as part of QA to detect when generated artifacts
    drift from user-provided binding constraints.

    Drift includes:
    - Direct contradiction of bound values
    - Reopening resolved decisions as open questions
    - Silently omitting bound constraints
    - Missing traceability in known_constraints
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
            clarification_id = invariant.get("id", "UNKNOWN")

            # QA-PGC-001: Check for contradictions
            contradiction = self._check_contradiction(
                artifact=artifact,
                artifact_text=artifact_text,
                invariant=invariant,
            )
            if contradiction:
                violations.append(contradiction)

            # QA-PGC-002: Check for reopened decisions
            reopened = self._check_reopened_decision(
                artifact=artifact,
                artifact_text=artifact_text,
                invariant=invariant,
            )
            if reopened:
                violations.append(reopened)

            # QA-PGC-003: Check constraint is stated
            omission = self._check_constraint_stated(
                artifact_text=artifact_text,
                invariant=invariant,
            )
            if omission:
                violations.append(omission)

            # QA-PGC-004: Check traceability in known_constraints
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
        """QA-PGC-001: Check if artifact contradicts a bound constraint.

        Contradiction detected when:
        - Exclusion constraint: Excluded value is mentioned positively
        - Selection constraint: Different value is mentioned as the choice

        Args:
            artifact: The generated artifact
            artifact_text: Lowercased JSON string of artifact
            invariant: The bound constraint to check

        Returns:
            DriftViolation if contradiction found, None otherwise
        """
        clarification_id = invariant.get("id", "UNKNOWN")
        constraint_kind = invariant.get("constraint_kind", "selection")
        user_answer = invariant.get("user_answer")
        user_answer_label = invariant.get("user_answer_label", "")
        choices = invariant.get("choices", [])

        # For exclusions, check if excluded value appears positively
        if constraint_kind == "exclusion":
            # The user's answer is what they excluded
            excluded_label = user_answer_label.lower() if user_answer_label else str(user_answer).lower()

            # Check if artifact recommends/suggests the excluded option
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

            # Also check if excluded option appears as a recommendation
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

            # Build list of non-selected options
            other_options = []
            for choice in choices:
                choice_id = (choice.get("id") or choice.get("value", "")).lower()
                choice_label = choice.get("label", "").lower()
                if choice_id != selected_value and choice_label != selected_label:
                    other_options.extend([choice_id, choice_label])

            # Check if artifact states a different option as the choice
            for other in other_options:
                if not other:
                    continue
                # Look for patterns like "platform is mobile" or "using mobile"
                if f"platform is {other}" in artifact_text or f"using {other}" in artifact_text:
                    return DriftViolation(
                        check_id="QA-PGC-001",
                        severity="ERROR",
                        clarification_id=clarification_id,
                        message=f"Artifact states '{other}' but user selected '{selected_label}'",
                        remediation=f"Correct the artifact to reflect the user's selection: {selected_label}",
                    )

        return None

    def _check_reopened_decision(
        self,
        artifact: Dict[str, Any],
        artifact_text: str,
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-002: Check if resolved clarification appears as open decision.

        Detected when:
        - Question topic appears with decision-pending language
        - Artifact presents alternatives for an already-decided topic

        Args:
            artifact: The generated artifact
            artifact_text: Lowercased JSON string of artifact
            invariant: The bound constraint to check

        Returns:
            DriftViolation if reopened, None otherwise
        """
        clarification_id = invariant.get("id", "UNKNOWN")
        question_text = invariant.get("text", "").lower()
        user_answer_label = invariant.get("user_answer_label", "")

        # Extract key topic from question (simplified - focus on noun phrases)
        # E.g., "What platform should the app target?" -> "platform"
        topic_words = self._extract_topic_words(question_text)

        if not topic_words:
            return None

        # Check for reopen patterns near topic words
        for topic in topic_words:
            for pattern in REOPEN_PATTERNS:
                # Look for pattern within 100 chars of topic mention
                topic_pattern = f"{topic}.{{0,100}}{pattern}|{pattern}.{{0,100}}{topic}"
                if re.search(topic_pattern, artifact_text, re.IGNORECASE):
                    return DriftViolation(
                        check_id="QA-PGC-002",
                        severity="ERROR",
                        clarification_id=clarification_id,
                        message=f"Artifact reopens '{topic}' as an open decision, but it was already resolved to '{user_answer_label}'",
                        remediation=f"Remove decision language around '{topic}'. The user already decided: {user_answer_label}",
                    )

        # Check for options/alternatives presentation for this topic
        for topic in topic_words:
            if f"{topic} options" in artifact_text or f"choose.*{topic}" in artifact_text:
                return DriftViolation(
                    check_id="QA-PGC-002",
                    severity="ERROR",
                    clarification_id=clarification_id,
                    message=f"Artifact presents options for '{topic}', but this was already decided",
                    remediation=f"Remove options presentation. User selected: {user_answer_label}",
                )

        return None

    def _check_constraint_stated(
        self,
        artifact_text: str,
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-003: Check if bound constraint is stated or implied in artifact.

        Warning if constraint value/label not mentioned anywhere.

        Args:
            artifact_text: Lowercased JSON string of artifact
            invariant: The bound constraint to check

        Returns:
            DriftViolation (WARNING) if omitted, None otherwise
        """
        clarification_id = invariant.get("id", "UNKNOWN")
        user_answer = invariant.get("user_answer")
        user_answer_label = invariant.get("user_answer_label") or str(user_answer or "")

        if not user_answer_label:
            return None

        # Check if answer label appears in artifact
        if user_answer_label.lower() in artifact_text:
            return None

        # Also check the raw answer value
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
        """QA-PGC-004: Check if bound constraint is traceable in known_constraints.

        Warning if constraint not found in the known_constraints section.

        Args:
            known_constraints: List of constraint objects from artifact
            invariant: The bound constraint to check

        Returns:
            DriftViolation (WARNING) if not traceable, None otherwise
        """
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

        # Check if any constraint mentions this clarification or its value
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

    def _extract_constraints(
        self,
        artifact: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract known_constraints section from artifact.

        Args:
            artifact: The generated artifact

        Returns:
            List of constraint objects
        """
        constraints = artifact.get("known_constraints", [])

        if isinstance(constraints, list):
            return constraints
        if isinstance(constraints, dict):
            # Convert dict format to list
            return [{"id": k, **v} if isinstance(v, dict) else {"id": k, "text": str(v)}
                    for k, v in constraints.items()]
        return []

    def _extract_topic_words(
        self,
        question_text: str,
    ) -> List[str]:
        """Extract key topic words from a question for matching.

        Simple extraction focusing on nouns that likely represent the topic.
        Very conservative to avoid false positives from common words.

        Args:
            question_text: The question text

        Returns:
            List of topic words
        """
        # Remove common question words, verbs, prepositions, and punctuation
        # This list is intentionally broad to avoid false positives
        # Words that commonly appear in questions but aren't specific topics
        stopwords = {
            # Question words
            "what", "which", "how", "should", "would", "will", "can", "does",
            "when", "where", "why", "who", "whom", "whose",
            # Articles and determiners
            "the", "a", "an", "this", "that", "these", "those",
            "any", "some", "all", "most", "other", "such", "each", "every",
            # Prepositions
            "to", "for", "of", "in", "on", "at", "by", "with", "without",
            "from", "into", "onto", "about", "over", "under", "through",
            "between", "among", "before", "after", "during", "within",
            # Common verbs
            "is", "are", "be", "been", "being", "was", "were",
            "have", "has", "had", "having", "do", "does", "did", "doing",
            "work", "works", "working", "support", "supports", "supporting",
            "need", "needs", "needed", "needing", "require", "requires",
            "want", "wants", "use", "uses", "using", "used",
            "get", "gets", "make", "makes", "take", "takes",
            "provide", "provides", "allow", "allows", "enable", "enables",
            "include", "includes", "contain", "contains",
            "track", "tracks", "tracking", "tracked",
            "store", "stores", "storing", "stored", "storage",
            "align", "aligns", "aligned", "alignment",
            "target", "targets", "targeting", "targeted",
            "intend", "intends", "intended", "intention",
            "select", "selects", "selected", "selection",
            "deploy", "deploys", "deployed", "deployment",
            # Modals
            "could", "might", "may", "must", "shall",
            # Pronouns
            "you", "your", "we", "our", "they", "their", "it", "its",
            # Generic tech terms (too common to be meaningful topics)
            "app", "application", "system", "software", "feature", "data",
            "user", "users", "client", "server", "service",
            "interface", "interfaces",
            "test", "tests", "testing", "tested",
            "result", "results", "resulting",
            "context", "contexts", "contextual",
            "standard", "standards", "standardized",
            "specific", "specifically", "specification",
            "option", "options", "optional",
            "question", "questions", "questioning",
            "answer", "answers", "answered",
            "primary", "primarily", "secondary",
            "device", "devices", "local", "locally",
            "operating", "operated", "operation",
            # Domain terms common in educational/business apps
            "educational", "education", "learning", "teaching",
            "deployment", "deployed", "environment",
            "requirement", "requirements", "required",
            "align", "aligned", "alignment",
            # Other common words
            "also", "well", "just", "only", "even", "still", "already",
            "yes", "no", "not", "and", "or", "but", "if", "then",
            "able", "like", "way", "thing", "things",
            "there", "here", "being", "based", "following",
            "certain", "particular", "general", "overall",
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-z]+\b', question_text.lower())
        topics = [w for w in words if w not in stopwords and len(w) > 3]

        # Return unique topics (first occurrences)
        seen = set()
        result = []
        for w in topics:
            if w not in seen:
                seen.add(w)
                result.append(w)

        return result[:3]  # Limit to top 3 topic words
