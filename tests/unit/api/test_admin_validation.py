"""
Tests for the Admin Validation API endpoints.

These tests verify the governance guardrails per ADR-044 WS-044-08.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.services.config_validator import (
    ConfigValidator,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    reset_config_validator,
)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset services before each test."""
    reset_config_validator()
    yield
    reset_config_validator()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestValidationRules:
    """Tests for the validation rules endpoint."""

    def test_list_rules(self, client):
        """Should list all governance rules."""
        response = client.get("/api/v1/admin/validation/rules")

        assert response.status_code == 200
        data = response.json()

        assert "rules" in data
        assert "principle" in data
        assert isinstance(data["rules"], list)

        # Should have rules
        assert len(data["rules"]) > 0

        # Each rule should have required fields
        for rule in data["rules"]:
            assert "rule_id" in rule
            assert "severity" in rule
            assert "description" in rule

        # Verify key rules are present
        rule_ids = [r["rule_id"] for r in data["rules"]]
        assert "MANIFEST_MISSING" in rule_ids
        assert "EXTRACTED_DOC_FORBIDDEN" in rule_ids
        assert "PGC_REQUIRED" in rule_ids
        assert "REQUIRED_INPUT_NOT_ACTIVE" in rule_ids


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_report_starts_valid(self):
        """Report should start valid."""
        report = ValidationReport(valid=True)
        assert report.valid is True
        assert len(report.errors) == 0
        assert len(report.warnings) == 0

    def test_add_error_invalidates_report(self):
        """Adding an error should invalidate the report."""
        report = ValidationReport(valid=True)
        report.add_error("TEST_ERROR", "Test message")

        assert report.valid is False
        assert len(report.errors) == 1
        assert report.errors[0].rule_id == "TEST_ERROR"
        assert report.errors[0].severity == ValidationSeverity.ERROR

    def test_add_warning_keeps_valid(self):
        """Adding a warning should keep report valid."""
        report = ValidationReport(valid=True)
        report.add_warning("TEST_WARNING", "Test warning")

        assert report.valid is True
        assert len(report.warnings) == 1
        assert report.warnings[0].severity == ValidationSeverity.WARNING

    def test_merge_reports(self):
        """Should merge two reports correctly."""
        report1 = ValidationReport(valid=True)
        report1.add_warning("WARN_1", "Warning 1")

        report2 = ValidationReport(valid=True)
        report2.add_error("ERR_1", "Error 1")

        report1.merge(report2)

        assert report1.valid is False
        assert len(report1.warnings) == 1
        assert len(report1.errors) == 1


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_validate_missing_manifest(self, tmp_path):
        """Should fail when manifest is missing."""
        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        assert any(e.rule_id == "MANIFEST_MISSING" for e in report.errors)

    def test_validate_invalid_yaml(self, tmp_path):
        """Should fail when manifest has invalid YAML."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("{ invalid yaml: [")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        assert any(e.rule_id == "MANIFEST_INVALID_YAML" for e in report.errors)

    def test_validate_missing_required_fields(self, tmp_path):
        """Should fail when required fields are missing."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("doc_type_id: test\n")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        # Should have errors for missing fields
        missing_field_errors = [
            e for e in report.errors if e.rule_id == "REQUIRED_FIELD_MISSING"
        ]
        assert len(missing_field_errors) > 0

    def test_validate_extracted_doc_forbidden(self, tmp_path):
        """Should fail when creation_mode is extracted."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("""
doc_type_id: test
display_name: Test
version: 1.0.0
authority_level: descriptive
creation_mode: extracted
""")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        assert any(e.rule_id == "EXTRACTED_DOC_FORBIDDEN" for e in report.errors)

    def test_validate_pgc_required_for_descriptive(self, tmp_path):
        """Should fail when descriptive doc lacks PGC."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("""
doc_type_id: test
display_name: Test
version: 1.0.0
authority_level: descriptive
creation_mode: llm_generated
artifacts: {}
""")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        assert any(e.rule_id == "PGC_REQUIRED" for e in report.errors)

    def test_validate_pgc_file_missing(self, tmp_path):
        """Should fail when PGC file doesn't exist."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("""
doc_type_id: test
display_name: Test
version: 1.0.0
authority_level: descriptive
creation_mode: llm_generated
artifacts:
  pgc_context: prompts/pgc.md
""")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        assert any(e.rule_id == "PGC_FILE_MISSING" for e in report.errors)

    def test_validate_artifact_file_missing(self, tmp_path):
        """Should fail when artifact file doesn't exist."""
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("""
doc_type_id: test
display_name: Test
version: 1.0.0
authority_level: constructive
creation_mode: llm_generated
artifacts:
  task_prompt: prompts/task.md
  schema: schemas/output.json
""")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is False
        artifact_errors = [
            e for e in report.errors if e.rule_id == "ARTIFACT_FILE_MISSING"
        ]
        # Should have errors for both missing files
        assert len(artifact_errors) >= 1

    def test_validate_valid_package(self, tmp_path):
        """Should pass for valid package."""
        # Create valid package structure
        manifest_path = tmp_path / "package.yaml"
        manifest_path.write_text("""
doc_type_id: test
display_name: Test
version: 1.0.0
authority_level: constructive
creation_mode: llm_generated
artifacts:
  task_prompt: prompts/task.md
""")
        # Create artifact files
        (tmp_path / "prompts").mkdir()
        (tmp_path / "prompts" / "task.md").write_text("# Task prompt")

        validator = ConfigValidator()
        report = validator.validate_package(tmp_path)

        assert report.valid is True
        assert len(report.errors) == 0

    def test_validate_ref_format_valid(self):
        """Should validate valid reference format."""
        validator = ConfigValidator()

        assert validator._validate_ref_format("prompt:role:analyst:1.0.0", "role") is True
        assert validator._validate_ref_format("prompt:template:doc_gen:2.0.0", "template") is True

    def test_validate_ref_format_invalid(self):
        """Should reject invalid reference format."""
        validator = ConfigValidator()

        # Wrong number of parts
        assert validator._validate_ref_format("prompt:role:analyst", "role") is False
        # Wrong prefix
        assert validator._validate_ref_format("schema:role:analyst:1.0.0", "role") is False
        # Wrong type
        assert validator._validate_ref_format("prompt:template:analyst:1.0.0", "role") is False


class TestPackageValidationEndpoint:
    """Tests for package validation endpoint."""

    def test_validate_nonexistent_package(self, client):
        """Should return 404 for nonexistent package."""
        response = client.post(
            "/api/v1/admin/validation/package/nonexistent/1.0.0"
        )

        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data["detail"]
        assert data["detail"]["error_code"] == "PACKAGE_NOT_FOUND"


class TestActivationValidationEndpoint:
    """Tests for activation validation endpoint."""

    def test_validate_activation_nonexistent(self, client):
        """Should return validation errors for nonexistent package."""
        response = client.post(
            "/api/v1/admin/validation/activation",
            json={"doc_type_id": "nonexistent", "version": "1.0.0"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert data["error_count"] > 0


class TestSchemaCompatibilityEndpoint:
    """Tests for schema compatibility endpoint."""

    def test_validate_schema_compatibility_nonexistent(self, client):
        """Should handle nonexistent versions gracefully."""
        response = client.post(
            "/api/v1/admin/validation/schema-compatibility",
            json={
                "doc_type_id": "nonexistent",
                "old_version": "1.0.0",
                "new_version": "2.0.0",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have warning about skipped comparison
        assert data["warning_count"] > 0 or data["valid"] is True


class TestAllActiveValidationEndpoint:
    """Tests for all-active validation endpoint."""

    def test_validate_all_active(self, client):
        """Should validate all active packages."""
        response = client.get("/api/v1/admin/validation/all-active")

        assert response.status_code == 200
        data = response.json()

        assert "valid" in data
        assert "error_count" in data
        assert "warning_count" in data
        assert "errors" in data
        assert "warnings" in data
