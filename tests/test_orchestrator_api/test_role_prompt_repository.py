"""
Test RolePromptRepository with PostgreSQL database.
"""
import pytest
from datetime import datetime, timezone

from app.combine.persistence.repositories.role_prompt_repository import (
    RolePromptRepository
)
from app.combine.persistence.repositories.exceptions import RepositoryError
from database import SessionLocal


@pytest.fixture
def clean_prompts():
    """Clean up role_prompts table before and after tests."""
    session = SessionLocal()
    try:
        # Clean before test
        session.execute("DELETE FROM role_prompts WHERE role_name LIKE 'test_%'")
        session.commit()
        yield
        # Clean after test
        session.execute("DELETE FROM role_prompts WHERE role_name LIKE 'test_%'")
        session.commit()
    finally:
        session.close()


class TestRolePromptRepository:
    """Test RolePromptRepository operations."""
    
    def test_create_prompt(self, clean_prompts):
        """Test creating a new role prompt."""
        repo = RolePromptRepository()
        
        prompt = repo.create(
            role_name="test_pm",
            version="1.0",
            instructions="Test PM instructions",
            expected_schema={"type": "object"},
            created_by="test_user",
            notes="Test prompt"
        )
        
        assert prompt is not None
        assert prompt.role_name == "test_pm"
        assert prompt.version == "1.0"
        assert prompt.instructions == "Test PM instructions"
        assert prompt.is_active is True
        assert prompt.created_at is not None
        assert prompt.created_at.tzinfo is not None  # Timezone-aware
    
    def test_get_active_prompt(self, clean_prompts):
        """Test retrieving active prompt."""
        repo = RolePromptRepository()
        
        # Create prompt
        repo.create(
            role_name="test_architect",
            version="1.0",
            instructions="Test architect instructions"
        )
        
        # Retrieve active
        prompt = repo.get_active_prompt("test_architect")
        
        assert prompt is not None
        assert prompt.role_name == "test_architect"
        assert prompt.is_active is True
    
    def test_multiple_versions_only_one_active(self, clean_prompts):
        """Test that only one version is active at a time."""
        repo = RolePromptRepository()
        
        # Create v1
        v1 = repo.create(
            role_name="test_ba",
            version="1.0",
            instructions="Version 1"
        )
        assert v1.is_active is True
        
        # Create v2 (should deactivate v1)
        v2 = repo.create(
            role_name="test_ba",
            version="2.0",
            instructions="Version 2"
        )
        assert v2.is_active is True
        
        # Check v1 was deactivated
        v1_reloaded = repo.get_by_id(v1.id)
        assert v1_reloaded.is_active is False
        
        # Active should be v2
        active = repo.get_active_prompt("test_ba")
        assert active.id == v2.id
    
    def test_set_active(self, clean_prompts):
        """Test setting a specific version as active."""
        repo = RolePromptRepository()
        
        # Create two versions
        v1 = repo.create(
            role_name="test_dev",
            version="1.0",
            instructions="Version 1",
            set_active=False
        )
        v2 = repo.create(
            role_name="test_dev",
            version="2.0",
            instructions="Version 2",
            set_active=True
        )
        
        # Set v1 as active
        repo.set_active(v1.id)
        
        # Verify v1 is active
        active = repo.get_active_prompt("test_dev")
        assert active.id == v1.id
        
        # Verify v2 is inactive
        v2_reloaded = repo.get_by_id(v2.id)
        assert v2_reloaded.is_active is False
    
    def test_list_versions(self, clean_prompts):
        """Test listing all versions for a role."""
        repo = RolePromptRepository()
        
        # Create multiple versions
        repo.create(role_name="test_qa", version="1.0", instructions="V1")
        repo.create(role_name="test_qa", version="1.1", instructions="V1.1")
        repo.create(role_name="test_qa", version="2.0", instructions="V2")
        
        # List versions
        versions = repo.list_versions("test_qa")
        
        assert len(versions) == 3
        # Should be ordered newest first
        assert versions[0].version == "2.0"
        assert versions[1].version == "1.1"
        assert versions[2].version == "1.0"
    
    def test_validation_errors(self, clean_prompts):
        """Test that validation errors are raised."""
        repo = RolePromptRepository()
        
        # Empty role_name
        with pytest.raises(ValueError, match="role_name is required"):
            repo.create(role_name="", version="1.0", instructions="Test")
        
        # Empty instructions
        with pytest.raises(ValueError, match="instructions is required"):
            repo.create(role_name="test", version="1.0", instructions="")
        
        # Invalid expected_schema type
        with pytest.raises(ValueError, match="expected_schema must be dict"):
            repo.create(
                role_name="test",
                version="1.0",
                instructions="Test",
                expected_schema="not a dict"  # Should be dict or None
            )
    
    def test_update_prompt(self, clean_prompts):
        """Test updating a prompt."""
        repo = RolePromptRepository()
        
        # Create prompt
        prompt = repo.create(
            role_name="test_update",
            version="1.0",
            instructions="Original instructions"
        )
        
        # Update it
        updated = repo.update(
            prompt_id=prompt.id,
            instructions="Updated instructions",
            notes="Updated notes"
        )
        
        assert updated is not None
        assert updated.instructions == "Updated instructions"
        assert updated.notes == "Updated notes"
        assert updated.updated_at > prompt.updated_at
    
    def test_delete_prompt(self, clean_prompts):
        """Test deleting a prompt."""
        repo = RolePromptRepository()
        
        # Create prompt
        prompt = repo.create(
            role_name="test_delete",
            version="1.0",
            instructions="To be deleted"
        )
        
        # Delete it
        deleted = repo.delete(prompt.id)
        assert deleted is True
        
        # Verify it's gone
        retrieved = repo.get_by_id(prompt.id)
        assert retrieved is None
        
        # Delete non-existent should return False
        deleted_again = repo.delete(prompt.id)
        assert deleted_again is False