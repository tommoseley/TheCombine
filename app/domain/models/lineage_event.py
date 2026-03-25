"""
Lineage Event Model (ADR-063, WS-REWIND-006).

Records rewind and regeneration events for audit and traceability.
Answers: what changed, why, what became stale, what replaced it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class LineageEvent:
    """
    A single lineage event recording a pipeline state change.

    Immutable after creation — lineage events are audit records.
    """

    id: UUID
    project_id: UUID
    event_type: str  # 'rewind' | 'regeneration'
    rewind_to_stage: str  # PipelineStage name (e.g., 'TA')
    reason: str
    actor: str
    affected_document_ids: List[UUID]
    created_at: datetime
    # Optional: set when this rewind is followed by regeneration
    regeneration_event_id: Optional[UUID] = None

    @classmethod
    def create_rewind_event(
        cls,
        project_id: UUID,
        rewind_to_stage: str,
        reason: str,
        actor: str,
        affected_document_ids: List[UUID],
    ) -> "LineageEvent":
        """Factory for rewind events."""
        return cls(
            id=uuid4(),
            project_id=project_id,
            event_type="rewind",
            rewind_to_stage=rewind_to_stage,
            reason=reason,
            actor=actor,
            affected_document_ids=affected_document_ids,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def create_regeneration_event(
        cls,
        project_id: UUID,
        from_stage: str,
        reason: str,
        actor: str,
        new_document_ids: List[UUID],
    ) -> "LineageEvent":
        """Factory for regeneration events."""
        return cls(
            id=uuid4(),
            project_id=project_id,
            event_type="regeneration",
            rewind_to_stage=from_stage,
            reason=reason,
            actor=actor,
            affected_document_ids=new_document_ids,
            created_at=datetime.now(timezone.utc),
        )
