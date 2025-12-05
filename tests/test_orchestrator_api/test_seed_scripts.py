"""
Tests for seed scripts.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
import pytest
from scripts.seed_role_prompts import seed_role_prompts
from scripts.seed_phase_configuration import seed_phase_configuration
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import PhaseConfigurationRepository


class TestSeedScripts:
    """Test suite for seed scripts."""
    
    def test_seed_role_prompts_empty_database(self, db_session):
        """Test seeding role prompts into empty database."""
        repo = RolePromptRepository()
        
        # Verify empty
        assert repo.get_active_prompt("pm") is None
        
        # Run seed script
        success = seed_role_prompts()
        
        assert success is True
        
        # Verify all 11 roles created
        roles = ["pm", "architect", "ba", "dev", "qa", "commit", 
                 "pm_mentor", "architect_mentor", "ba_mentor", "developer_mentor", "qa_mentor"]
        for role in roles:
            prompt = repo.get_active_prompt(role)
            assert prompt is not None
            assert prompt.version == "1.0"
            assert prompt.is_active is True
    
    def test_seed_role_prompts_idempotent(self, db_session):
        """Test that re-running seed script is safe (idempotent)."""
        # Run seed script twice
        success1 = seed_role_prompts()
        success2 = seed_role_prompts()
        
        assert success1 is True
        assert success2 is True
        
        # Verify still only one active prompt per role
        repo = RolePromptRepository()
        for role in ["pm", "architect", "ba", "dev", "qa", "commit"]:
            versions = repo.list_versions(role)
            active_count = sum(1 for v in versions if v.is_active)
            assert active_count == 1
    
    def test_seed_phase_configuration_empty_database(self, db_session):
        """Test seeding phase configuration into empty database."""
        # First seed roles (required for validation)
        seed_role_prompts()
        
        repo = PhaseConfigurationRepository()
        
        # Verify empty
        assert repo.get_by_phase("pm_phase") is None
        
        # Run seed script
        success = seed_phase_configuration()
        
        assert success is True
        
        # Verify all 6 phases created
        phases = ["pm_phase", "arch_phase", "ba_phase", "dev_phase", "qa_phase", "commit_phase"]
        for phase in phases:
            config = repo.get_by_phase(phase)
            assert config is not None
            assert config.is_active is True
    
    def test_seed_phase_configuration_idempotent(self, db_session):
        """Test that re-running phase seed script is safe."""
        # Seed roles first
        seed_role_prompts()
        
        # Run phase seed twice
        success1 = seed_phase_configuration()
        success2 = seed_phase_configuration()
        
        assert success1 is True
        assert success2 is True
        
        # Verify still only 6 configs
        repo = PhaseConfigurationRepository()
        configs = repo.get_all_active()
        assert len(configs) == 6
    
    def test_seed_phase_configuration_validates_graph(self, db_session):
        """Test that seed script validates configuration graph."""
        # Seed roles first
        seed_role_prompts()
        
        # Run seed (should validate automatically)
        success = seed_phase_configuration()
        
        assert success is True
        
        # Manually verify validation passes
        repo = PhaseConfigurationRepository()
        result = repo.validate_configuration_graph()
        assert result.is_valid is True
        assert result.errors == []
    
    def test_seed_phase_configuration_correct_chain(self, db_session):
        """Test that seeded phases form correct chain."""
        # Seed roles and phases
        seed_role_prompts()
        seed_phase_configuration()
        
        repo = PhaseConfigurationRepository()
        
        # Verify chain: pm → arch → ba → dev → qa → commit → null
        pm = repo.get_by_phase("pm_phase")
        assert pm.next_phase == "arch_phase"
        
        arch = repo.get_by_phase("arch_phase")
        assert arch.next_phase == "ba_phase"
        
        ba = repo.get_by_phase("ba_phase")
        assert ba.next_phase == "dev_phase"
        
        dev = repo.get_by_phase("dev_phase")
        assert dev.next_phase == "qa_phase"
        
        qa = repo.get_by_phase("qa_phase")
        assert qa.next_phase == "commit_phase"
        
        commit = repo.get_by_phase("commit_phase")
        assert commit.next_phase is None  # Terminal
    
    def test_seed_phase_configuration_role_mappings(self, db_session):
        """Test that phases have correct role and artifact mappings."""
        # Seed roles and phases
        seed_role_prompts()
        seed_phase_configuration()
        
        repo = PhaseConfigurationRepository()
        
        # Verify mappings
        expected_mappings = {
            "pm_phase": ("pm", "epic"),
            "arch_phase": ("architect", "arch_notes"),
            "ba_phase": ("ba", "ba_spec"),
            "dev_phase": ("dev", "proposed_change_set"),
            "qa_phase": ("qa", "qa_result"),
            "commit_phase": ("commit", "commit_result"),
        }
        
        for phase_name, (role_name, artifact_type) in expected_mappings.items():
            config = repo.get_by_phase(phase_name)
            assert config.role_name == role_name
            assert config.artifact_type == artifact_type