"""Tests for state_mapping pure functions.

Extracted from pg_state_persistence._row_to_state() per WS-CRAP-007.
Tier-1: in-memory, no DB.
"""

import json
import os
import sys
import types
from datetime import datetime

import pytest

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.state_mapping import (  # noqa: E402
    build_node_history,
    derive_timestamps,
    parse_json_field,
    row_dict_to_state,
)
from app.domain.workflow.document_workflow_state import (  # noqa: E402
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)


# ---------------------------------------------------------------------------
# parse_json_field
# ---------------------------------------------------------------------------


class TestParseJsonField:
    """Tests for parse_json_field."""

    def test_none_returns_default(self):
        assert parse_json_field(None, []) == []
        assert parse_json_field(None, {}) == {}

    def test_empty_string_returns_default(self):
        assert parse_json_field("", {}) == {}

    def test_already_parsed_dict(self):
        d = {"key": "value"}
        assert parse_json_field(d, {}) is d

    def test_already_parsed_list(self):
        lst = [1, 2, 3]
        assert parse_json_field(lst, []) is lst

    def test_json_string_dict(self):
        result = parse_json_field('{"a": 1}', {})
        assert result == {"a": 1}

    def test_json_string_list(self):
        result = parse_json_field('[1, 2]', [])
        assert result == [1, 2]

    def test_default_for_none_with_none_default(self):
        assert parse_json_field(None, None) is None


# ---------------------------------------------------------------------------
# build_node_history
# ---------------------------------------------------------------------------


class TestBuildNodeHistory:
    """Tests for build_node_history."""

    def test_empty_log(self):
        assert build_node_history([]) == []

    def test_single_entry(self):
        entries = [
            {
                "node_id": "gen_1",
                "outcome": "success",
                "timestamp": "2026-01-15T10:00:00+00:00",
                "metadata": {"tokens": 500},
            }
        ]
        result = build_node_history(entries)
        assert len(result) == 1
        assert isinstance(result[0], NodeExecution)
        assert result[0].node_id == "gen_1"
        assert result[0].outcome == "success"
        assert result[0].metadata == {"tokens": 500}

    def test_multiple_entries(self):
        entries = [
            {
                "node_id": "pgc_gate",
                "outcome": "qualified",
                "timestamp": "2026-01-15T10:00:00+00:00",
            },
            {
                "node_id": "gen_1",
                "outcome": "success",
                "timestamp": "2026-01-15T10:05:00+00:00",
            },
        ]
        result = build_node_history(entries)
        assert len(result) == 2
        assert result[0].node_id == "pgc_gate"
        assert result[1].node_id == "gen_1"

    def test_missing_metadata_defaults_to_empty(self):
        entries = [
            {
                "node_id": "node_1",
                "outcome": "ok",
                "timestamp": "2026-01-15T10:00:00+00:00",
            }
        ]
        result = build_node_history(entries)
        assert result[0].metadata == {}


# ---------------------------------------------------------------------------
# derive_timestamps
# ---------------------------------------------------------------------------


class TestDeriveTimestamps:
    """Tests for derive_timestamps."""

    def test_empty_log_returns_utc_now(self):
        created, updated = derive_timestamps([])
        # Should be close to now
        assert created.tzinfo is not None or created.year >= 2026
        assert created == updated

    def test_single_entry(self):
        log = [{"timestamp": "2026-01-15T10:00:00+00:00"}]
        created, updated = derive_timestamps(log)
        assert created == datetime.fromisoformat("2026-01-15T10:00:00+00:00")
        assert updated == created

    def test_multiple_entries(self):
        log = [
            {"timestamp": "2026-01-15T10:00:00+00:00"},
            {"timestamp": "2026-01-15T11:00:00+00:00"},
            {"timestamp": "2026-01-15T12:00:00+00:00"},
        ]
        created, updated = derive_timestamps(log)
        assert created == datetime.fromisoformat("2026-01-15T10:00:00+00:00")
        assert updated == datetime.fromisoformat("2026-01-15T12:00:00+00:00")


# ---------------------------------------------------------------------------
# row_dict_to_state
# ---------------------------------------------------------------------------


class TestRowDictToState:
    """Tests for row_dict_to_state."""

    @pytest.fixture
    def minimal_row(self):
        return {
            "execution_id": "exec-001",
            "document_id": "proj-123",
            "document_type": "project_discovery",
            "workflow_id": "wf-disc-1",
            "user_id": None,
            "current_node_id": "gen_1",
            "status": "running",
            "execution_log": [],
            "retry_counts": {},
            "gate_outcome": None,
            "terminal_outcome": None,
            "thread_id": None,
            "context_state": {},
            "pending_user_input": False,
            "pending_user_input_rendered": None,
            "pending_choices": None,
            "pending_user_input_payload": None,
            "pending_user_input_schema_ref": None,
        }

    def test_minimal_row(self, minimal_row):
        state = row_dict_to_state(minimal_row)
        assert isinstance(state, DocumentWorkflowState)
        assert state.execution_id == "exec-001"
        assert state.project_id == "proj-123"
        assert state.document_type == "project_discovery"
        assert state.workflow_id == "wf-disc-1"
        assert state.status == DocumentWorkflowStatus.RUNNING
        assert state.node_history == []
        assert state.retry_counts == {}

    def test_with_execution_log(self, minimal_row):
        minimal_row["execution_log"] = [
            {
                "node_id": "pgc_gate",
                "outcome": "qualified",
                "timestamp": "2026-01-15T10:00:00+00:00",
                "metadata": {},
            },
            {
                "node_id": "gen_1",
                "outcome": "success",
                "timestamp": "2026-01-15T10:05:00+00:00",
                "metadata": {"tokens": 1000},
            },
        ]
        state = row_dict_to_state(minimal_row)
        assert len(state.node_history) == 2
        assert state.node_history[0].node_id == "pgc_gate"
        assert state.created_at == datetime.fromisoformat("2026-01-15T10:00:00+00:00")
        assert state.updated_at == datetime.fromisoformat("2026-01-15T10:05:00+00:00")

    def test_json_string_fields(self, minimal_row):
        """Fields that come as JSON strings should be parsed."""
        minimal_row["execution_log"] = json.dumps([])
        minimal_row["retry_counts"] = json.dumps({"gen_1": 2})
        minimal_row["context_state"] = json.dumps({"intake_summary": "test"})
        minimal_row["pending_choices"] = json.dumps(["yes", "no"])

        state = row_dict_to_state(minimal_row)
        assert state.retry_counts == {"gen_1": 2}
        assert state.context_state == {"intake_summary": "test"}
        assert state.pending_choices == ["yes", "no"]

    def test_null_document_id_defaults_to_unknown(self, minimal_row):
        minimal_row["document_id"] = None
        state = row_dict_to_state(minimal_row)
        assert state.project_id == "unknown"

    def test_null_document_type_defaults_to_unknown(self, minimal_row):
        minimal_row["document_type"] = None
        state = row_dict_to_state(minimal_row)
        assert state.document_type == "unknown"

    def test_null_workflow_id_defaults_to_unknown(self, minimal_row):
        minimal_row["workflow_id"] = None
        state = row_dict_to_state(minimal_row)
        assert state.workflow_id == "unknown"

    def test_null_status_defaults_to_running(self, minimal_row):
        minimal_row["status"] = None
        state = row_dict_to_state(minimal_row)
        assert state.status == DocumentWorkflowStatus.RUNNING

    def test_completed_status(self, minimal_row):
        minimal_row["status"] = "completed"
        state = row_dict_to_state(minimal_row)
        assert state.status == DocumentWorkflowStatus.COMPLETED

    def test_user_id_stringified(self, minimal_row):
        minimal_row["user_id"] = 42
        state = row_dict_to_state(minimal_row)
        assert state.user_id == "42"

    def test_pending_user_input_false_when_none(self, minimal_row):
        minimal_row["pending_user_input"] = None
        state = row_dict_to_state(minimal_row)
        assert state.pending_user_input is False

    def test_gate_outcome_preserved(self, minimal_row):
        minimal_row["gate_outcome"] = "approved"
        state = row_dict_to_state(minimal_row)
        assert state.gate_outcome == "approved"

    def test_terminal_outcome_preserved(self, minimal_row):
        minimal_row["terminal_outcome"] = "stabilized"
        state = row_dict_to_state(minimal_row)
        assert state.terminal_outcome == "stabilized"

    def test_thread_id_preserved(self, minimal_row):
        minimal_row["thread_id"] = "thread-abc"
        state = row_dict_to_state(minimal_row)
        assert state.thread_id == "thread-abc"

    def test_pending_user_input_payload_preserved(self, minimal_row):
        payload = {"questions": [{"id": "Q1", "text": "What?"}]}
        minimal_row["pending_user_input_payload"] = payload
        state = row_dict_to_state(minimal_row)
        assert state.pending_user_input_payload == payload

    def test_pending_user_input_schema_ref_preserved(self, minimal_row):
        minimal_row["pending_user_input_schema_ref"] = "pgc_questions.v1"
        state = row_dict_to_state(minimal_row)
        assert state.pending_user_input_schema_ref == "pgc_questions.v1"
