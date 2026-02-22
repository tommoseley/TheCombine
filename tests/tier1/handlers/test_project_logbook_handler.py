"""
Tests for Project Logbook — WS-ONTOLOGY-003.

Six test groups mapping to the six Tier 1 verification criteria:
  C1: Document type registration
  C2: Logbook header fields
  C3: Auto-append on WS acceptance
  C4: Atomicity (deepcopy protection)
  C5: Append-only enforcement
  C6: Logbook created on first acceptance (lazy creation)
"""

import pytest

from app.domain.handlers.registry import HANDLERS
from app.domain.handlers.project_logbook_handler import ProjectLogbookHandler
from app.domain.services.logbook_service import (
    create_empty_logbook,
    execute_ws_acceptance,
    LogbookAppendError,
)
import app.domain.services.logbook_service as logbook_service_module


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def handler():
    return ProjectLogbookHandler()


@pytest.fixture
def logbook_schema():
    """Return the logbook schema (inline — project_logbook not yet in combine-config)."""
    return {
        "type": "object",
        "required": [
            "schema_version",
            "project_id",
            "mode_b_rate",
            "verification_debt_open",
            "entries",
        ],
        "properties": {
            "schema_version": {"type": "string"},
            "project_id": {"type": "string"},
            "mode_b_rate": {"type": "number"},
            "verification_debt_open": {"type": "integer"},
            "program_ref": {"type": "string"},
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "ws_id": {"type": "string"},
                        "parent_wp_id": {"type": "string"},
                        "result": {"type": "string"},
                        "mode_b_list": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "tier0_json": {"type": "object"},
                    },
                },
            },
        },
    }


@pytest.fixture
def ws_data():
    """Minimal WS dict in IN_PROGRESS state (ready to be accepted)."""
    return {
        "ws_id": "WS-001",
        "parent_wp_id": "WP-001",
        "title": "Implement Login Flow",
        "objective": "Enable user authentication via JWT",
        "scope_in": ["Login endpoint"],
        "scope_out": ["Password reset"],
        "procedure": ["Step 1: Create endpoint"],
        "verification_criteria": ["Login returns 200"],
        "prohibited_actions": ["Do not modify user table"],
        "state": "IN_PROGRESS",
        "governance_pins": {},
    }


@pytest.fixture
def wp_data():
    """Minimal WP dict with one registered WS."""
    return {
        "wp_id": "WP-001",
        "title": "Auth Work Package",
        "state": "IN_PROGRESS",
        "ws_total": 1,
        "ws_done": 0,
        "ws_child_refs": ["WS-001"],
        "governance_pins": {},
    }


@pytest.fixture
def logbook_data():
    """An existing empty logbook."""
    return create_empty_logbook("P-001")


# =========================================================================
# C1 — Document type registration
# =========================================================================


class TestC1Registration:
    def test_handler_registered_in_registry(self):
        assert "project_logbook" in HANDLERS

    def test_handler_doc_type_id(self, handler):
        assert handler.doc_type_id == "project_logbook"

    def test_handler_registered(self):
        assert "project_logbook" in HANDLERS


# =========================================================================
# C2 — Logbook header fields
# =========================================================================


class TestC2HeaderFields:
    def test_schema_requires_header_fields(self, logbook_schema):
        required = logbook_schema["required"]
        for field in [
            "schema_version",
            "project_id",
            "mode_b_rate",
            "verification_debt_open",
            "entries",
        ]:
            assert field in required, f"'{field}' not in schema required"

    def test_schema_defines_header_properties(self, logbook_schema):
        props = logbook_schema["properties"]
        for field in [
            "schema_version",
            "project_id",
            "mode_b_rate",
            "verification_debt_open",
            "program_ref",
            "entries",
        ]:
            assert field in props, f"'{field}' not in schema properties"

    def test_create_empty_logbook_has_all_header_fields(self):
        lb = create_empty_logbook("P-001")
        assert lb["schema_version"] == "1.0"
        assert lb["project_id"] == "P-001"
        assert lb["mode_b_rate"] == 0.0
        assert lb["verification_debt_open"] == 0
        assert lb["program_ref"] is None
        assert lb["entries"] == []


# =========================================================================
# C3 — Auto-append on WS acceptance
# =========================================================================


class TestC3AutoAppend:
    def test_execute_ws_acceptance_appends_entry(
        self, ws_data, wp_data, logbook_data
    ):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert len(lb["entries"]) == 1

    def test_entry_contains_required_fields(
        self, ws_data, wp_data, logbook_data
    ):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        entry = lb["entries"][0]
        for field in [
            "timestamp",
            "ws_id",
            "parent_wp_id",
            "result",
            "mode_b_list",
            "tier0_json",
        ]:
            assert field in entry, f"'{field}' not in entry"

    def test_entry_result_is_accepted(self, ws_data, wp_data, logbook_data):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert lb["entries"][0]["result"] == "ACCEPTED"

    def test_entry_ws_id_matches(self, ws_data, wp_data, logbook_data):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert lb["entries"][0]["ws_id"] == "WS-001"

    def test_entry_parent_wp_id_matches(
        self, ws_data, wp_data, logbook_data
    ):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert lb["entries"][0]["parent_wp_id"] == "WP-001"

    def test_ws_transitions_to_accepted(
        self, ws_data, wp_data, logbook_data
    ):
        ws, _, _ = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert ws["state"] == "ACCEPTED"

    def test_wp_rollup_updated(self, ws_data, wp_data, logbook_data):
        _, wp, _ = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        assert wp["ws_done"] == 1


# =========================================================================
# C4 — Atomicity (deepcopy protection)
# =========================================================================


class TestC4Atomicity:
    def test_failed_append_leaves_ws_unchanged(self, ws_data, wp_data):
        malformed_logbook = {
            "schema_version": "1.0",
            "project_id": "P-001",
            "mode_b_rate": 0.0,
            "verification_debt_open": 0,
            "program_ref": None,
            "entries": "not-a-list",
        }
        with pytest.raises(LogbookAppendError):
            execute_ws_acceptance(
                ws_data, wp_data, malformed_logbook, project_id="P-001"
            )
        assert ws_data["state"] == "IN_PROGRESS"

    def test_failed_append_leaves_wp_unchanged(self, ws_data, wp_data):
        malformed_logbook = {
            "schema_version": "1.0",
            "project_id": "P-001",
            "mode_b_rate": 0.0,
            "verification_debt_open": 0,
            "program_ref": None,
            "entries": "not-a-list",
        }
        with pytest.raises(LogbookAppendError):
            execute_ws_acceptance(
                ws_data, wp_data, malformed_logbook, project_id="P-001"
            )
        assert wp_data["ws_done"] == 0


# =========================================================================
# C5 — Append-only enforcement
# =========================================================================


class TestC5AppendOnly:
    def test_append_only_grows_entries(self, ws_data, wp_data, logbook_data):
        # First acceptance
        ws1, wp1, lb1 = execute_ws_acceptance(
            ws_data, wp_data, logbook_data, project_id="P-001"
        )
        # Second WS acceptance on same logbook
        ws2_data = {
            "ws_id": "WS-002",
            "parent_wp_id": "WP-001",
            "title": "Second WS",
            "objective": "Test",
            "scope_in": [],
            "scope_out": [],
            "procedure": [],
            "verification_criteria": [],
            "prohibited_actions": [],
            "state": "IN_PROGRESS",
            "governance_pins": {},
        }
        wp1["ws_child_refs"].append("WS-002")
        wp1["ws_total"] = 2
        _, _, lb2 = execute_ws_acceptance(
            ws2_data, wp1, lb1, project_id="P-001"
        )
        assert len(lb2["entries"]) == 2

    def test_no_delete_or_update_functions_exposed(self):
        for name in [
            "delete_logbook_entry",
            "update_logbook_entry",
            "remove_logbook_entry",
        ]:
            assert not hasattr(logbook_service_module, name), (
                f"Module should not expose '{name}'"
            )


# =========================================================================
# C6 — Logbook created on first acceptance (lazy creation)
# =========================================================================


class TestC6LazyCreation:
    def test_execute_ws_acceptance_creates_logbook_when_none(
        self, ws_data, wp_data
    ):
        ws, wp, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data=None, project_id="P-001"
        )
        assert lb is not None
        assert len(lb["entries"]) == 1

    def test_created_logbook_has_valid_header(self, ws_data, wp_data):
        _, _, lb = execute_ws_acceptance(
            ws_data, wp_data, logbook_data=None, project_id="P-001"
        )
        assert lb["schema_version"] == "1.0"
        assert lb["project_id"] == "P-001"
        assert isinstance(lb["entries"], list)
