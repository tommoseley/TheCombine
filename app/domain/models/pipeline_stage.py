"""
Canonical Pipeline Stage Model (ADR-063).

Defines the authoritative stage ordering for The Combine pipeline.
Used by rewind, invalidation, and regeneration logic.

PGC is cross-cutting and operates WITHIN stages, not between them.
PGC is NOT a rewind target.
"""

from enum import Enum
from typing import List


class PipelineStage(Enum):
    """
    Authoritative pipeline stages in execution order.

    The integer value encodes ordering: lower values are upstream,
    higher values are downstream. Rewinding to stage N invalidates
    all stages with value >= N.
    """

    CI = (0, "concierge_intake", "Concierge Intake")
    PD = (1, "project_discovery", "Product Discovery")
    TA = (2, "technical_architecture", "Technical Architecture")
    IP = (3, "implementation_plan", "Implementation Plan")
    WP = (4, "work_package", "Work Package")
    WS = (5, "work_statement", "Work Statement")

    def __init__(self, order: int, doc_type_id: str, display_name: str):
        self._order = order
        self._doc_type_id = doc_type_id
        self._display_name = display_name

    @property
    def order(self) -> int:
        """Numeric ordering. Lower = more upstream."""
        return self._order

    @property
    def doc_type_id(self) -> str:
        """The document type ID associated with this stage."""
        return self._doc_type_id

    @property
    def display_name(self) -> str:
        """Human-readable stage name."""
        return self._display_name

    def is_downstream_of(self, other: "PipelineStage") -> bool:
        """True if this stage is strictly downstream of the other."""
        return self._order > other._order

    def is_upstream_of(self, other: "PipelineStage") -> bool:
        """True if this stage is strictly upstream of the other."""
        return self._order < other._order

    def downstream_stages(self) -> List["PipelineStage"]:
        """All stages strictly downstream of this one."""
        return [s for s in PipelineStage if s._order > self._order]

    def stages_at_and_after(self) -> List["PipelineStage"]:
        """This stage plus all downstream stages (the invalidation set)."""
        return [s for s in PipelineStage if s._order >= self._order]

    @classmethod
    def from_doc_type_id(cls, doc_type_id: str) -> "PipelineStage":
        """Look up stage by document type ID. Raises ValueError if not found."""
        for stage in cls:
            if stage._doc_type_id == doc_type_id:
                return stage
        raise ValueError(
            f"No pipeline stage for doc_type_id '{doc_type_id}'. "
            f"Valid types: {[s._doc_type_id for s in cls]}"
        )

    @classmethod
    def all_stages_ordered(cls) -> List["PipelineStage"]:
        """All stages in pipeline order."""
        return sorted(cls, key=lambda s: s._order)
