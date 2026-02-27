"""Tests for prompt loader."""

import pytest

from app.domain.workflow.prompt_loader import PromptLoader, PromptNotFoundError


class TestPromptLoader:
    """Tests for PromptLoader.

    Note: PromptLoader now uses PackageLoader with combine-config/ structure.
    The prompts_dir parameter is ignored for backward compatibility.
    Tests use snake_case task/role IDs to load active versions.
    """

    @pytest.fixture
    def loader(self):
        """Create a loader."""
        return PromptLoader()

    def test_load_role_returns_content(self, loader):
        """load_role returns prompt content."""
        # Use snake_case ID to load active version
        content = loader.load_role("technical_architect")

        assert isinstance(content, str)
        assert len(content) > 0

    def test_load_task_returns_content(self, loader):
        """load_task returns prompt content."""
        # Use snake_case ID to load active version
        content = loader.load_task("project_discovery")

        assert isinstance(content, str)
        assert len(content) > 0

    def test_load_role_raises_for_missing(self, loader):
        """load_role raises PromptNotFoundError for unknown role."""
        with pytest.raises(PromptNotFoundError, match="not found"):
            loader.load_role("nonexistent_role")

    def test_load_task_raises_for_missing(self, loader):
        """load_task raises PromptNotFoundError for unknown task."""
        with pytest.raises(PromptNotFoundError, match="not found"):
            loader.load_task("nonexistent_task")

    def test_list_roles_returns_available(self, loader):
        """list_roles returns available role IDs."""
        roles = loader.list_roles()

        assert isinstance(roles, list)
        assert "technical_architect" in roles
        assert "business_analyst" in roles

    def test_list_tasks_returns_available(self, loader):
        """list_tasks returns available task IDs."""
        tasks = loader.list_tasks()

        assert isinstance(tasks, list)
        assert "project_discovery" in tasks

    def test_role_exists_true(self, loader):
        """role_exists returns True for existing role."""
        assert loader.role_exists("technical_architect") is True

    def test_role_exists_false(self, loader):
        """role_exists returns False for missing role."""
        assert loader.role_exists("nonexistent_role") is False

    def test_task_exists_true(self, loader):
        """task_exists returns True for existing task."""
        assert loader.task_exists("project_discovery") is True

    def test_task_exists_false(self, loader):
        """task_exists returns False for missing task."""
        assert loader.task_exists("nonexistent_task") is False

    def test_caching_returns_same_content(self, loader):
        """Subsequent loads return cached content."""
        content1 = loader.load_role("technical_architect")
        content2 = loader.load_role("technical_architect")

        assert content1 is content2  # Same object (cached)

    def test_clear_cache(self, loader):
        """clear_cache removes cached prompts from PromptLoader's internal cache."""
        content1 = loader.load_role("technical_architect")
        assert "technical_architect" in loader._role_cache

        loader.clear_cache()
        assert loader._role_cache == {}
        assert loader._task_cache == {}

        # Can reload after cache clear
        content2 = loader.load_role("technical_architect")
        assert content1 == content2

    def test_handles_missing_directory(self):
        """Loader uses PackageLoader which handles missing content gracefully."""
        # The PromptLoader now uses PackageLoader, which loads from combine-config
        # and returns empty lists when packages don't exist
        loader = PromptLoader()
        roles = loader.list_roles()
        tasks = loader.list_tasks()

        # Should return lists (possibly with content from combine-config)
        assert isinstance(roles, list)
        assert isinstance(tasks, list)