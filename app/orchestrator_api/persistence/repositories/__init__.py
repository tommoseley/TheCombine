"""
Repository layer for PIPELINE-175A.

Exports all repository classes for easy importing.
"""
# Existing repositories (PIPELINE-150)
from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
from app.orchestrator_api.persistence.repositories.artifact_repository import ArtifactRepository
from app.orchestrator_api.persistence.repositories.phase_transition_repository import PhaseTransitionRepository

# New repositories (PIPELINE-175A)
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import (
    PhaseConfigurationRepository,
    ValidationResult
)
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository
)

__all__ = [
    # Existing repositories
    "PipelineRepository",
    "ArtifactRepository",
    "PhaseTransitionRepository",
    # New repositories
    "RepositoryError",
    "RolePromptRepository",
    "PhaseConfigurationRepository",
    "ValidationResult",
    "PipelinePromptUsageRepository",
]