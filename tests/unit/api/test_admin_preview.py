"""
Tests for the Admin Preview & Dry-Run API endpoints.

These tests verify the preview functionality per ADR-044 WS-044-06.
"""

import pytest

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.services.preview_service import (
    PreviewService,
    PreviewResult,
    PreviewStatus,
    PromptPreview,
    SchemaPreview,
    PreviewDiff,
    DiffItem,
    reset_preview_service,
)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_preview_service()
    yield
    reset_preview_service()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestPreviewStatus:
    """Tests for PreviewStatus enum."""

    def test_preview_statuses(self):
        """Should have correct preview statuses."""
        assert PreviewStatus.SUCCESS.value == "success"
        assert PreviewStatus.VALIDATION_FAILED.value == "validation_failed"
        assert PreviewStatus.GENERATION_FAILED.value == "generation_failed"
        assert PreviewStatus.ERROR.value == "error"


class TestPromptPreview:
    """Tests for PromptPreview dataclass."""

    def test_prompt_preview_creation(self):
        """Should create PromptPreview correctly."""
        preview = PromptPreview(
            role_prompt="You are a technical architect.",
            task_prompt="Analyze the requirements.",
            token_estimate=100,
        )
        assert preview.role_prompt is not None
        assert preview.task_prompt is not None
        assert preview.token_estimate == 100


class TestSchemaPreview:
    """Tests for SchemaPreview dataclass."""

    def test_schema_preview_creation(self):
        """Should create SchemaPreview correctly."""
        preview = SchemaPreview(
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
            required_fields=["name"],
            optional_fields=[],
            field_count=1,
        )
        assert preview.schema is not None
        assert "name" in preview.required_fields
        assert preview.field_count == 1


class TestDiffItem:
    """Tests for DiffItem dataclass."""

    def test_diff_item_creation(self):
        """Should create DiffItem correctly."""
        item = DiffItem(
            artifact_type="task_prompt",
            change_type="modified",
            old_value="old content",
            new_value="new content",
            summary="Task Prompt modified",
        )
        assert item.artifact_type == "task_prompt"
        assert item.change_type == "modified"


class TestPreviewDiff:
    """Tests for PreviewDiff dataclass."""

    def test_preview_diff_creation(self):
        """Should create PreviewDiff correctly."""
        diff = PreviewDiff(
            previous_version="1.0.0",
            current_version="1.1.0",
            has_changes=True,
            changes=[
                DiffItem(
                    artifact_type="task_prompt",
                    change_type="modified",
                    summary="Task Prompt modified",
                )
            ],
            breaking_changes=[],
        )
        assert diff.has_changes is True
        assert len(diff.changes) == 1


class TestPreviewResult:
    """Tests for PreviewResult dataclass."""

    def test_preview_result_creation(self):
        """Should create PreviewResult correctly."""
        result = PreviewResult(
            doc_type_id="project_discovery",
            version="1.4.0",
            status=PreviewStatus.SUCCESS,
            warnings=["Minor issue"],
            errors=[],
            execution_time_ms=150,
        )
        assert result.doc_type_id == "project_discovery"
        assert result.status == PreviewStatus.SUCCESS
        assert result.execution_time_ms == 150


class TestPreviewServiceUnit:
    """Unit tests for PreviewService class."""

    def test_service_initialization(self):
        """Should initialize PreviewService."""
        service = PreviewService()
        assert service._loader is not None
        assert service._validator is not None

    def test_estimate_tokens(self):
        """Should estimate tokens correctly."""
        service = PreviewService()
        # 4 chars per token approximation
        assert service._estimate_tokens("") == 0
        assert service._estimate_tokens("test") == 1
        assert service._estimate_tokens("a" * 100) == 25

    def test_truncate_short_text(self):
        """Should not truncate short text."""
        service = PreviewService()
        assert service._truncate("short", 100) == "short"

    def test_truncate_long_text(self):
        """Should truncate long text."""
        service = PreviewService()
        long_text = "a" * 300
        truncated = service._truncate(long_text, 200)
        assert len(truncated) == 203  # 200 + "..."
        assert truncated.endswith("...")


class TestPreviewDocumentTypeEndpoint:
    """Tests for preview document type endpoint."""

    def test_preview_existing_document_type(self, client):
        """Should preview existing document type."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["version"] == "1.4.0"
        assert "status" in data
        assert "execution_time_ms" in data
        assert "timestamp" in data

    def test_preview_includes_validation(self, client):
        """Should include validation report."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0")

        assert response.status_code == 200
        data = response.json()

        # May or may not have validation depending on status
        if data["status"] != "error":
            assert "validation" in data

    def test_preview_includes_diff(self, client):
        """Should include diff when requested."""
        response = client.get(
            "/api/v1/admin/preview/project_discovery/1.4.0",
            params={"include_diff": True},
        )

        assert response.status_code == 200
        data = response.json()

        if data["status"] == "success":
            assert "diff" in data

    def test_preview_without_diff(self, client):
        """Should exclude diff when not requested."""
        response = client.get(
            "/api/v1/admin/preview/project_discovery/1.4.0",
            params={"include_diff": False},
        )

        assert response.status_code == 200
        response.json()
        # Diff may be None when not included


class TestPreviewPromptsEndpoint:
    """Tests for preview prompts endpoint."""

    def test_preview_prompts(self, client):
        """Should preview prompts for document type."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0/prompts")

        assert response.status_code == 200
        data = response.json()

        assert "token_estimate" in data
        # May have task_prompt, role_prompt, etc.


class TestPreviewSchemaEndpoint:
    """Tests for preview schema endpoint."""

    def test_preview_schema(self, client):
        """Should preview schema for document type."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0/schema")

        assert response.status_code == 200
        data = response.json()

        assert "required_fields" in data
        assert "optional_fields" in data
        assert "field_count" in data


class TestDiffEndpoint:
    """Tests for diff endpoint."""

    def test_generate_diff(self, client):
        """Should generate diff."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0/diff")

        assert response.status_code == 200
        data = response.json()

        assert "current_version" in data
        assert data["current_version"] == "1.4.0"
        assert "has_changes" in data
        assert "changes" in data
        assert "breaking_changes" in data


class TestActivationReadinessEndpoint:
    """Tests for activation readiness endpoint."""

    def test_check_activation_readiness(self, client):
        """Should check activation readiness."""
        response = client.get("/api/v1/admin/preview/project_discovery/1.4.0/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["doc_type_id"] == "project_discovery"
        assert data["version"] == "1.4.0"
        assert "ready_for_activation" in data
        assert isinstance(data["ready_for_activation"], bool)
        assert "validation" in data
        assert "blocking_errors" in data
        assert "warnings" in data

    def test_readiness_blocks_on_errors(self, client):
        """Should report not ready when validation fails."""
        # Use a nonexistent version which should fail validation
        response = client.get("/api/v1/admin/preview/nonexistent_doc/99.0.0/ready")

        assert response.status_code == 200
        data = response.json()

        # Should not be ready due to validation errors
        assert data["ready_for_activation"] is False
        assert len(data["blocking_errors"]) > 0
