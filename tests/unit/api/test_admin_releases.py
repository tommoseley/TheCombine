"""
Tests for the Admin Release Management API endpoints.

These tests verify the release management functionality per ADR-044 WS-044-07.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.services.release_service import (
    ReleaseService,
    ReleaseInfo,
    ReleaseState,
    ReleaseHistoryEntry,
    RollbackResult,
    ReleaseServiceError,
    ImmutabilityViolationError,
    ValidationFailedError,
    reset_release_service,
)
from app.api.services.config_validator import ValidationReport, ValidationResult, ValidationSeverity


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_release_service()
    yield
    reset_release_service()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestReleaseState:
    """Tests for ReleaseState enum."""

    def test_release_states(self):
        """Should have correct release states."""
        assert ReleaseState.DRAFT.value == "draft"
        assert ReleaseState.STAGED.value == "staged"
        assert ReleaseState.RELEASED.value == "released"


class TestReleaseInfo:
    """Tests for ReleaseInfo dataclass."""

    def test_release_info_creation(self):
        """Should create ReleaseInfo correctly."""
        info = ReleaseInfo(
            doc_type_id="project_discovery",
            version="1.0.0",
            state=ReleaseState.RELEASED,
            is_active=True,
            commit_hash="abc123",
            commit_date=datetime.now(),
            commit_author="Test User",
            commit_message="Test commit",
        )
        assert info.doc_type_id == "project_discovery"
        assert info.version == "1.0.0"
        assert info.state == ReleaseState.RELEASED
        assert info.is_active is True


class TestReleaseServiceUnit:
    """Unit tests for ReleaseService class."""

    def test_service_initialization(self):
        """Should initialize ReleaseService."""
        service = ReleaseService()
        assert service._git is not None
        assert service._validator is not None
        assert service._loader is not None

    def test_get_active_version(self):
        """Should get active version from loader."""
        service = ReleaseService()
        # This will read from the actual active_releases.json
        active = service.get_active_version("project_discovery")
        # May or may not be set, but should not raise
        assert active is None or isinstance(active, str)

    def test_check_immutability_active_version(self):
        """Should return True for active version."""
        service = ReleaseService()
        # Mock the loader to return a specific active version
        mock_active = MagicMock()
        mock_active.document_types = {"test_doc": "1.0.0"}
        service._loader.get_active_releases = MagicMock(return_value=mock_active)

        assert service.check_immutability("test_doc", "1.0.0") is True
        assert service.check_immutability("test_doc", "0.9.0") is False

    def test_enforce_immutability_raises(self):
        """Should raise ImmutabilityViolationError for active version."""
        service = ReleaseService()
        mock_active = MagicMock()
        mock_active.document_types = {"test_doc": "1.0.0"}
        service._loader.get_active_releases = MagicMock(return_value=mock_active)

        with pytest.raises(ImmutabilityViolationError) as exc:
            service.enforce_immutability("test_doc", "1.0.0")

        assert "immutable" in str(exc.value).lower()
        assert "1.0.0" in str(exc.value)


class TestListReleasesEndpoint:
    """Tests for list releases endpoint."""

    def test_list_releases_returns_list(self, client):
        """Should return list of releases."""
        # Use a document type that exists in combine-config
        response = client.get("/api/v1/admin/releases/project_discovery")

        assert response.status_code == 200
        data = response.json()

        assert "doc_type_id" in data
        assert "releases" in data
        assert "total" in data
        assert isinstance(data["releases"], list)


class TestGetReleaseInfoEndpoint:
    """Tests for get release info endpoint."""

    def test_get_release_info_existing(self, client):
        """Should return release info for existing version."""
        response = client.get("/api/v1/admin/releases/project_discovery/1.4.0")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["version"] == "1.4.0"
        assert "state" in data
        assert "is_active" in data

    def test_get_release_info_nonexistent(self, client):
        """Should return 404 for nonexistent version."""
        response = client.get("/api/v1/admin/releases/project_discovery/99.99.99")

        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data["detail"]


class TestImmutabilityEndpoint:
    """Tests for immutability check endpoint."""

    def test_check_immutability(self, client):
        """Should check immutability of a version."""
        response = client.get("/api/v1/admin/releases/project_discovery/1.4.0/immutability")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["version"] == "1.4.0"
        assert "is_immutable" in data
        assert isinstance(data["is_immutable"], bool)


class TestReleaseHistoryEndpoint:
    """Tests for release history endpoint."""

    def test_get_release_history(self, client):
        """Should return release history."""
        response = client.get("/api/v1/admin/releases/project_discovery/history")

        assert response.status_code == 200
        data = response.json()

        assert "entries" in data
        assert "total" in data
        assert isinstance(data["entries"], list)

    def test_get_all_release_history(self, client):
        """Should return all release history."""
        response = client.get("/api/v1/admin/releases/history/all")

        assert response.status_code == 200
        data = response.json()

        assert "entries" in data
        assert "total" in data


class TestValidationFailedError:
    """Tests for ValidationFailedError."""

    def test_validation_failed_error_has_report(self):
        """Should contain validation report."""
        report = ValidationReport(valid=False)
        report.add_error("TEST_ERROR", "Test error message")

        error = ValidationFailedError("Validation failed", report)

        assert error.report is report
        assert len(error.report.errors) == 1
        assert error.report.errors[0].rule_id == "TEST_ERROR"


class TestRollbackResult:
    """Tests for RollbackResult dataclass."""

    def test_rollback_result_creation(self):
        """Should create RollbackResult correctly."""
        result = RollbackResult(
            doc_type_id="test_doc",
            rolled_back_from="2.0.0",
            rolled_back_to="1.0.0",
            commit_hash="abc123",
            commit_message="Rollback test_doc from 2.0.0 to 1.0.0",
        )
        assert result.doc_type_id == "test_doc"
        assert result.rolled_back_from == "2.0.0"
        assert result.rolled_back_to == "1.0.0"


class TestReleaseHistoryEntry:
    """Tests for ReleaseHistoryEntry dataclass."""

    def test_history_entry_creation(self):
        """Should create ReleaseHistoryEntry correctly."""
        entry = ReleaseHistoryEntry(
            doc_type_id="test_doc",
            action="activated",
            version="1.0.0",
            previous_version=None,
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test User",
            message="Activate version 1.0.0",
        )
        assert entry.action == "activated"
        assert entry.previous_version is None
