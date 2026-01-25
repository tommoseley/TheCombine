"""Code-based validation for document workflow.

This module provides deterministic validation that runs BEFORE LLM-based QA
to catch promotion violations, internal contradictions, and constraint drift.

Per WS-PGC-VALIDATION-001 Phase 1 and ADR-042.
"""

from app.domain.workflow.validation.validation_result import (
    # Promotion validation types (WS-PGC-VALIDATION-001)
    PromotionValidationInput,
    PromotionValidationResult,
    ValidationIssue,
    # Drift validation types (ADR-042)
    DriftViolation,
    DriftValidationResult,
)
from app.domain.workflow.validation.promotion_validator import PromotionValidator
from app.domain.workflow.validation.constraint_drift_validator import ConstraintDriftValidator

__all__ = [
    # Promotion validation
    "PromotionValidator",
    "PromotionValidationInput",
    "PromotionValidationResult",
    "ValidationIssue",
    # Drift validation (ADR-042)
    "ConstraintDriftValidator",
    "DriftViolation",
    "DriftValidationResult",
]
