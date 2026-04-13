"""
Repair Proposal Domain Model (ADR-065).

Immutable DTO for component-scoped repair proposals.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


VALID_STATUSES = {"pending", "accepted", "rejected", "superseded"}


@dataclass
class RepairProposalDTO:
    """Domain transfer object for repair proposals."""

    id: UUID
    artifact_id: UUID
    artifact_type: str  # "TA"
    component_identifier: str  # component.name
    trigger_finding: dict[str, Any]
    proposed_payload: dict[str, Any]
    status: str  # pending | accepted | rejected | superseded
    created_at: datetime
    created_by: str
    decision_at: Optional[datetime] = None
    decision_by: Optional[str] = None

    @classmethod
    def create(
        cls,
        artifact_id: UUID,
        artifact_type: str,
        component_identifier: str,
        trigger_finding: dict[str, Any],
        proposed_payload: dict[str, Any],
        created_by: str,
    ) -> "RepairProposalDTO":
        """Factory for new pending proposals."""
        return cls(
            id=uuid4(),
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            component_identifier=component_identifier,
            trigger_finding=trigger_finding,
            proposed_payload=proposed_payload,
            status="pending",
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
