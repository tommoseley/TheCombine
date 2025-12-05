"""
Tests for RolePromptRepository.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.orchestrator_api.models.role_prompt import RolePrompt
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


class TestRolePromptRepository:
    """Test suite for RolePromptRepository."""
    
    def test_create_prompt_success(self, db_session):
        """Test creating a role prompt with all fields."""
        repo = RolePromptRepository()
        
        prompt = repo.create(
            role_name="test_role",
            version="1.0",
            bootstrapper="You are a test role",
            instructions="Follow these test instructions",
            starting_prompt="Welcome to testing",
            working_schema={"test": "schema"},
            created_by="test_user",
            notes="Test prompt",
            set_active=True
        )
        
        assert prompt.id.startswith("rp_")
        assert prompt.role_name == "test_role"
        assert prompt.version == "1.0"
        assert prompt.bootstrapper == "You are a test role"
        assert prompt.instructions == "Follow these test instructions"
        assert prompt.starting_prompt == "Welcome to testing"
        assert prompt.working_schema == {"test": "schema"}
        assert prompt.is_active is True
        assert prompt.created_by == "test_user"
        assert prompt.notes == "Test prompt"
        assert isinstance(prompt.created_at, datetime)
        assert isinstance(prompt.updated_at, datetime)
    
    def test_create_prompt_minimal_fields(self, db_session):
        """Test creating prompt with only required fields."""
        repo = RolePromptRepository()
        
        prompt = repo.create(
            role_name="minimal_role",
            version="1.0",
            bootstrapper="Minimal bootstrap",
            instructions="Minimal instructions"
        )
        
        assert prompt.role_name == "minimal_role"
        assert prompt.bootstrapper == "Minimal bootstrap"
        assert prompt.instructions == "Minimal instructions"
        assert prompt.starting_prompt is None
        assert prompt.working_schema is None
        assert prompt.created_by is None
        assert prompt.notes is None
        assert prompt.is_active is True  # Default
    
    def test_create_prompt_missing_bootstrapper(self, db_session):
        """Test that creating prompt without bootstrapper raises ValueError."""
        repo = RolePromptRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                role_name="test",
                version="1.0",
                bootstrapper="",  # Empty
                instructions="Valid"
            )
        
        assert "bootstrapper is required" in str(exc_info.value)
    
    def test_create_prompt_missing_instructions(self, db_session):
        """Test that creating prompt without instructions raises ValueError."""
        repo = RolePromptRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                role_name="test",
                version="1.0",
                bootstrapper="Valid",
                instructions=""  # Empty
            )
        
        assert "instructions is required" in str(exc_info.value)
    
    def test_create_prompt_invalid_working_schema(self, db_session):
        """Test that invalid working_schema type raises ValueError."""
        repo = RolePromptRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.create(
                role_name="test",
                version="1.0",
                bootstrapper="Valid",
                instructions="Valid",
                working_schema="not a dict"  # Should be dict or None
            )
        
        assert "working_schema must be dict or None" in str(exc_info.value)
    
    def test_get_active_prompt_exists(self, db_session):
        """Test retrieving active prompt for a role."""
        repo = RolePromptRepository()
        
        # Create prompt
        created = repo.create(
            role_name="pm",
            version="1.0",
            bootstrapper="PM bootstrap",
            instructions="PM instructions",
            set_active=True
        )
        
        # Retrieve
        retrieved = repo.get_active_prompt("pm")
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.role_name == "pm"
        assert retrieved.is_active is True
    
    def test_get_active_prompt_not_found(self, db_session):
        """Test retrieving active prompt for non-existent role."""
        repo = RolePromptRepository()
        
        prompt = repo.get_active_prompt("nonexistent")
        
        assert prompt is None
    
    def test_get_by_id_exists(self, db_session):
        """Test retrieving prompt by ID."""
        repo = RolePromptRepository()
        
        created = repo.create(
            role_name="test",
            version="1.0",
            bootstrapper="Test",
            instructions="Test"
        )
        
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_by_id_not_found(self, db_session):
        """Test retrieving prompt by non-existent ID."""
        repo = RolePromptRepository()
        
        prompt = repo.get_by_id("rp_nonexistent")
        
        assert prompt is None
    
    def test_list_versions(self, db_session):
        """Test listing all versions for a role."""
        repo = RolePromptRepository()
        
        # Create multiple versions
        v1 = repo.create("test", "1.0", "boot1", "inst1", set_active=False)
        v2 = repo.create("test", "1.1", "boot2", "inst2", set_active=False)
        v3 = repo.create("test", "2.0", "boot3", "inst3", set_active=True)
        
        versions = repo.list_versions("test")
        
        assert len(versions) == 3
        # Should be ordered by created_at descending (newest first)
        assert versions[0].version == "2.0"
        assert versions[1].version == "1.1"
        assert versions[2].version == "1.0"
    
    def test_list_versions_empty(self, db_session):
        """Test listing versions for role with no prompts."""
        repo = RolePromptRepository()
        
        versions = repo.list_versions("nonexistent")
        
        assert versions == []
    
    def test_set_active_deactivates_others(self, db_session):
        """Test that set_active deactivates other versions."""
        repo = RolePromptRepository()
        
        # Create 3 versions, v3 active
        v1 = repo.create("test", "1.0", "boot1", "inst1", set_active=False)
        v2 = repo.create("test", "1.1", "boot2", "inst2", set_active=False)
        v3 = repo.create("test", "2.0", "boot3", "inst3", set_active=True)
        
        # Activate v2
        repo.set_active(v2.id)
        
        # Check states
        v1_check = repo.get_by_id(v1.id)
        v2_check = repo.get_by_id(v2.id)
        v3_check = repo.get_by_id(v3.id)
        
        assert v1_check.is_active is False
        assert v2_check.is_active is True
        assert v3_check.is_active is False
    
    def test_set_active_invalid_id(self, db_session):
        """Test set_active with non-existent ID raises ValueError."""
        repo = RolePromptRepository()
        
        with pytest.raises(ValueError) as exc_info:
            repo.set_active("rp_nonexistent")
        
        assert "Prompt not found" in str(exc_info.value)
    
    def test_create_with_set_active_true_deactivates_existing(self, db_session):
        """Test that creating with set_active=True deactivates existing active prompt."""
        repo = RolePromptRepository()
        
        # Create first active prompt
        v1 = repo.create("test", "1.0", "boot1", "inst1", set_active=True)
        assert v1.is_active is True
        
        # Create second active prompt
        v2 = repo.create("test", "2.0", "boot2", "inst2", set_active=True)
        
        # Check v1 was deactivated
        v1_check = repo.get_by_id(v1.id)
        assert v1_check.is_active is False
        assert v2.is_active is True
    
    def test_create_with_set_active_false_preserves_existing(self, db_session):
        """Test that creating with set_active=False doesn't affect existing active prompt."""
        repo = RolePromptRepository()
        
        # Create active prompt
        v1 = repo.create("test", "1.0", "boot1", "inst1", set_active=True)
        
        # Create inactive prompt
        v2 = repo.create("test", "2.0", "boot2", "inst2", set_active=False)
        
        # Check v1 still active
        v1_check = repo.get_by_id(v1.id)
        assert v1_check.is_active is True
        assert v2.is_active is False