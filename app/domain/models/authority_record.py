"""
Authority Record Domain Model (ADR-064).

Durable, project-scoped authority records that persist across pipeline
rewinds and regenerations. PGC answers are project authority, not
execution state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass
class AuthorityRecordDTO:
    """
    Domain representation of an authority record.

    No SQLAlchemy dependency — used in services and tests.
    """

    project_id: UUID
    authority_type: str  # "pgc_answer" (MVP); future: "bound_constraint", "user_override"
    stage: str  # PipelineStage name (e.g., "PD", "IP", "TA")
    key: str  # question_id, constraint_id, or override key
    value: Any  # the user's answer or constraint value (stored as JSONB)
    source_execution_id: UUID  # which execution produced this
    lineage_path_id: UUID  # identifies accepted lineage path (MVP: execution_id surrogate)
    actor: str  # "user" for PGC answers

    id: UUID = field(default_factory=uuid4)
    status: str = "current"  # "current" | "superseded" | "historical"
    superseded_by: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
