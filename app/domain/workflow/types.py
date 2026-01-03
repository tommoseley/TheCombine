"""Validation result types for workflow validation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ValidationErrorCode(Enum):
    """Error codes for workflow validation failures."""
    
    # Schema errors
    SCHEMA_INVALID = "SCHEMA_INVALID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Type reference errors
    UNKNOWN_DOCUMENT_TYPE = "UNKNOWN_DOCUMENT_TYPE"
    UNKNOWN_ENTITY_TYPE = "UNKNOWN_ENTITY_TYPE"
    UNKNOWN_SCOPE = "UNKNOWN_SCOPE"
    
    # Ownership errors
    OWNERSHIP_CYCLE = "OWNERSHIP_CYCLE"
    
    # Scope errors
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    INVALID_SCOPE_HIERARCHY = "INVALID_SCOPE_HIERARCHY"
    
    # Reference errors
    INVALID_REFERENCE = "INVALID_REFERENCE"
    MISSING_ITERATION_SOURCE = "MISSING_ITERATION_SOURCE"
    FORBIDDEN_SIBLING_REFERENCE = "FORBIDDEN_SIBLING_REFERENCE"
    FORBIDDEN_DESCENDANT_REFERENCE = "FORBIDDEN_DESCENDANT_REFERENCE"
    FORBIDDEN_CROSS_BRANCH_REFERENCE = "FORBIDDEN_CROSS_BRANCH_REFERENCE"
    
    # Prompt reference errors
    INVALID_PROMPT_FORMAT = "INVALID_PROMPT_FORMAT"
    PROMPT_NOT_IN_MANIFEST = "PROMPT_NOT_IN_MANIFEST"


@dataclass
class ValidationError:
    """A single validation error with code, message, and location."""
    
    code: ValidationErrorCode
    message: str
    path: str = ""  # JSON path to error location (e.g., "steps[2].task_prompt")
    
    def __str__(self) -> str:
        if self.path:
            return f"[{self.code.value}] {self.path}: {self.message}"
        return f"[{self.code.value}] {self.message}"


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    
    def __bool__(self) -> bool:
        return self.valid
    
    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(valid=True, errors=[])
    
    @classmethod
    def failure(cls, errors: List[ValidationError]) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(valid=False, errors=errors)
