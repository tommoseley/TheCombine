"""
Integration tests for PIPELINE-175A.

Tests end-to-end workflows with all components.
"""
import pytest
from scripts.seed_role_prompts import seed_role_prompts
from scripts.seed_phase_configuration import seed_phase_configuration
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import PhaseConfigurationRepository


class TestPipeline175AIntegration:
    """Integration tests for PIPELINE-175A."""
    
    def test_end_to_end_seed_and_query(self, db_session):
        """Test complete workflow: seed → query → build prompt."""
        # 1. Seed data
        assert seed_role_prompts() is True
        assert seed_phase_configuration() is True
        
        # 2. Query roles
        role_repo = RolePromptRepository()
        pm_prompt = role_repo.get_active_prompt("pm")
        assert pm_prompt is not None
        
        # 3. Query phases
        phase_repo = PhaseConfigurationRepository()
        pm_phase = phase_repo.get_by_phase("pm_phase")
        assert pm_phase is not None
        assert pm_phase.role_name == "pm"
        
        # 4. Build prompt
        service = RolePromptService()
        prompt_text, prompt_id = service.build_prompt(
            role_name="pm",
            pipeline_id="test_pipeline",
            phase="pm_phase",
            epic_context="Test epic"
        )
        
        assert len(prompt_text) > 0
        assert prompt_id == pm_prompt.id
        assert "# Role Bootstrap" in prompt_text
        assert "Test epic" in prompt_text
    
    def test_full_pipeline_phase_chain(self, db_session):
        """Test walking through complete phase chain."""
        # Seed data
        seed_role_prompts()
        seed_phase_configuration()
        
        phase_repo = PhaseConfigurationRepository()
        service = RolePromptService()
        
        # Walk through chain
        phases = ["pm_phase", "arch_phase", "ba_phase", "dev_phase", "qa_phase", "commit_phase"]
        
        for phase_name in phases:
            # Get phase config
            config = phase_repo.get_by_phase(phase_name)
            assert config is not None
            
            # Build prompt for phase's role
            prompt_text, prompt_id = service.build_prompt(
                role_name=config.role_name,
                pipeline_id="test_pipeline",
                phase=phase_name
            )
            
            assert len(prompt_text) > 0
            assert prompt_id is not None
    
    def test_configuration_graph_validation_after_seed(self, db_session):
        """Test that seeded configuration passes validation."""
        # Seed data
        seed_role_prompts()
        seed_phase_configuration()
        
        # Validate
        phase_repo = PhaseConfigurationRepository()
        result = phase_repo.validate_configuration_graph()
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_all_mentor_roles_present(self, db_session):
        """Test that all 5 mentor roles are seeded."""
        seed_role_prompts()
        
        role_repo = RolePromptRepository()
        mentor_roles = ["pm_mentor", "architect_mentor", "ba_mentor", "developer_mentor", "qa_mentor"]
        
        for mentor_role in mentor_roles:
            prompt = role_repo.get_active_prompt(mentor_role)
            assert prompt is not None
            assert prompt.is_active is True
            assert "mentor" in prompt.role_name.lower()
    
    def test_multi_version_prompt_workflow(self, db_session):
        """Test creating and switching between prompt versions."""
        role_repo = RolePromptRepository()
        
        # Create v1.0
        v1 = role_repo.create("test", "1.0", "boot1", "inst1", set_active=True)
        
        # Create v1.1
        v2 = role_repo.create("test", "1.1", "boot2", "inst2", set_active=True)
        
        # Verify v1.1 is active
        active = role_repo.get_active_prompt("test")
        assert active.version == "1.1"
        
        # Switch back to v1.0
        role_repo.set_active(v1.id)
        
        # Verify v1.0 is active
        active = role_repo.get_active_prompt("test")
        assert active.version == "1.0"
        
        # Verify both versions still exist
        versions = role_repo.list_versions("test")
        assert len(versions) == 2