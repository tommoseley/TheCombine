"""
Tests for PhaseConfigurationRepository.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
import pytest
from app.orchestrator_api.models.phase_configuration import PhaseConfiguration
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import (
    PhaseConfigurationRepository,
    ValidationResult
)
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


class TestPhaseConfigurationRepository:
    """Test suite for PhaseConfigurationRepository."""
    
    def test_create_phase_success(self, db_session):
        """Test creating phase configuration with all fields."""
        repo = PhaseConfigurationRepository()
        
        config = repo.create(
            phase_name="test_phase",
            role_name="test_role",
            artifact_type="test_artifact",
            next_phase="next_test_phase",
            config={"timeout": 30}
        )
        
        assert config.id.startswith("pc_")
        assert config.phase_name == "test_phase"
        assert config.role_name == "test_role"
        assert config.artifact_type == "test_artifact"
        assert config.next_phase == "next_test_phase"
        assert config.config == {"timeout": 30}
        assert config.is_active is True
    
    def test_create_phase_minimal_fields(self, db_session):
        """Test creating phase with only required fields."""
        repo = PhaseConfigurationRepository()
        
        config = repo.create(
            phase_name="minimal_phase",
            role_name="minimal_role",
            artifact_type="minimal_artifact"
        )
        
        assert config.phase_name == "minimal_phase"
        assert config.role_name == "minimal_role"
        assert config.artifact_type == "minimal_artifact"
        assert config.next_phase is None
        assert config.config is None
        assert config.is_active is True
    
    def test_create_terminal_phase(self, db_session):
        """Test creating terminal phase (next_phase=None)."""
        repo = PhaseConfigurationRepository()
        
        config = repo.create(
            phase_name="terminal_phase",
            role_name="terminal_role",
            artifact_type="terminal_artifact",
            next_phase=None
        )
        
        assert config.next_phase is None
    
    def test_create_phase_missing_phase_name(self, db_session):
        """Test that missing phase_name raises ValueError."""
        repo = PhaseConfigurationRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                phase_name="",
                role_name="test",
                artifact_type="test"
            )
        
        assert "phase_name is required" in str(exc_info.value)
    
    def test_create_phase_missing_role_name(self, db_session):
        """Test that missing role_name raises ValueError."""
        repo = PhaseConfigurationRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                phase_name="test",
                role_name="",
                artifact_type="test"
            )
        
        assert "role_name is required" in str(exc_info.value)
    
    def test_create_phase_missing_artifact_type(self, db_session):
        """Test that missing artifact_type raises ValueError."""
        repo = PhaseConfigurationRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                phase_name="test",
                role_name="test",
                artifact_type=""
            )
        
        assert "artifact_type is required" in str(exc_info.value)
    
    def test_create_phase_duplicate_phase_name(self, db_session):
        """Test that duplicate phase_name raises RepositoryError."""
        repo = PhaseConfigurationRepository()
        
        # Create first phase
        repo.create("duplicate", "role1", "artifact1")
        
        # Attempt duplicate
        with pytest.raises(RepositoryError) as exc_info:
            repo.create("duplicate", "role2", "artifact2")
        
        assert "constraint violation" in str(exc_info.value).lower()
    
    def test_get_by_phase_exists(self, db_session):
        """Test retrieving phase configuration by phase_name."""
        repo = PhaseConfigurationRepository()
        
        created = repo.create("test_phase", "test_role", "test_artifact")
        retrieved = repo.get_by_phase("test_phase")
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.phase_name == "test_phase"
    
    def test_get_by_phase_not_found(self, db_session):
        """Test retrieving non-existent phase."""
        repo = PhaseConfigurationRepository()
        
        config = repo.get_by_phase("nonexistent")
        
        assert config is None
    
    def test_get_all_active(self, db_session):
        """Test retrieving all active phase configurations."""
        repo = PhaseConfigurationRepository()
        
        # Create multiple phases
        repo.create("phase_a", "role_a", "artifact_a")
        repo.create("phase_b", "role_b", "artifact_b")
        repo.create("phase_c", "role_c", "artifact_c")
        
        configs = repo.get_all_active()
        
        assert len(configs) == 3
        phase_names = {c.phase_name for c in configs}
        assert phase_names == {"phase_a", "phase_b", "phase_c"}
    
    def test_update_next_phase(self, db_session):
        """Test updating next_phase for a configuration."""
        repo = PhaseConfigurationRepository()
        
        config = repo.create("test_phase", "test_role", "test_artifact", next_phase="old_next")
        
        updated = repo.update_next_phase("test_phase", "new_next")
        
        assert updated.next_phase == "new_next"
        
        # Verify persistence
        retrieved = repo.get_by_phase("test_phase")
        assert retrieved.next_phase == "new_next"
    
    def test_update_next_phase_to_null(self, db_session):
        """Test updating next_phase to None (making it terminal)."""
        repo = PhaseConfigurationRepository()
        
        config = repo.create("test_phase", "test_role", "test_artifact", next_phase="some_next")
        
        updated = repo.update_next_phase("test_phase", None)
        
        assert updated.next_phase is None
    
    def test_update_next_phase_not_found(self, db_session):
        """Test updating next_phase for non-existent phase raises ValueError."""
        repo = PhaseConfigurationRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.update_next_phase("nonexistent", "new_next")
        
        assert "not found" in str(exc_info.value)
    
    def test_validate_configuration_graph_valid(self, db_session):
        """Test validating a valid configuration graph."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create roles
        role_repo.create("role_a", "1.0", "boot", "inst")
        role_repo.create("role_b", "1.0", "boot", "inst")
        role_repo.create("role_c", "1.0", "boot", "inst")
        
        # Create valid phase chain: a → b → c → null
        phase_repo.create("phase_a", "role_a", "artifact_a", next_phase="phase_b")
        phase_repo.create("phase_b", "role_b", "artifact_b", next_phase="phase_c")
        phase_repo.create("phase_c", "role_c", "artifact_c", next_phase=None)
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validate_configuration_graph_missing_role(self, db_session):
        """Test validation fails when role doesn't exist."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create only one role
        role_repo.create("existing_role", "1.0", "boot", "inst")
        
        # Create phase with non-existent role
        phase_repo.create("phase_a", "nonexistent_role", "artifact_a")
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "nonexistent_role" in result.errors[0]
        assert "existing_role" in result.errors[0]
    
    def test_validate_configuration_graph_missing_next_phase(self, db_session):
        """Test validation fails when next_phase doesn't exist."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create role
        role_repo.create("test_role", "1.0", "boot", "inst")
        
        # Create phase with non-existent next_phase
        phase_repo.create("phase_a", "test_role", "artifact_a", next_phase="nonexistent_phase")
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "nonexistent_phase" in result.errors[0]
    
    def test_validate_configuration_graph_circular_reference(self, db_session):
        """Test validation detects circular references."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create role
        role_repo.create("test_role", "1.0", "boot", "inst")
        
        # Create circular chain: a → b → c → a
        phase_repo.create("phase_a", "test_role", "artifact_a", next_phase="phase_b")
        phase_repo.create("phase_b", "test_role", "artifact_b", next_phase="phase_c")
        phase_repo.create("phase_c", "test_role", "artifact_c", next_phase="phase_a")
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert any("circular" in error.lower() for error in result.errors)
    
    def test_validate_configuration_graph_self_loop(self, db_session):
        """Test validation detects self-referencing phase."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create role
        role_repo.create("test_role", "1.0", "boot", "inst")
        
        # Create self-loop: a → a
        phase_repo.create("phase_a", "test_role", "artifact_a", next_phase="phase_a")
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert any("circular" in error.lower() for error in result.errors)
    
    def test_validate_configuration_graph_chain_too_long(self, db_session):
        """Test validation detects chain exceeding 20 hops."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create role
        role_repo.create("test_role", "1.0", "boot", "inst")
        
        # Create chain of 25 phases
        for i in range(25):
            next_phase = f"phase_{i+1}" if i < 24 else None
            phase_repo.create(f"phase_{i}", "test_role", f"artifact_{i}", next_phase=next_phase)
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert any("exceeds maximum length" in error for error in result.errors)
    
    def test_validate_configuration_graph_multiple_errors(self, db_session):
        """Test validation returns all errors."""
        phase_repo = PhaseConfigurationRepository()
        role_repo = RolePromptRepository()
        
        # Create only one role
        role_repo.create("existing_role", "1.0", "boot", "inst")
        
        # Create phases with multiple issues
        phase_repo.create("phase_a", "nonexistent_role", "artifact_a", next_phase="nonexistent_phase")
        phase_repo.create("phase_b", "existing_role", "artifact_b", next_phase="phase_b")  # Self-loop
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Should have multiple errors
    
    def test_validate_configuration_graph_empty_database(self, db_session):
        """Test validation with no configurations (should be valid)."""
        phase_repo = PhaseConfigurationRepository()
        
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is True
        assert result.errors == []