"""
Tests for WorkPackageCandidateHandler — WS-WB-002.

Test groups:
  C1: Document type registration (handler registered, doc_type_id correct)
  C2: Schema fields present (required fields, property types)
  C3: Create succeeds with valid candidate data
  C4: Validation rejects invalid data (missing fields, wrong types)
  C5: Update rejection (immutability invariant)
  C6: Handler methods (extract_title, transform, render, render_summary)
"""

import pytest

from app.domain.handlers.registry import HANDLERS
from app.config.package_loader import get_package_loader
from app.domain.handlers.work_package_candidate_handler import (
    WorkPackageCandidateHandler,
)
from app.domain.handlers.exceptions import DocumentValidationError


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return WorkPackageCandidateHandler()


@pytest.fixture
def wpc_schema():
    """Return the output schema from combine-config."""
    package = get_package_loader().get_document_type("work_package_candidate")
    schema = package.get_schema()
    assert schema is not None, "work_package_candidate schema not found in combine-config"
    return schema


@pytest.fixture
def valid_wpc_content():
    """Minimal well-formed Work Package Candidate content."""
    return {
        "wpc_id": "WPC-001",
        "title": "Implement Authentication Module",
        "rationale": "Users need secure access to the platform",
        "scope_summary": ["Login flow", "JWT token management", "Password reset"],
        "source_ip_id": "doc-abc-123",
        "source_ip_version": "1.0.0",
        "frozen_at": "2026-03-01T12:00:00Z",
        "frozen_by": "system:ipf_reconciliation",
    }


@pytest.fixture
def valid_wpc_content_alternate():
    """Another valid WPC for testing variety."""
    return {
        "wpc_id": "WPC-042",
        "title": "Database Migration Pipeline",
        "rationale": "Schema changes need automated migration support",
        "scope_summary": ["Alembic integration", "Rollback support"],
        "source_ip_id": "doc-def-456",
        "source_ip_version": "2.1.0",
        "frozen_at": "2026-02-28T08:30:00Z",
        "frozen_by": "user:tom",
    }


# =========================================================================
# C1 — Document type registration
# =========================================================================


class TestC1Registration:
    def test_handler_registered_in_registry(self):
        assert "work_package_candidate" in HANDLERS

    def test_handler_doc_type_id(self, handler):
        assert handler.doc_type_id == "work_package_candidate"

    def test_combine_config_entry_exists(self):
        ids = get_package_loader().list_document_types()
        assert "work_package_candidate" in ids

    def test_registry_returns_correct_handler_class(self):
        handler = HANDLERS["work_package_candidate"]
        assert isinstance(handler, WorkPackageCandidateHandler)


# =========================================================================
# C2 — Schema fields present
# =========================================================================


WPC_REQUIRED_FIELDS = [
    "wpc_id",
    "title",
    "rationale",
    "scope_summary",
    "source_ip_id",
    "source_ip_version",
    "frozen_at",
    "frozen_by",
]


class TestC2SchemaFields:
    def test_schema_requires_all_fields(self, wpc_schema):
        required = wpc_schema.get("required", [])
        for field in WPC_REQUIRED_FIELDS:
            assert field in required, f"'{field}' missing from schema required list"

    def test_schema_defines_properties(self, wpc_schema):
        props = wpc_schema.get("properties", {})
        expected_types = {
            "wpc_id": "string",
            "title": "string",
            "rationale": "string",
            "scope_summary": "array",
            "source_ip_id": "string",
            "source_ip_version": "string",
            "frozen_at": "string",
            "frozen_by": "string",
        }
        for field, expected_type in expected_types.items():
            assert field in props, f"'{field}' missing from schema properties"
            assert props[field]["type"] == expected_type, (
                f"'{field}' type should be '{expected_type}', "
                f"got '{props[field].get('type')}'"
            )

    def test_schema_disallows_additional_properties(self, wpc_schema):
        assert wpc_schema.get("additionalProperties") is False


# =========================================================================
# C3 — Create succeeds with valid candidate data
# =========================================================================


class TestC3CreateValid:
    def test_validate_accepts_valid_content(self, handler, valid_wpc_content, wpc_schema):
        is_valid, errors = handler.validate(valid_wpc_content, wpc_schema)
        assert is_valid is True
        assert errors == []

    def test_validate_accepts_alternate_content(
        self, handler, valid_wpc_content_alternate, wpc_schema
    ):
        is_valid, errors = handler.validate(valid_wpc_content_alternate, wpc_schema)
        assert is_valid is True
        assert errors == []

    def test_transform_returns_data_unchanged(self, handler, valid_wpc_content):
        """WPC transform should not mutate the data — candidates are frozen."""
        import copy

        original = copy.deepcopy(valid_wpc_content)
        result = handler.transform(valid_wpc_content)
        assert result == original

    def test_process_pipeline_succeeds(self, handler, valid_wpc_content, wpc_schema):
        """Full parse-validate-transform pipeline works with JSON input."""
        import json

        raw = json.dumps(valid_wpc_content)
        result = handler.process(raw, wpc_schema)
        assert result["doc_type_id"] == "work_package_candidate"
        assert result["title"] == "Implement Authentication Module"
        assert result["data"]["wpc_id"] == "WPC-001"


# =========================================================================
# C4 — Validation rejects invalid data
# =========================================================================


class TestC4ValidationRejectsInvalid:
    def test_rejects_missing_required_fields(self, handler, wpc_schema):
        incomplete = {"wpc_id": "WPC-001", "title": "Incomplete"}
        is_valid, errors = handler.validate(incomplete, wpc_schema)
        assert is_valid is False
        assert len(errors) > 0

    def test_rejects_null_required_field(self, handler, valid_wpc_content, wpc_schema):
        valid_wpc_content["rationale"] = None
        is_valid, errors = handler.validate(valid_wpc_content, wpc_schema)
        assert is_valid is False
        assert any("rationale" in e for e in errors)

    def test_rejects_wrong_type_scope_summary(self, handler, valid_wpc_content, wpc_schema):
        valid_wpc_content["scope_summary"] = "not an array"
        is_valid, errors = handler.validate(valid_wpc_content, wpc_schema)
        assert is_valid is False
        assert any("scope_summary" in e for e in errors)

    def test_rejects_invalid_wpc_id_format(self, handler, valid_wpc_content, wpc_schema):
        """wpc_id must match WPC-NNN pattern."""
        valid_wpc_content["wpc_id"] = "INVALID-ID"
        is_valid, errors = handler.validate(valid_wpc_content, wpc_schema)
        assert is_valid is False
        assert any("wpc_id" in e for e in errors)

    def test_validate_or_raise_throws(self, handler, wpc_schema):
        incomplete = {"wpc_id": "WPC-001"}
        with pytest.raises(DocumentValidationError):
            handler.validate_or_raise(incomplete, wpc_schema)


# =========================================================================
# C5 — Update rejection (immutability invariant)
# =========================================================================


class TestC5ImmutabilityInvariant:
    def test_reject_update_raises_validation_error(self, handler, valid_wpc_content, wpc_schema):
        """When existing_document is provided, handler must reject the update."""
        with pytest.raises(DocumentValidationError) as exc_info:
            handler.validate_update(valid_wpc_content, wpc_schema)
        assert "immutable" in str(exc_info.value).lower()

    def test_reject_update_error_references_doc_type(self, handler, valid_wpc_content, wpc_schema):
        with pytest.raises(DocumentValidationError) as exc_info:
            handler.validate_update(valid_wpc_content, wpc_schema)
        assert exc_info.value.doc_type_id == "work_package_candidate"

    def test_reject_update_error_has_errors_list(self, handler, valid_wpc_content, wpc_schema):
        with pytest.raises(DocumentValidationError) as exc_info:
            handler.validate_update(valid_wpc_content, wpc_schema)
        assert len(exc_info.value.errors) > 0


# =========================================================================
# C6 — Handler methods (title, render, render_summary)
# =========================================================================


class TestC6HandlerMethods:
    def test_extract_title(self, handler, valid_wpc_content):
        title = handler.extract_title(valid_wpc_content)
        assert title == "Implement Authentication Module"

    def test_extract_title_fallback(self, handler):
        title = handler.extract_title({})
        assert title == "Untitled Work Package Candidate"

    def test_render_contains_title(self, handler, valid_wpc_content):
        html = handler.render(valid_wpc_content)
        assert "Implement Authentication Module" in html

    def test_render_contains_wpc_id(self, handler, valid_wpc_content):
        html = handler.render(valid_wpc_content)
        assert "WPC-001" in html

    def test_render_contains_scope_items(self, handler, valid_wpc_content):
        html = handler.render(valid_wpc_content)
        assert "Login flow" in html
        assert "JWT token management" in html

    def test_render_contains_source_ip_info(self, handler, valid_wpc_content):
        html = handler.render(valid_wpc_content)
        assert "doc-abc-123" in html

    def test_render_summary_contains_title(self, handler, valid_wpc_content):
        html = handler.render_summary(valid_wpc_content)
        assert "Implement Authentication Module" in html

    def test_render_summary_contains_wpc_id(self, handler, valid_wpc_content):
        html = handler.render_summary(valid_wpc_content)
        assert "WPC-001" in html

    def test_render_escapes_html(self, handler):
        """Verify HTML special characters are escaped."""
        data = {
            "wpc_id": "WPC-001",
            "title": "<script>alert('xss')</script>",
            "rationale": "Test & verify",
            "scope_summary": ["Item <b>one</b>"],
            "source_ip_id": "doc-123",
            "source_ip_version": "1.0.0",
            "frozen_at": "2026-03-01T12:00:00Z",
            "frozen_by": "system",
        }
        html = handler.render(data)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
