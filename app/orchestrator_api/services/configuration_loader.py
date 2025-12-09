"""
Configuration Loader - Load and validate phase configurations.

This module loads phase configurations from the database and validates
they are active before use.

Author: D-2 (Mid-Level Developer)
Epic: PIPELINE-175B
"""

from dataclasses import dataclass
from typing import Optional
import logging
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import (
    PhaseConfigurationRepository
)

logger = logging.getLogger(__name__)


@dataclass
class PhaseConfig:
    """Phase configuration data transfer object."""
    phase_name: str
    role_name: str
    artifact_type: str
    next_phase: Optional[str]
    is_active: bool


class ConfigurationError(Exception):
    """Phase configuration not found or invalid."""
    
    def __init__(self, message: str, phase_name: str = None, pipeline_id: str = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            phase_name: Phase that failed (optional)
            pipeline_id: Pipeline context (optional)
        """
        self.message = message
        self.phase_name = phase_name
        self.pipeline_id = pipeline_id
        
        # Format message with context if available
        if phase_name and pipeline_id:
            full_message = f"[{pipeline_id}:{phase_name}] {message}"
        elif phase_name:
            full_message = f"[{phase_name}] {message}"
        else:
            full_message = message
            
        super().__init__(full_message)


class ConfigurationLoader:
    """Load and validate phase configurations."""
    
    def __init__(self, repo: PhaseConfigurationRepository):
        """
        Initialize loader with repository.
        
        Args:
            repo: Phase configuration repository instance
        """
        self._repo = repo
    
    def load_config(self, phase_name: str) -> PhaseConfig:
        """
        Load and validate phase configuration.
        
        Args:
            phase_name: Phase identifier (e.g., "pm_phase")
            
        Returns:
            PhaseConfig with validated data
            
        Raises:
            ConfigurationError: If config not found or not active
        """
        try:
            config_model = self._repo.get_by_phase_name(phase_name)
            
            if config_model is None:
                logger.error(f"Phase config not found: {phase_name}")
                raise ConfigurationError(
                    f"Phase configuration not found: {phase_name}",
                    phase_name=phase_name
                )
            
            if not config_model.is_active:
                logger.error(f"Phase config not active: {phase_name}")
                raise ConfigurationError(
                    f"Phase configuration not active: {phase_name}",
                    phase_name=phase_name
                )
            
            # Convert ORM model to dataclass
            config = PhaseConfig(
                phase_name=config_model.phase_name,
                role_name=config_model.role_name,
                artifact_type=config_model.artifact_type,
                next_phase=config_model.next_phase,
                is_active=config_model.is_active
            )
            
            logger.debug(f"Loaded config for {phase_name}: role={config.role_name}")
            return config
            
        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading config for {phase_name}: {e}")
            raise ConfigurationError(
                f"Failed to load configuration: {str(e)}",
                phase_name=phase_name
            )