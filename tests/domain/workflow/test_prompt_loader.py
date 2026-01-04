"""Tests for prompt loader."""

import pytest
from pathlib import Path

from app.domain.workflow.prompt_loader import PromptLoader, PromptNotFoundError


class TestPromptLoader:
    """Tests for PromptLoader."""
    
    @pytest.fixture
    def loader(self):
        """Create a loader with real prompts directory."""
        return PromptLoader(Path("seed/prompts"))
    
    def test_load_role_returns_content(self, loader):
        """load_role returns prompt content."""
        content = loader.load_role("Technical Architect 1.0")
        
        assert isinstance(content, str)
        assert len(content) > 0
    
    def test_load_task_returns_content(self, loader):
        """load_task returns prompt content."""
        content = loader.load_task("Project Discovery v1.0")
        
        assert isinstance(content, str)
        assert len(content) > 0
    
    def test_load_role_raises_for_missing(self, loader):
        """load_role raises PromptNotFoundError for unknown role."""
        with pytest.raises(PromptNotFoundError, match="not found"):
            loader.load_role("Nonexistent Role 1.0")
    
    def test_load_task_raises_for_missing(self, loader):
        """load_task raises PromptNotFoundError for unknown task."""
        with pytest.raises(PromptNotFoundError, match="not found"):
            loader.load_task("Nonexistent Task v1.0")
    
    def test_list_roles_returns_available(self, loader):
        """list_roles returns available role names."""
        roles = loader.list_roles()
        
        assert isinstance(roles, list)
        assert "Technical Architect 1.0" in roles
        assert "Business Analyst 1.0" in roles
    
    def test_list_tasks_returns_available(self, loader):
        """list_tasks returns available task names."""
        tasks = loader.list_tasks()
        
        assert isinstance(tasks, list)
        assert "Project Discovery v1.0" in tasks
    
    def test_role_exists_true(self, loader):
        """role_exists returns True for existing role."""
        assert loader.role_exists("Technical Architect 1.0") is True
    
    def test_role_exists_false(self, loader):
        """role_exists returns False for missing role."""
        assert loader.role_exists("Nonexistent Role") is False
    
    def test_task_exists_true(self, loader):
        """task_exists returns True for existing task."""
        assert loader.task_exists("Project Discovery v1.0") is True
    
    def test_task_exists_false(self, loader):
        """task_exists returns False for missing task."""
        assert loader.task_exists("Nonexistent Task") is False
    
    def test_caching_returns_same_content(self, loader):
        """Subsequent loads return cached content."""
        content1 = loader.load_role("Technical Architect 1.0")
        content2 = loader.load_role("Technical Architect 1.0")
        
        assert content1 is content2  # Same object (cached)
    
    def test_clear_cache(self, loader):
        """clear_cache removes cached prompts."""
        content1 = loader.load_role("Technical Architect 1.0")
        loader.clear_cache()
        content2 = loader.load_role("Technical Architect 1.0")
        
        # Same content but different objects (reloaded)
        assert content1 == content2
        assert content1 is not content2
    
    def test_handles_missing_directory(self):
        """Loader handles missing directory gracefully."""
        loader = PromptLoader(Path("nonexistent/prompts"))
        
        assert loader.list_roles() == []
        assert loader.list_tasks() == []