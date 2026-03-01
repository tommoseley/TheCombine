"""Tier-1 tests for service_pure.py.

Pure data transformation tests -- no DB, no I/O, no filesystem.
Covers: qa_coverage, dashboard, cost, transcript, mechanical_ops.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.api.services.service_pure import (
    aggregate_daily_costs,
    build_constraint_lookup,
    build_operation_summary,
    build_transcript_entry,
    compute_dashboard_stats,
    compute_transcript_totals,
    format_execution_dates,
    format_transcript_timestamps,
    process_qa_nodes,
    sort_key_datetime,
)


# =========================================================================
# QA Coverage: build_constraint_lookup
# =========================================================================


class TestBuildConstraintLookup:
    """Tests for build_constraint_lookup."""

    def test_empty_invariants(self):
        assert build_constraint_lookup([]) == {}

    def test_single_invariant(self):
        inv = [
            {
                "id": "C1",
                "text": "Must be secure",
                "user_answer_label": "Yes",
                "binding_source": "intake",
                "priority": "high",
            }
        ]
        result = build_constraint_lookup(inv)
        assert "C1" in result
        assert result["C1"]["question"] == "Must be secure"
        assert result["C1"]["answer"] == "Yes"
        assert result["C1"]["source"] == "intake"
        assert result["C1"]["priority"] == "high"

    def test_missing_id_skipped(self):
        inv = [{"text": "No ID constraint"}]
        assert build_constraint_lookup(inv) == {}

    def test_user_answer_fallback(self):
        inv = [{"id": "C2", "user_answer": True}]
        result = build_constraint_lookup(inv)
        assert result["C2"]["answer"] == "True"

    def test_user_answer_label_takes_priority(self):
        inv = [{"id": "C3", "user_answer_label": "Custom", "user_answer": True}]
        result = build_constraint_lookup(inv)
        assert result["C3"]["answer"] == "Custom"

    def test_multiple_invariants(self):
        inv = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        result = build_constraint_lookup(inv)
        assert len(result) == 3

    def test_missing_fields_default_empty(self):
        inv = [{"id": "C4"}]
        result = build_constraint_lookup(inv)
        assert result["C4"]["question"] == ""
        assert result["C4"]["source"] == ""
        assert result["C4"]["priority"] == ""


# =========================================================================
# QA Coverage: process_qa_nodes
# =========================================================================


class TestProcessQaNodes:
    """Tests for process_qa_nodes."""

    def test_empty_log(self):
        processed, summary = process_qa_nodes([])
        assert processed == []
        assert summary["total_checks"] == 0

    def test_non_qa_nodes_filtered(self):
        log = [
            {"node_id": "pgc_check", "outcome": "success"},
            {"node_id": "assembly", "outcome": "success"},
        ]
        processed, summary = process_qa_nodes(log)
        assert processed == []
        assert summary["total_checks"] == 0

    def test_qa_node_identified(self):
        log = [
            {"node_id": "qa_audit", "outcome": "success", "metadata": {}},
        ]
        processed, summary = process_qa_nodes(log)
        assert len(processed) == 1
        assert summary["total_checks"] == 1
        assert summary["passed"] == 1
        assert summary["failed"] == 0

    def test_qa_node_failed(self):
        log = [
            {"node_id": "qa_check", "outcome": "failed", "metadata": {}},
        ]
        processed, summary = process_qa_nodes(log)
        assert summary["total_checks"] == 1
        assert summary["passed"] == 0
        assert summary["failed"] == 1

    def test_semantic_report_coverage(self):
        log = [
            {
                "node_id": "qa_audit",
                "outcome": "success",
                "metadata": {
                    "semantic_qa_report": {
                        "summary": {"errors": 2, "warnings": 1},
                        "coverage": {
                            "items": [
                                {"status": "satisfied"},
                                {"status": "missing"},
                                {"status": "contradicted"},
                                {"status": "reopened"},
                                {"status": "unknown"},
                            ]
                        },
                        "findings": [{"id": "f1"}],
                    }
                },
            }
        ]
        processed, summary = process_qa_nodes(log)
        assert summary["total_errors"] == 2
        assert summary["total_warnings"] == 1
        assert summary["total_constraints"] == 5
        assert summary["satisfied"] == 1
        assert summary["missing"] == 1
        assert summary["contradicted"] == 1
        assert summary["reopened"] == 1
        assert summary["not_evaluated"] == 1
        assert len(processed[0]["findings"]) == 1

    def test_drift_and_validation_metadata(self):
        log = [
            {
                "node_id": "qa_check",
                "outcome": "success",
                "metadata": {
                    "drift_errors": ["err1"],
                    "drift_warnings": ["warn1"],
                    "code_validation_warnings": ["cw1"],
                    "validation_errors": ["ve1"],
                },
            }
        ]
        processed, _ = process_qa_nodes(log)
        assert processed[0]["drift_errors"] == ["err1"]
        assert processed[0]["drift_warnings"] == ["warn1"]
        assert processed[0]["code_validation_warnings"] == ["cw1"]
        assert processed[0]["code_validation_errors"] == ["ve1"]

    def test_qa_passed_from_metadata(self):
        log = [
            {
                "node_id": "qa_node",
                "outcome": "success",
                "metadata": {"qa_passed": False},
            }
        ]
        processed, _ = process_qa_nodes(log)
        assert processed[0]["qa_passed"] is False

    def test_qa_passed_defaults_from_outcome(self):
        log = [
            {"node_id": "qa_node", "outcome": "success", "metadata": {}},
        ]
        processed, _ = process_qa_nodes(log)
        assert processed[0]["qa_passed"] is True


# =========================================================================
# Dashboard: sort_key_datetime
# =========================================================================


class TestSortKeyDatetime:
    """Tests for sort_key_datetime."""

    def test_none_started_at(self):
        result = sort_key_datetime({})
        assert result == datetime.min.replace(tzinfo=timezone.utc)

    def test_datetime_object(self):
        dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        result = sort_key_datetime({"started_at": dt})
        assert result == dt

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2026, 1, 15, 12, 0)
        result = sort_key_datetime({"started_at": dt})
        assert result.tzinfo == timezone.utc

    def test_iso_string(self):
        result = sort_key_datetime({"started_at": "2026-01-15T12:00:00Z"})
        assert result.year == 2026
        assert result.month == 1

    def test_invalid_string(self):
        result = sort_key_datetime({"started_at": "not-a-date"})
        assert result == datetime.min.replace(tzinfo=timezone.utc)


# =========================================================================
# Dashboard: format_execution_dates
# =========================================================================


class TestFormatExecutionDates:
    """Tests for format_execution_dates."""

    def test_formats_aware_datetime(self):
        dt = datetime(2026, 1, 15, 17, 30, tzinfo=timezone.utc)
        execs = [{"started_at": dt}]
        result = format_execution_dates(execs, ZoneInfo("America/New_York"))
        assert result[0]["started_at_formatted"] == "2026-01-15 12:30"
        assert result[0]["started_at_iso"] is not None

    def test_formats_naive_datetime(self):
        dt = datetime(2026, 1, 15, 17, 30)
        execs = [{"started_at": dt}]
        result = format_execution_dates(execs, ZoneInfo("UTC"))
        assert result[0]["started_at_formatted"] == "2026-01-15 17:30"

    def test_none_started_at(self):
        execs = [{"started_at": None}]
        result = format_execution_dates(execs, ZoneInfo("UTC"))
        assert result[0]["started_at_formatted"] is None
        assert result[0]["started_at_iso"] is None

    def test_multiple_entries(self):
        execs = [
            {"started_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)},
            {"started_at": None},
        ]
        result = format_execution_dates(execs, ZoneInfo("UTC"))
        assert result[0]["started_at_formatted"] is not None
        assert result[1]["started_at_formatted"] is None


# =========================================================================
# Dashboard: compute_dashboard_stats
# =========================================================================


class TestComputeDashboardStats:
    """Tests for compute_dashboard_stats."""

    def test_all_zeros(self):
        result = compute_dashboard_stats(0, 0, 0, 0)
        assert result == {
            "total_workflows": 0,
            "running_executions": 0,
            "waiting_action": 0,
            "doc_builds_today": 0,
        }

    def test_values_preserved(self):
        result = compute_dashboard_stats(5, 2, 3, 10)
        assert result["total_workflows"] == 5
        assert result["running_executions"] == 2
        assert result["waiting_action"] == 3
        assert result["doc_builds_today"] == 10


# =========================================================================
# Cost: aggregate_daily_costs
# =========================================================================


class TestAggregateDailyCosts:
    """Tests for aggregate_daily_costs."""

    def test_empty_totals(self):
        today = date(2026, 2, 15)
        daily_data, summary = aggregate_daily_costs({}, today, 3)
        assert len(daily_data) == 3
        assert all(d["cost"] == 0.0 for d in daily_data)
        assert summary["total_cost"] == 0.0
        assert summary["total_calls"] == 0
        assert summary["success_rate"] == 100

    def test_single_day(self):
        today = date(2026, 2, 15)
        totals = {
            "2026-02-15": {
                "cost": 1.5,
                "tokens": 1000,
                "calls": 5,
                "errors": 1,
                "workflow_cost": 1.0,
                "document_cost": 0.5,
            }
        }
        daily_data, summary = aggregate_daily_costs(totals, today, 1)
        assert len(daily_data) == 1
        assert daily_data[0]["cost"] == 1.5
        assert daily_data[0]["date"] == "2026-02-15"
        assert daily_data[0]["date_short"] == "02/15"
        assert summary["total_cost"] == 1.5
        assert summary["total_tokens"] == 1000
        assert summary["total_calls"] == 5
        assert summary["total_errors"] == 1
        assert summary["avg_cost_per_day"] == 1.5
        assert summary["success_rate"] == 80.0

    def test_chronological_order(self):
        today = date(2026, 2, 15)
        totals = {
            "2026-02-14": {
                "cost": 1.0, "tokens": 500, "calls": 2, "errors": 0,
                "workflow_cost": 1.0, "document_cost": 0.0,
            },
            "2026-02-15": {
                "cost": 2.0, "tokens": 800, "calls": 3, "errors": 0,
                "workflow_cost": 2.0, "document_cost": 0.0,
            },
        }
        daily_data, summary = aggregate_daily_costs(totals, today, 2)
        assert daily_data[0]["date"] == "2026-02-14"
        assert daily_data[1]["date"] == "2026-02-15"

    def test_avg_cost_per_call_zero_calls(self):
        today = date(2026, 2, 15)
        _, summary = aggregate_daily_costs({}, today, 1)
        assert summary["avg_cost_per_call"] == 0

    def test_success_rate_calculation(self):
        today = date(2026, 2, 15)
        totals = {
            "2026-02-15": {
                "cost": 0, "tokens": 0, "calls": 10, "errors": 3,
                "workflow_cost": 0, "document_cost": 0,
            }
        }
        _, summary = aggregate_daily_costs(totals, today, 1)
        assert summary["success_rate"] == 70.0

    def test_missing_day_uses_defaults(self):
        today = date(2026, 2, 15)
        totals = {
            "2026-02-14": {
                "cost": 5.0, "tokens": 2000, "calls": 10, "errors": 0,
                "workflow_cost": 5.0, "document_cost": 0,
            },
        }
        daily_data, _ = aggregate_daily_costs(totals, today, 2)
        assert daily_data[1]["cost"] == 0.0  # 2026-02-15 has no data


# =========================================================================
# Transcript: build_transcript_entry
# =========================================================================


class TestBuildTranscriptEntry:
    """Tests for build_transcript_entry."""

    def test_basic_entry(self):
        tz = ZoneInfo("America/New_York")
        started = datetime(2026, 1, 15, 17, 30, 0, tzinfo=timezone.utc)
        ended = datetime(2026, 1, 15, 17, 30, 5, tzinfo=timezone.utc)

        result = build_transcript_entry(
            run_number=1,
            run_id="abcdef12-3456-7890-abcd-ef1234567890",
            role="business_analyst",
            prompt_id="task:charter",
            node_id="assembly",
            prompt_sources={"task": "v1"},
            model_name="claude-3",
            status="SUCCESS",
            started_at=started,
            ended_at=ended,
            total_tokens=1500,
            cost_usd=0.05,
            inputs=[{"kind": "task", "content": "...", "size": 100}],
            outputs=[{"kind": "response", "content": "...", "size": 200}],
            display_tz=tz,
        )
        assert result["run_number"] == 1
        assert result["run_id_short"] == "abcdef12"
        assert result["role"] == "business_analyst"
        assert result["duration"] == "5.0s"
        assert result["duration_seconds"] == 5.0
        assert result["tokens"] == 1500
        assert result["cost"] == 0.05
        assert result["started_at_time"] is not None
        assert result["started_at_iso"] is not None

    def test_no_timestamps(self):
        tz = ZoneInfo("UTC")
        result = build_transcript_entry(
            run_number=1,
            run_id="abcdef12",
            role=None,
            prompt_id=None,
            node_id=None,
            prompt_sources=None,
            model_name=None,
            status=None,
            started_at=None,
            ended_at=None,
            total_tokens=None,
            cost_usd=None,
            inputs=[],
            outputs=[],
            display_tz=tz,
        )
        assert result["duration"] is None
        assert result["duration_seconds"] is None
        assert result["started_at_time"] is None
        assert result["started_at_iso"] is None
        assert result["cost"] is None
        assert result["tokens"] is None

    def test_started_but_no_ended(self):
        tz = ZoneInfo("UTC")
        started = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = build_transcript_entry(
            run_number=1,
            run_id="abcdef12",
            role=None,
            prompt_id=None,
            node_id=None,
            prompt_sources=None,
            model_name=None,
            status=None,
            started_at=started,
            ended_at=None,
            total_tokens=None,
            cost_usd=None,
            inputs=[],
            outputs=[],
            display_tz=tz,
        )
        assert result["duration"] is None
        assert result["started_at_time"] is not None


# =========================================================================
# Transcript: compute_transcript_totals
# =========================================================================


class TestComputeTranscriptTotals:
    """Tests for compute_transcript_totals."""

    def test_empty_entries(self):
        tokens, cost = compute_transcript_totals([])
        assert tokens == 0
        assert cost == 0.0

    def test_sums_tokens_and_cost(self):
        entries = [
            {"tokens": 100, "cost": 0.01},
            {"tokens": 200, "cost": 0.02},
        ]
        tokens, cost = compute_transcript_totals(entries)
        assert tokens == 300
        assert cost == pytest.approx(0.03)

    def test_none_tokens_skipped(self):
        entries = [
            {"tokens": 100, "cost": 0.01},
            {"tokens": None, "cost": None},
        ]
        tokens, cost = compute_transcript_totals(entries)
        assert tokens == 100
        assert cost == pytest.approx(0.01)

    def test_zero_cost(self):
        entries = [{"tokens": 0, "cost": 0.0}]
        tokens, cost = compute_transcript_totals(entries)
        assert tokens == 0
        assert cost == 0.0


# =========================================================================
# Transcript: format_transcript_timestamps
# =========================================================================


class TestFormatTranscriptTimestamps:
    """Tests for format_transcript_timestamps."""

    def test_both_timestamps(self):
        tz = ZoneInfo("America/New_York")
        started = datetime(2026, 1, 15, 17, 30, 0, tzinfo=timezone.utc)
        ended = datetime(2026, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
        result = format_transcript_timestamps(started, ended, tz)
        assert result["started_at_formatted"] is not None
        assert result["ended_at_formatted"] is not None
        assert result["started_at_iso"] is not None
        assert result["ended_at_iso"] is not None

    def test_no_timestamps(self):
        tz = ZoneInfo("UTC")
        result = format_transcript_timestamps(None, None, tz)
        assert result["started_at_formatted"] is None
        assert result["ended_at_formatted"] is None

    def test_only_started(self):
        tz = ZoneInfo("UTC")
        started = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = format_transcript_timestamps(started, None, tz)
        assert result["started_at_formatted"] is not None
        assert result["ended_at_formatted"] is None


# =========================================================================
# Mechanical Ops: build_operation_summary
# =========================================================================


class TestBuildOperationSummary:
    """Tests for build_operation_summary."""

    def test_full_summary(self):
        result = build_operation_summary(
            op_id="schema_validate",
            op_name="Schema Validation",
            op_description="Validates JSON against schema",
            op_type="validator",
            op_metadata={"tags": ["validation", "json"]},
            type_name="Validator",
            type_category="quality",
            active_version="1.0.0",
        )
        assert result["op_id"] == "schema_validate"
        assert result["name"] == "Schema Validation"
        assert result["type"] == "validator"
        assert result["type_name"] == "Validator"
        assert result["category"] == "quality"
        assert result["active_version"] == "1.0.0"
        assert result["tags"] == ["validation", "json"]

    def test_none_type_name_falls_back_to_type(self):
        result = build_operation_summary(
            op_id="test",
            op_name="Test",
            op_description="",
            op_type="unknown_type",
            op_metadata={},
            type_name=None,
            type_category=None,
            active_version="1.0.0",
        )
        assert result["type_name"] == "unknown_type"
        assert result["category"] == "uncategorized"

    def test_empty_metadata_tags(self):
        result = build_operation_summary(
            op_id="test",
            op_name="Test",
            op_description="",
            op_type="t",
            op_metadata={},
            type_name="T",
            type_category="c",
            active_version="1.0.0",
        )
        assert result["tags"] == []
