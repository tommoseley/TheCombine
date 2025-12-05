"""
Repository for PhaseConfiguration CRUD operations with graph validation.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import IntegrityError
from app.orchestrator_api.models.phase_configuration import PhaseConfiguration
from app.orchestrator_api.models.role_prompt import RolePrompt
from app.orchestrator_api.persistence.database import SessionLocal
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


@dataclass
class ValidationResult:
    """Result of configuration graph validation."""
    is_valid: bool
    errors: List[str]


class PhaseConfigurationRepository:
    """Repository for PhaseConfiguration CRUD operations."""
    
    @staticmethod
    def get_by_phase(phase_name: str) -> Optional[PhaseConfiguration]:
        """
        Get configuration for specific phase.
        
        Args:
            phase_name: Phase identifier
            
        Returns:
            PhaseConfiguration or None if not found
        """
        session = SessionLocal()
        try:
            config = session.query(PhaseConfiguration).filter(
                PhaseConfiguration.phase_name == phase_name
            ).first()
            return config
        finally:
            session.close()
    
    @staticmethod
    def get_all_active() -> List[PhaseConfiguration]:
        """
        Get all active phase configurations.
        
        Returns:
            List of active PhaseConfiguration objects ordered by phase_name
        """
        session = SessionLocal()
        try:
            configs = session.query(PhaseConfiguration).filter(
                PhaseConfiguration.is_active == True
            ).order_by(PhaseConfiguration.phase_name).all()
            return configs
        finally:
            session.close()
    
    @staticmethod
    def create(
        phase_name: str,
        role_name: str,
        artifact_type: str,
        next_phase: Optional[str] = None,
        config: Optional[dict] = None
    ) -> PhaseConfiguration:
        """
        Create new phase configuration.
        
        Basic field validation only. Use validate_configuration_graph()
        after creating all configs to check references.
        
        Args:
            phase_name: Phase identifier (pm_phase, arch_phase, etc.)
            role_name: Role that executes this phase
            artifact_type: Expected artifact output (epic, arch_notes, etc.)
            next_phase: Next phase in sequence (null = terminal phase)
            config: Phase-specific configuration (JSON)
            
        Returns:
            Created PhaseConfiguration
            
        Raises:
            ValueError: If required fields missing or validation fails
            RepositoryError: If database operation fails
        """
        # Validate required fields
        if not phase_name or not phase_name.strip():
            raise ValueError("phase_name is required and cannot be empty")
        if not role_name or not role_name.strip():
            raise ValueError("role_name is required and cannot be empty")
        if not artifact_type or not artifact_type.strip():
            raise ValueError("artifact_type is required and cannot be empty")
        
        # Validate config is dict or None
        if config is not None and not isinstance(config, dict):
            raise ValueError("config must be dict or None")
        
        session = SessionLocal()
        try:
            phase_config = PhaseConfiguration(
                id=f"pc_{uuid.uuid4().hex[:16]}",
                phase_name=phase_name,
                role_name=role_name,
                artifact_type=artifact_type,
                next_phase=next_phase,
                is_active=True,
                config=config,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            session.add(phase_config)
            session.commit()
            session.refresh(phase_config)
            return phase_config
            
        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Database constraint violation (duplicate phase_name?): {e}")
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to create phase configuration: {e}")
        finally:
            session.close()
    
    @staticmethod
    def update_next_phase(phase_name: str, next_phase: Optional[str]) -> PhaseConfiguration:
        """
        Update next_phase for a configuration.
        
        Args:
            phase_name: Phase to update
            next_phase: New next phase (null for terminal)
            
        Returns:
            Updated PhaseConfiguration
            
        Raises:
            ValueError: If phase not found
            RepositoryError: If database operation fails
        """
        session = SessionLocal()
        try:
            config = session.query(PhaseConfiguration).filter(
                PhaseConfiguration.phase_name == phase_name
            ).first()
            
            if not config:
                raise ValueError(f"Phase configuration not found: {phase_name}")
            
            config.next_phase = next_phase
            config.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(config)
            return config
            
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to update next_phase: {e}")
        finally:
            session.close()
    
    @staticmethod
    def validate_configuration_graph() -> ValidationResult:
        """
        Validate entire configuration graph for:
        1. All role_names exist in role_prompts
        2. All next_phases exist in phase_configurations (or null)
        3. No circular references (max 20 hops)
        
        Returns:
            ValidationResult with is_valid and error list
        """
        session = SessionLocal()
        try:
            errors = []
            
            # Load all active configs and role prompts
            configs = session.query(PhaseConfiguration).filter(
                PhaseConfiguration.is_active == True
            ).all()
            
            role_prompts = session.query(RolePrompt).filter(
                RolePrompt.is_active == True
            ).all()
            
            phase_names = {cfg.phase_name for cfg in configs}
            role_names = {rp.role_name for rp in role_prompts}
            
            # Check 1: All role_names exist
            for cfg in configs:
                if cfg.role_name not in role_names:
                    available_roles = sorted(list(role_names))
                    errors.append(
                        f"Phase '{cfg.phase_name}' references non-existent role '{cfg.role_name}'. "
                        f"Available roles: {available_roles}"
                    )
            
            # Check 2: All next_phases exist (or null)
            for cfg in configs:
                if cfg.next_phase and cfg.next_phase not in phase_names:
                    available_phases = sorted(list(phase_names))
                    errors.append(
                        f"Phase '{cfg.phase_name}' references non-existent next_phase '{cfg.next_phase}'. "
                        f"Available phases: {available_phases}"
                    )
            
            # Check 3: No circular references
            config_map = {cfg.phase_name: cfg for cfg in configs}
            
            for start_config in configs:
                visited = set()
                current = start_config.phase_name
                hops = 0
                path = []
                
                while current and hops < 20:
                    if current in visited:
                        cycle_path = " → ".join(path) + f" → {current}"
                        errors.append(
                            f"Circular reference detected starting at '{start_config.phase_name}': {cycle_path}"
                        )
                        break
                    
                    visited.add(current)
                    path.append(current)
                    current_cfg = config_map.get(current)
                    current = current_cfg.next_phase if current_cfg else None
                    hops += 1
                
                if hops >= 20:
                    errors.append(
                        f"Phase chain starting at '{start_config.phase_name}' exceeds maximum length (20 hops)"
                    )
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors
            )
            
        finally:
            session.close()