"""
Common Models Package

Contains Pydantic models for all roles in The Combine.
"""

from .epic_models import (
    EpicSchema,
    EpicSummary,
    EpicScope,
    PMPerspective,
    PMPerspectives,
    Story,
)

from .architecture_models import (
    ArchitectureDocument,
    ArchitectureSummary,
    ArchitectureContext,
    Component,
    DataEntity,
    DataField,
    Interface,
    Endpoint,
    Workflow,
    WorkflowStep,
    QualityAttribute,
    RiskItem,
    ArchitectureStory,
)

from .ba_models import (
    BAStory,
    BAStorySet,
    BAStorySetDict,
    BAStoryDict,
)

__all__ = [
    # Epic models
    "EpicSchema",
    "EpicSummary",
    "EpicScope",
    "PMPerspective",
    "PMPerspectives",
    "Story",
    # Architecture models
    "ArchitectureDocument",
    "ArchitectureSummary",
    "ArchitectureContext",
    "Component",
    "DataEntity",
    "DataField",
    "Interface",
    "Endpoint",
    "Workflow",
    "WorkflowStep",
    "QualityAttribute",
    "RiskItem",
    "ArchitectureStory",
    # BA models
    "BAStory",
    "BAStorySet",
    "BAStorySetDict",
    "BAStoryDict",
]