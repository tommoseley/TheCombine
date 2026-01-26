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

# Patterns that indicate reopening a decision (open framing)
OPEN_FRAMING_PATTERNS = [
    r"needs? to be decided",
    r"still needs? clarification",
    r"decision required",
    r"requires? decision",
    r"to be determined",
    r"\btbd\b",
    r"open question",
    r"unresolved",
    r"should we",
    r"do we need",
    r"options? include",
    r"alternatives? (are|include)",
    r"pending (decision|input)",
    r"choose between",
    r"either[/\s]or",
    r"consider (whether|if)",
    r"evaluate options",
    r"which .+ (should|to use)",
]

# Patterns that indicate finality (decision is settled)
FINALITY_PATTERNS = [
    r"(is|are|will be) (selected|chosen|decided)",
    r"(has been|was) (selected|chosen|decided)",
    r"out of scope",
    r"not in scope",
    r"excluded",
    r"will (use|be)",
    r"must (use|be)",
    r"(selected|chosen):?",
    r"decision:? ",
    r"resolved to",
    r"confirmed:?",
    r"final:?",
    r"not required",
    r"not needed",
]

# Patterns that indicate contradiction
CONTRADICTION_PATTERNS = [
    r"(instead of|rather than|not .+? but)",
    r"(alternative(ly)?|could also|might consider)",
    r"(override|bypass|ignore)",
]

# Legacy alias for backward compatibility
REOPEN_PATTERNS = OPEN_FRAMING_PATTERNS


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

            # QA-PGC-002: DISABLED - requires semantic understanding
            # Keyword matching can't distinguish:
            # - "How many family members?" (valid follow-up)
            # - "Should we target classroom instead of family?" (reopening)
            # TODO: Implement as LLM-based semantic check (Layer 2 QA)
            # reopened = self._check_reopened_decision(...)

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
    def _check_reopened_decision(
        self,
        artifact: Dict[str, Any],
        artifact_text: str,
        invariant: Dict[str, Any],
    ) -> Optional[DriftViolation]:
        """QA-PGC-002: Check if resolved clarification appears as open decision.

        STRUCTURAL CHECK ONLY - does not scan global text.
        
        Checks only decision-bearing sections:
        - early_decision_points[].decision_area or options
        - stakeholder_questions[] with uncertainty framing
        - unknowns[] that question the bound topic
        - recommendations_for_pm[] that propose investigating (exclusions only)
        
        PASS if topic appears elsewhere (summary, assumptions, known_constraints).
        Restatement as fact is allowed and expected.
        """
        # Get canonical tags - if none, skip tag-based validation
        canonical_tags = invariant.get("canonical_tags", [])
        if not canonical_tags:
            # No tags means this constraint isn't checkable via tags
            # It's still enforced via pinning and filtering
            return None
        
        # ALL constraints use structural checking - no global text search
        return self._check_decision_bearing_sections(artifact, invariant, canonical_tags)
    def _check_decision_bearing_sections(
        self,
        artifact: Dict[str, Any],
        invariant: Dict[str, Any],
        canonical_tags: List[str],
    ) -> Optional[DriftViolation]:
        """Check decision-bearing sections for constraint violations.
        
        STRUCTURAL + FRAMING-AWARE validation:
        - Only checks decision-bearing sections, not global text
        - Fails only if BOTH topic AND open framing are in the same item
        - Passes if topic is restated as fact elsewhere
        
        Allowed: "The app is for home use by parents." (restatement)
        Allowed: "Platform is web (selected)." (finality)
        Not allowed: "Choose platform: web/mobile/desktop." (open framing)
        """
        clarification_id = invariant.get("id", "UNKNOWN")
        user_answer_label = invariant.get("user_answer_label", "")
        normalized_text = invariant.get("normalized_text", f"{clarification_id}")
        invariant_kind = invariant.get("invariant_kind", "requirement")
        
        tags_lower = [t.lower() for t in canonical_tags]
        answer_lower = user_answer_label.lower() if user_answer_label else ""
        
        # Check early_decision_points - applies to ALL constraints
        # A decision point about a bound topic is always a violation
        decision_points = artifact.get("early_decision_points", [])
        for dp in decision_points:
            if isinstance(dp, dict):
                decision_area = dp.get("decision_area", "").lower()
                options = dp.get("options", [])
                options_text = json.dumps(options).lower() if options else ""
                
                for tag in tags_lower:
                    # Check if decision_area explicitly mentions the bound topic
                    if tag in decision_area:
                        # This is presenting the bound topic as needing a decision
                        if not self._has_finality_language(decision_area, answer_lower):
                            return DriftViolation(
                                check_id="QA-PGC-002",
                                severity="ERROR",
                                clarification_id=clarification_id,
                                message=f"early_decision_points[].decision_area reopens '{tag}' as undecided",
                                remediation=f"Remove this decision point. Already resolved: {user_answer_label}",
                            )
        
        # Check unknowns - applies to ALL constraints
        unknowns = artifact.get("unknowns", [])
        for unk in unknowns:
            if isinstance(unk, dict):
                question = unk.get("question", "").lower()
                
                for tag in tags_lower:
                    if tag in question:
                        # Check if it's questioning the bound constraint
                        if self._is_uncertainty_about_topic(question, tag) and not self._has_finality_language(question, answer_lower):
                            return DriftViolation(
                                check_id="QA-PGC-002",
                                severity="ERROR",
                                clarification_id=clarification_id,
                                message=f"unknowns[].question presents '{tag}' as uncertain, but was resolved",
                                remediation=f"Remove or rephrase. Already resolved: {user_answer_label}",
                            )
        
        # Check stakeholder_questions - for exclusions with "should we" framing
        if invariant_kind == "exclusion":
            stakeholder_questions = artifact.get("stakeholder_questions", [])
            for sq in stakeholder_questions:
                sq_text = sq.get("question", "") if isinstance(sq, dict) else str(sq)
                sq_lower = sq_text.lower()
                
                for tag in tags_lower:
                    if tag in sq_lower:
                        if self._is_reopening_question(sq_lower, tag):
                            return DriftViolation(
                                check_id="QA-PGC-002",
                                severity="ERROR",
                                clarification_id=clarification_id,
                                message=f"stakeholder_questions asks about excluded '{tag}'",
                                remediation=f"Remove. Topic explicitly excluded: {user_answer_label}",
                            )
        
        # Check recommendations_for_pm - only for exclusions proposing investigation
        if invariant_kind == "exclusion":
            recommendations = artifact.get("recommendations_for_pm", [])
            for rec in recommendations:
                rec_text = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
                rec_lower = rec_text.lower()
                
                for tag in tags_lower:
                    if tag in rec_lower:
                        if self._is_investigation_proposal(rec_lower, tag):
                            return DriftViolation(
                                check_id="QA-PGC-002",
                                severity="ERROR",
                                clarification_id=clarification_id,
                                message=f"recommendations_for_pm proposes investigating excluded '{tag}'",
                                remediation=f"Remove. Topic explicitly excluded: {user_answer_label}",
                            )
        
        return None
    
    def _is_uncertainty_about_topic(self, text: str, topic: str) -> bool:
        """Check if text expresses uncertainty about a topic."""
        uncertainty_patterns = [
            f"what.*{topic}", f"which.*{topic}", f"how.*{topic}",
            f"{topic}.*unclear", f"{topic}.*unknown", f"{topic}.*tbd",
            f"determine.*{topic}", f"decide.*{topic}", f"confirm.*{topic}",
        ]
        for pattern in uncertainty_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _has_open_framing_without_finality(
        self,
        text: str,
        topic: str,
        bound_answer: str,
    ) -> bool:
        """Check if text has open framing without finality language.
        
        Returns True only if:
        - Open framing patterns are found near the topic
        - AND no finality patterns are found
        - AND the bound answer is not mentioned
        """
        # Check for open framing patterns
        has_open_framing = False
        for pattern in OPEN_FRAMING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                has_open_framing = True
                break
        
        if not has_open_framing:
            return False
        
        # Check for finality language
        if self._has_finality_language(text, bound_answer):
            return False
        
        return True
    
    def _has_finality_language(self, text: str, bound_answer: str) -> bool:
        """Check if text contains finality language or the bound answer."""
        # Check if bound answer is mentioned
        if bound_answer and bound_answer in text:
            return True
        
        # Check for finality patterns
        for pattern in FINALITY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    def _is_reopening_question(self, question: str, topic: str) -> bool:
        """Check if a stakeholder question reopens a decision vs confirms it's out of scope."""
        reopening_patterns = [
            f"should we.*{topic}", f"do we need.*{topic}", f"consider.*{topic}",
            f"evaluate.*{topic}", f"what.*{topic}.*option", f"which.*{topic}",
        ]
        compliant_patterns = [
            f"confirm.*no.*{topic}", f"verify.*no.*{topic}", f"ensure.*no.*{topic}",
            f"document.*exclusion.*{topic}", f"{topic}.*not.*required",
            f"{topic}.*out of scope", f"no.*{topic}.*needed",
        ]
        
        for pattern in compliant_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return False
        for pattern in reopening_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True
        return False
    
    def _is_investigation_proposal(self, recommendation: str, topic: str) -> bool:
        """Check if a recommendation proposes investigating an excluded topic."""
        investigation_patterns = [
            f"investigate.*{topic}", f"explore.*{topic}", f"evaluate.*{topic}",
            f"consider.*{topic}", f"research.*{topic}", f"add.*{topic}",
            f"implement.*{topic}", f"integrate.*{topic}",
        ]
        for pattern in investigation_patterns:
            if re.search(pattern, recommendation, re.IGNORECASE):
                return True
        return False
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
    def _extract_topic_words(self, question_text: str) -> List[str]:
        """Extract key topic words from a question for matching."""
        stopwords = {
            "what", "which", "how", "should", "would", "will", "can", "does",
            "when", "where", "why", "who", "whom", "whose",
            "the", "a", "an", "this", "that", "these", "those",
            "any", "some", "all", "most", "other", "such", "each", "every",
            "to", "for", "of", "in", "on", "at", "by", "with", "without",
            "from", "into", "onto", "about", "over", "under", "through",
            "between", "among", "before", "after", "during", "within",
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
            "could", "might", "may", "must", "shall",
            "you", "your", "we", "our", "they", "their", "it", "its",
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
            "educational", "education", "learning", "teaching",
            "deployment", "deployed", "environment",
            "requirement", "requirements", "required",
            "also", "well", "just", "only", "even", "still", "already",
            "yes", "no", "not", "and", "or", "but", "if", "then",
            "able", "like", "way", "thing", "things",
            "there", "here", "being", "based", "following",
            "certain", "particular", "general", "overall",
        }

        words = re.findall(r'\b[a-z]+\b', question_text.lower())
        topics = [w for w in words if w not in stopwords and len(w) > 3]

        seen = set()
        result = []
        for w in topics:
            if w not in seen:
                seen.add(w)
                result.append(w)

        return result[:3]