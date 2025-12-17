"""
Mentor implementations for The Combine.

Each mentor extends StreamingMentor and handles a specific role + task
in the software development pipeline.
"""

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    ProgressStep,
    PromptServiceProtocol,
    ArtifactServiceProtocol,
    IdGeneratorFunc,
    validate_required_fields,
    validate_non_empty_array,
    validate_with_json_schema,
    DEFAULT_PROGRESS_STEPS
)

from app.domain.mentors.pm_mentor import PMMentor
from app.domain.mentors.architect_mentor import ArchitectMentor
from app.domain.mentors.preliminary_architect_mentor import PreliminaryArchitectMentor
from app.domain.mentors.ba_mentor import BAMentor
from app.domain.mentors.developer_mentor import DeveloperMentor

from app.domain.mentors.requests import (
    PMRequest,
    ArchitectRequest,
    PreliminaryArchitectRequest,
    BARequest,
    DeveloperRequest
)

__all__ = [
    # Base class and utilities
    "StreamingMentor",
    "ProgressStep",
    "PromptServiceProtocol",
    "ArtifactServiceProtocol",
    "IdGeneratorFunc",
    "validate_required_fields",
    "validate_non_empty_array",
    "validate_with_json_schema",
    "DEFAULT_PROGRESS_STEPS",
    
    # Mentor implementations
    "PMMentor",
    "ArchitectMentor",
    "PreliminaryArchitectMentor",
    "BAMentor",
    "DeveloperMentor",
    
    # Request models
    "PMRequest",
    "ArchitectRequest",
    "PreliminaryArchitectRequest",
    "BARequest",
    "DeveloperRequest",
]