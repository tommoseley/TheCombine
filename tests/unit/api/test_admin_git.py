"""
Tests for the Admin Git API endpoints.

These tests verify the Git operations for the Admin Workbench.
Note: These tests operate on the real combine-config repository.
"""

import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.services.git_service import (
    GitService,
    reset_git_service,
)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_git_service()
    yield
    reset_git_service()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def git_service():
    """Create a Git service instance."""
    return GitService()


class TestGitStatus:
    """Tests for Git status endpoint."""

    def test_get_status(self, client):
        """Should return Git status."""
        response = client.get("/api/v1/admin/git/status")

        assert response.status_code == 200
        data = response.json()

        assert "branch" in data
        assert "base_commit" in data
        assert "base_commit_short" in data
        assert "is_dirty" in data
        assert "modified_files" in data
        assert "added_files" in data
        assert "deleted_files" in data
        assert "untracked_files" in data
        assert "total_changes" in data

        # Branch should be a string
        assert isinstance(data["branch"], str)
        assert len(data["branch"]) > 0

        # Commit hash should be present
        assert len(data["base_commit"]) == 40  # Full SHA
        assert len(data["base_commit_short"]) == 7  # Short SHA


class TestGitDiff:
    """Tests for Git diff endpoint."""

    def test_get_diff_empty(self, client):
        """Should return empty diff when no changes."""
        response = client.get("/api/v1/admin/git/diff")

        assert response.status_code == 200
        data = response.json()

        assert "diffs" in data
        assert "total_files" in data
        assert "total_additions" in data
        assert "total_deletions" in data


class TestGitBranches:
    """Tests for Git branch endpoints."""

    def test_list_branches(self, client):
        """Should list branches."""
        response = client.get("/api/v1/admin/git/branches")

        assert response.status_code == 200
        data = response.json()

        assert "branches" in data
        assert "current_branch" in data
        assert isinstance(data["branches"], list)

        # Should have at least one branch
        assert len(data["branches"]) >= 1

        # Each branch should have required fields
        for branch in data["branches"]:
            assert "name" in branch
            assert "commit_hash" in branch
            assert "is_current" in branch


class TestGitCommitHistory:
    """Tests for Git commit history endpoint."""

    def test_get_commit_history(self, client):
        """Should return commit history."""
        response = client.get("/api/v1/admin/git/commits")

        assert response.status_code == 200
        data = response.json()

        assert "commits" in data
        assert "total" in data
        assert isinstance(data["commits"], list)

        # Should have commits
        assert len(data["commits"]) > 0

        # Each commit should have required fields
        for commit in data["commits"]:
            assert "commit_hash" in commit
            assert "commit_hash_short" in commit
            assert "author" in commit
            assert "date" in commit
            assert "message" in commit

    def test_get_commit_history_with_path(self, client):
        """Should return commit history filtered by path."""
        response = client.get(
            "/api/v1/admin/git/commits",
            params={"path": "_active/active_releases.json"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "commits" in data
        # May have commits for this path
        assert isinstance(data["commits"], list)

    def test_get_commit_history_with_limit(self, client):
        """Should respect limit parameter."""
        response = client.get(
            "/api/v1/admin/git/commits",
            params={"limit": 5},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["commits"]) <= 5


class TestGitFileContent:
    """Tests for Git file content endpoint."""

    def test_get_file_content(self, client):
        """Should return file content at HEAD."""
        response = client.get("/api/v1/admin/git/file/_active/active_releases.json")

        assert response.status_code == 200
        data = response.json()

        assert data["file_path"] == "_active/active_releases.json"
        assert data["ref"] == "HEAD"
        assert data["exists"] is True
        assert data["content"] is not None
        assert "document_types" in data["content"]

    def test_get_nonexistent_file(self, client):
        """Should indicate file doesn't exist."""
        response = client.get("/api/v1/admin/git/file/nonexistent/file.txt")

        assert response.status_code == 200
        data = response.json()

        assert data["exists"] is False
        assert data["content"] is None


class TestGitServiceUnit:
    """Unit tests for GitService class."""

    def test_service_initialization(self, git_service):
        """Should initialize with valid repo path."""
        assert git_service.repo_path.exists()
        assert (git_service.repo_path / ".git").exists()

    def test_get_status(self, git_service):
        """Should return status object."""
        status = git_service.get_status()

        assert status.branch is not None
        assert status.base_commit is not None
        assert len(status.base_commit) == 40

    def test_list_branches(self, git_service):
        """Should list branches."""
        branches = git_service.list_branches()

        assert len(branches) >= 1
        # At least one should be current
        current_branches = [b for b in branches if b.is_current]
        assert len(current_branches) == 1

    def test_get_commit(self, git_service):
        """Should get commit info."""
        commit = git_service.get_commit("HEAD")

        assert commit.commit_hash is not None
        assert len(commit.commit_hash) == 40
        assert commit.author is not None
        assert commit.message is not None

    def test_get_file_content(self, git_service):
        """Should get file content."""
        content = git_service.get_file_content("_active/active_releases.json")

        assert content is not None
        assert "document_types" in content

    def test_get_file_content_nonexistent(self, git_service):
        """Should return None for nonexistent file."""
        content = git_service.get_file_content("nonexistent.txt")

        assert content is None

    def test_list_tags(self, git_service):
        """Should list tags (may be empty)."""
        tags = git_service.list_tags()

        assert isinstance(tags, list)
