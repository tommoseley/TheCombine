"""Data classes for validation input and output contracts.

Per WS-PGC-VALIDATION-001 Phase 1.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


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
