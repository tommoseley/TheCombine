"""Data classes for validation input and output contracts.

Per WS-PGC-VALIDATION-001 Phase 1.
Extended for ADR-042 constraint drift validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


# =============================================================================
# Shared Drift Validation Types (ADR-042)
# =============================================================================

@dataclass
class DriftViolation:
    """A constraint drift violation per ADR-042.

    Attributes:
        check_id: Check identifier (e.g., QA-PGC-001)
        severity: ERROR fails validation, WARNING is informational
        clarification_id: ID of the violated clarification
        message: Human-readable description
        remediation: Optional guidance for fixing the issue
    """
    check_id: str
    severity: Literal["ERROR", "WARNING"]
    clarification_id: str
    message: str
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "check_id": self.check_id,
            "severity": self.severity,
            "clarification_id": self.clarification_id,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass
class DriftValidationResult:
    """Result of constraint drift validation per ADR-042.

    Attributes:
        passed: True if no ERROR-level violations
        violations: All violations found during validation
    """
    passed: bool
    violations: List[DriftViolation] = field(default_factory=list)

    @property
    def errors(self) -> List[DriftViolation]:
        """Get only ERROR-severity violations."""
        return [v for v in self.violations if v.severity == "ERROR"]

    @property
    def warnings(self) -> List[DriftViolation]:
        """Get only WARNING-severity violations."""
        return [v for v in self.violations if v.severity == "WARNING"]

    @property
    def error_summary(self) -> str:
        """Get a summary of all errors for logging/display."""
        if not self.errors:
            return ""
        return "; ".join(f"{e.check_id}: {e.message}" for e in self.errors)


# =============================================================================
# Promotion Validation Types (WS-PGC-VALIDATION-001)
# =============================================================================


@dataclass
class PromotionValidationInput:
    """Input contract for promotion validation.

    Attributes:
        pgc_questions: Questions from PGC node output
        pgc_answers: User's answers keyed by question ID
        generated_document: The document to validate
        intake: Optional concierge intake for grounding check
    """
    pgc_questions: List[Dict[str, Any]]
    pgc_answers: Dict[str, Any]
    generated_document: Dict[str, Any]
    intake: Optional[Dict[str, Any]] = None


@dataclass
class ValidationIssue:
    """A single validation issue.

    Attributes:
        severity: "error" fails validation, "warning" is informational
        check_type: Category of the check that found this issue
        section: Document section where issue was found
        field_id: Optional field/constraint ID
        message: Human-readable description
        evidence: Source data that triggered the issue
    """
    severity: Literal["error", "warning"]
    check_type: Literal["promotion", "contradiction", "policy", "grounding"]
    section: str
    message: str
    evidence: Dict[str, Any]
    field_id: Optional[str] = None


@dataclass
class PromotionValidationResult:
    """Result of promotion validation.

    Attributes:
        passed: True if no errors (warnings are OK)
        issues: All issues found during validation
    """
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-severity issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-severity issues."""
        return [i for i in self.issues if i.severity == "warning"]
