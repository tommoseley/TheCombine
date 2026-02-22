"""
Tests for WorkStatementHandler — WS-ONTOLOGY-002.

Eight test groups mapping to the eight Tier 1 verification criteria:
  C1: Document type registration
  C2: Parent required
  C3: Parent must exist
  C4: WP rollup updated on registration
  C5: Valid lifecycle transitions accepted
  C6: Invalid lifecycle transitions rejected
  C7: Governance pins inherited
  C8: WP progress reflects WS states
"""

import pytest

from app.domain.handlers.registry import HANDLERS
from app.config.package_loader import get_package_loader
from app.domain.handlers.work_statement_handler import WorkStatementHandler
from app.domain.services.work_statement_state import (
    validate_ws_transition,
    InvalidWSTransitionError,
)
from app.domain.services.work_statement_registration import (
    validate_parent_exists,
    inherit_governance_pins,
    register_ws_on_wp,
    apply_ws_accepted_to_wp,
    ParentNotFoundError,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return WorkStatementHandler()


@pytest.fixture
def ws_schema():
    """Return the output schema from combine-config."""
    package = get_package_loader().get_document_type("work_statement")
    schema = package.get_schema()
    assert schema is not None, "work_statement schema not found in combine-config"
    return schema


@pytest.fixture
def valid_ws_content():
    """Minimal well-formed Work Statement content."""
    return {
        "ws_id": "WS-001",
        "parent_wp_id": "WP-001",
        "title": "Implement Login Flow",
        "objective": "Enable user authentication via JWT",
        "scope_in": ["Login endpoint", "Token generation"],
        "scope_out": ["Password reset"],
        "procedure": ["Step 1: Create endpoint", "Step 2: Add JWT"],
        "verification_criteria": ["Login returns 200 with valid creds"],
        "prohibited_actions": ["Do not modify user table schema"],
        "state": "DRAFT",
        "governance_pins": {},
    }


@pytest.fixture
def wp_data():
    """Minimal WP dict for cross-document operations."""
    return {
        "wp_id": "WP-001",
        "title": "Auth Work Package",
        "state": "PLANNED",
        "ws_total": 0,
        "ws_done": 0,
        "ws_child_refs": [],
        "governance_pins": {
            "adr_refs": ["ADR-045"],
            "policy_refs": ["POL-WS-001"],
        },
    }


# =========================================================================
# C1 — Document type registration
# =========================================================================


class TestC1Registration:
    def test_handler_registered_in_registry(self):
        assert "work_statement" in HANDLERS

    def test_handler_doc_type_id(self, handler):
        assert handler.doc_type_id == "work_statement"

    def test_combine_config_entry_exists(self):
        ids = get_package_loader().list_document_types()
        assert "work_statement" in ids


# =========================================================================
# C2 — Parent required
# =========================================================================


class TestC2ParentRequired:
    def test_validate_rejects_missing_parent_wp_id(self, handler, ws_schema):
        data = {
            "ws_id": "WS-001",
            "title": "No Parent",
            "objective": "Test",
            "scope_in": [],
            "scope_out": [],
            "procedure": [],
            "verification_criteria": [],
            "prohibited_actions": [],
            "state": "DRAFT",
            "governance_pins": {},
        }
        is_valid, errors = handler.validate(data, ws_schema)
        assert is_valid is False
        assert any("parent_wp_id" in e for e in errors)

    def test_validate_rejects_null_parent_wp_id(self, handler, ws_schema):
        data = {
            "ws_id": "WS-001",
            "parent_wp_id": None,
            "title": "Null Parent",
            "objective": "Test",
            "scope_in": [],
            "scope_out": [],
            "procedure": [],
            "verification_criteria": [],
            "prohibited_actions": [],
            "state": "DRAFT",
            "governance_pins": {},
        }
        is_valid, errors = handler.validate(data, ws_schema)
        assert is_valid is False
        assert any("parent_wp_id" in e for e in errors)


# =========================================================================
# C3 — Parent must exist
# =========================================================================


class TestC3ParentMustExist:
    def test_validate_parent_exists_raises_on_none(self):
        with pytest.raises(ParentNotFoundError):
            validate_parent_exists(None)

    def test_validate_parent_exists_passes_on_dict(self):
        validate_parent_exists({"wp_id": "WP-001", "title": "Some WP"})


# =========================================================================
# C4 — WP rollup updated on registration
# =========================================================================


class TestC4WPRollupOnRegistration:
    def test_register_ws_increments_ws_total(self, wp_data):
        result = register_ws_on_wp(wp_data, "WS-001")
        assert result["ws_total"] == 1

    def test_register_ws_appends_to_child_refs(self, wp_data):
        result = register_ws_on_wp(wp_data, "WS-001")
        assert "WS-001" in result["ws_child_refs"]

    def test_register_ws_idempotent_on_duplicate(self, wp_data):
        result = register_ws_on_wp(wp_data, "WS-001")
        result = register_ws_on_wp(result, "WS-001")
        assert result["ws_total"] == 1
        assert result["ws_child_refs"].count("WS-001") == 1


# =========================================================================
# C5 — Valid lifecycle transitions accepted
# =========================================================================


class TestC5ValidTransitions:
    def test_valid_transition_draft_to_ready(self):
        assert validate_ws_transition("DRAFT", "READY") is True

    def test_valid_transition_ready_to_in_progress(self):
        assert validate_ws_transition("READY", "IN_PROGRESS") is True

    def test_valid_transition_in_progress_to_accepted(self):
        assert validate_ws_transition("IN_PROGRESS", "ACCEPTED") is True

    def test_valid_transition_in_progress_to_rejected(self):
        assert validate_ws_transition("IN_PROGRESS", "REJECTED") is True

    def test_valid_transition_in_progress_to_blocked(self):
        assert validate_ws_transition("IN_PROGRESS", "BLOCKED") is True

    def test_valid_transition_blocked_to_in_progress(self):
        assert validate_ws_transition("BLOCKED", "IN_PROGRESS") is True


# =========================================================================
# C6 — Invalid lifecycle transitions rejected
# =========================================================================


class TestC6InvalidTransitions:
    def test_invalid_transition_draft_to_accepted(self):
        with pytest.raises(InvalidWSTransitionError):
            validate_ws_transition("DRAFT", "ACCEPTED")

    def test_invalid_transition_accepted_to_any(self):
        with pytest.raises(InvalidWSTransitionError):
            validate_ws_transition("ACCEPTED", "DRAFT")

    def test_invalid_transition_rejected_to_any(self):
        with pytest.raises(InvalidWSTransitionError):
            validate_ws_transition("REJECTED", "DRAFT")


# =========================================================================
# C7 — Governance pins inherited
# =========================================================================


class TestC7GovernancePins:
    def test_inherit_pins_copies_from_wp(self, wp_data):
        ws_data = {"ws_id": "WS-001", "governance_pins": {}}
        result = inherit_governance_pins(ws_data, wp_data)
        assert result["governance_pins"] == wp_data["governance_pins"]

    def test_inherit_pins_empty_wp_gives_empty(self):
        ws_data = {"ws_id": "WS-001", "governance_pins": {}}
        wp_empty = {"wp_id": "WP-001", "governance_pins": {}}
        result = inherit_governance_pins(ws_data, wp_empty)
        assert result["governance_pins"] == {}


# =========================================================================
# C8 — WP progress reflects WS states
# =========================================================================


class TestC8WPProgress:
    def test_apply_ws_accepted_increments_ws_done(self, wp_data):
        wp_data["ws_total"] = 3
        wp_data["ws_done"] = 1
        result = apply_ws_accepted_to_wp(wp_data)
        assert result["ws_done"] == 2

    def test_ws_done_does_not_exceed_ws_total(self, wp_data):
        wp_data["ws_total"] = 2
        wp_data["ws_done"] = 2
        result = apply_ws_accepted_to_wp(wp_data)
        assert result["ws_done"] == 2
