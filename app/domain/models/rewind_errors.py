"""
Rewind Error Model (ADR-063, WS-REWIND-015).

Standardized error responses for rewind-related failures.
Used by progression guard, QA rejection, and stabilization rejection.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class RewindBlockedError:
    """
    Structured error for rewind-related failures.

    Returned when an operation is blocked because artifacts are stale
    or the pipeline requires regeneration.
    """

    error_code: str  # e.g., "STALE_ARTIFACT", "UPSTREAM_REWIND_REQUIRED"
    document_id: UUID
    document_type: str
    current_status: str
    message: str  # human-readable
    required_action: str  # e.g., "Regenerate from TA stage before proceeding"
    rewind_stage: Optional[str] = None  # stage that caused invalidation


# Standard error codes
STALE_ARTIFACT = "STALE_ARTIFACT"
SUPERSEDED_ARTIFACT = "SUPERSEDED_ARTIFACT"
STALE_INPUT = "STALE_INPUT"
STALE_CHILD = "STALE_CHILD"


def stale_artifact_error(
    document_id: UUID,
    document_type: str,
    rewind_stage: Optional[str] = None,
) -> RewindBlockedError:
    """Create a standard stale artifact error."""
    return RewindBlockedError(
        error_code=STALE_ARTIFACT,
        document_id=document_id,
        document_type=document_type,
        current_status="stale",
        message=f"Document {document_type} is stale due to upstream rewind",
        required_action=(
            f"Regenerate from {rewind_stage} stage before proceeding"
            if rewind_stage
            else "Regenerate upstream artifacts before proceeding"
        ),
        rewind_stage=rewind_stage,
    )


def stale_input_error(
    document_id: UUID,
    document_type: str,
    consuming_operation: str,
) -> RewindBlockedError:
    """Create error for stale input to an operation."""
    return RewindBlockedError(
        error_code=STALE_INPUT,
        document_id=document_id,
        document_type=document_type,
        current_status="stale",
        message=(
            f"Cannot {consuming_operation}: input {document_type} "
            f"is stale due to upstream rewind"
        ),
        required_action="Regenerate the stale input artifact before proceeding",
    )
