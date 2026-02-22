"""
Tests for WorkPackageHandler — WS-ONTOLOGY-001.

Six test groups mapping to the six Tier 1 verification criteria:
  C1: Document type registration
  C2: Schema fields present
  C3: Valid state transitions accepted
  C4: Invalid state transitions rejected
  C5: CRUD via document APIs (handler methods)
  C6: Default rollup fields
"""

import pytest

from app.domain.handlers.registry import HANDLERS
from app.config.package_loader import get_package_loader
from app.domain.handlers.work_package_handler import WorkPackageHandler
from app.domain.services.work_package_state import (
    validate_wp_transition,
    InvalidWPTransitionError,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return WorkPackageHandler()


@pytest.fixture
def wp_schema():
    """Return the output schema from combine-config."""
    package = get_package_loader().get_document_type("work_package")
    schema = package.get_schema()
    assert schema is not None, "work_package schema not found in combine-config"
    return schema


@pytest.fixture
def valid_wp_content():
    """Minimal well-formed Work Package content."""
    return {
        "wp_id": "WP-001",
        "title": "Implement Authentication",
        "rationale": "Users need secure access",
        "scope_in": ["Login flow", "JWT tokens"],
        "scope_out": ["SSO integration"],
        "dependencies": [],
        "definition_of_done": ["All endpoints secured", "Tests pass"],
        "state": "PLANNED",
        "ws_child_refs": [],
        "governance_pins": {},
    }


# =========================================================================
# C1 — Document type registration
# =========================================================================


class TestC1Registration:
    def test_handler_registered_in_registry(self):
        assert "work_package" in HANDLERS

    def test_handler_doc_type_id(self, handler):
        assert handler.doc_type_id == "work_package"

    def test_combine_config_entry_exists(self):
        ids = get_package_loader().list_document_types()
        assert "work_package" in ids


# =========================================================================
# C2 — Schema fields present
# =========================================================================


REQUIRED_FIELDS = [
    "wp_id",
    "title",
    "rationale",
    "scope_in",
    "scope_out",
    "dependencies",
    "definition_of_done",
    "governance_pins",
]


class TestC2SchemaFields:
    def test_schema_requires_all_fields(self, wp_schema):
        required = wp_schema.get("required", [])
        for field in REQUIRED_FIELDS:
            assert field in required, f"'{field}' missing from schema required list"

    def test_schema_defines_properties(self, wp_schema):
        props = wp_schema.get("properties", {})
        expected_types = {
            "wp_id": "string",
            "title": "string",
            "rationale": "string",
            "scope_in": "array",
            "scope_out": "array",
            "dependencies": "array",
            "definition_of_done": "array",
            "state": "string",
            "ws_child_refs": "array",
            "governance_pins": "object",
        }
        for field, expected_type in expected_types.items():
            assert field in props, f"'{field}' missing from schema properties"
            assert props[field]["type"] == expected_type, (
                f"'{field}' type should be '{expected_type}', "
                f"got '{props[field].get('type')}'"
            )


# =========================================================================
# C3 — Valid state transitions accepted
# =========================================================================


class TestC3ValidTransitions:
    def test_valid_transition_planned_to_ready(self):
        assert validate_wp_transition("PLANNED", "READY") is True

    def test_valid_transition_ready_to_in_progress(self):
        assert validate_wp_transition("READY", "IN_PROGRESS") is True

    def test_valid_transition_in_progress_to_awaiting_gate(self):
        assert validate_wp_transition("IN_PROGRESS", "AWAITING_GATE") is True

    def test_valid_transition_awaiting_gate_to_done(self):
        assert validate_wp_transition("AWAITING_GATE", "DONE") is True


# =========================================================================
# C4 — Invalid state transitions rejected
# =========================================================================


class TestC4InvalidTransitions:
    def test_invalid_transition_planned_to_in_progress(self):
        with pytest.raises(InvalidWPTransitionError):
            validate_wp_transition("PLANNED", "IN_PROGRESS")

    def test_invalid_transition_done_to_any(self):
        with pytest.raises(InvalidWPTransitionError):
            validate_wp_transition("DONE", "PLANNED")

    def test_invalid_transition_in_progress_to_planned(self):
        with pytest.raises(InvalidWPTransitionError):
            validate_wp_transition("IN_PROGRESS", "PLANNED")


# =========================================================================
# C5 — CRUD via document APIs (handler methods)
# =========================================================================


class TestC5HandlerMethods:
    def test_handler_validate_accepts_valid_wp(self, handler, valid_wp_content, wp_schema):
        is_valid, errors = handler.validate(valid_wp_content, wp_schema)
        assert is_valid is True
        assert errors == []

    def test_handler_validate_rejects_missing_fields(self, handler, wp_schema):
        incomplete = {"wp_id": "WP-001", "title": "Incomplete"}
        is_valid, errors = handler.validate(incomplete, wp_schema)
        assert is_valid is False
        assert len(errors) > 0

    def test_handler_extract_title(self, handler, valid_wp_content):
        title = handler.extract_title(valid_wp_content)
        assert title == "Implement Authentication"

    def test_handler_transform_sets_defaults(self, handler, valid_wp_content):
        result = handler.transform(valid_wp_content)
        assert "ws_total" in result
        assert "ws_done" in result
        assert "mode_b_count" in result


# =========================================================================
# C6 — Default rollup fields
# =========================================================================


class TestC6DefaultRollups:
    def test_default_ws_total_is_zero(self, handler, valid_wp_content):
        result = handler.transform(valid_wp_content)
        assert result["ws_total"] == 0

    def test_default_ws_done_is_zero(self, handler, valid_wp_content):
        result = handler.transform(valid_wp_content)
        assert result["ws_done"] == 0

    def test_default_mode_b_count_is_zero(self, handler, valid_wp_content):
        result = handler.transform(valid_wp_content)
        assert result["mode_b_count"] == 0

    def test_existing_rollups_preserved(self, handler, valid_wp_content):
        valid_wp_content["ws_total"] = 5
        valid_wp_content["ws_done"] = 3
        valid_wp_content["mode_b_count"] = 1
        result = handler.transform(valid_wp_content)
        assert result["ws_total"] == 5
        assert result["ws_done"] == 3
        assert result["mode_b_count"] == 1
