"""Tests for production state model (ADR-043)."""

import pytest

from app.domain.workflow.production_state import (
    ProductionState,
    Station,
    InterruptType,
    map_node_outcome_to_state,
    map_station_from_node,
    STATE_DISPLAY_TEXT,
    STATION_DISPLAY_TEXT,
)


class TestProductionState:
    """Tests for ProductionState enum."""

    def test_all_states_defined(self):
        """All canonical states from ADR-043 are present."""
        expected = {
            "queued",
            "blocked",
            "binding",
            "assembling",
            "auditing",
            "remediating",
            "awaiting_operator",
            "stabilized",
            "halted",
            "escalated",
        }
        actual = {s.value for s in ProductionState}
        assert actual == expected

    def test_states_are_strings(self):
        """States are string enums for JSON serialization."""
        for state in ProductionState:
            assert isinstance(state.value, str)
            assert state == state.value  # str enum comparison

    def test_all_states_have_display_text(self):
        """Every state has user-facing display text."""
        for state in ProductionState:
            assert state in STATE_DISPLAY_TEXT
            assert isinstance(STATE_DISPLAY_TEXT[state], str)
            assert len(STATE_DISPLAY_TEXT[state]) > 0


class TestStation:
    """Tests for Station enum."""

    def test_all_stations_defined(self):
        """All canonical stations from ADR-043 are present."""
        expected = {"bind", "asm", "aud", "rem"}
        actual = {s.value for s in Station}
        assert actual == expected

    def test_all_stations_have_display_text(self):
        """Every station has user-facing display text."""
        for station in Station:
            assert station in STATION_DISPLAY_TEXT


class TestInterruptType:
    """Tests for InterruptType enum."""

    def test_all_interrupt_types_defined(self):
        """All interrupt types from ADR-043 are present."""
        expected = {
            "clarification_required",
            "audit_review",
            "constraint_conflict",
        }
        actual = {t.value for t in InterruptType}
        assert actual == expected


class TestMapNodeOutcomeToState:
    """Tests for legacy outcome to state mapping."""

    def test_pgc_needs_input_maps_to_awaiting_operator(self):
        """PGC needing input = awaiting operator."""
        result = map_node_outcome_to_state("pgc", "needs_user_input")
        assert result == ProductionState.AWAITING_OPERATOR

    def test_task_success_maps_to_auditing(self):
        """Task success = ready for audit."""
        result = map_node_outcome_to_state("task", "success", is_terminal=False)
        assert result == ProductionState.AUDITING

    def test_task_success_terminal_maps_to_stabilized(self):
        """Task success at terminal = stabilized."""
        result = map_node_outcome_to_state("task", "success", is_terminal=True)
        assert result == ProductionState.STABILIZED

    def test_qa_failed_maps_to_remediating(self):
        """QA failure = remediating."""
        result = map_node_outcome_to_state("qa", "failed")
        assert result == ProductionState.REMEDIATING

    def test_qa_success_terminal_maps_to_stabilized(self):
        """QA success at terminal = stabilized."""
        result = map_node_outcome_to_state("qa", "success", is_terminal=True)
        assert result == ProductionState.STABILIZED

    def test_legacy_pending_maps_to_queued(self):
        """Legacy 'pending' = queued."""
        result = map_node_outcome_to_state("unknown", "pending")
        assert result == ProductionState.QUEUED

    def test_legacy_paused_maps_to_awaiting_operator(self):
        """Legacy 'paused' = awaiting operator."""
        result = map_node_outcome_to_state("unknown", "paused")
        assert result == ProductionState.AWAITING_OPERATOR

    def test_legacy_failed_maps_to_halted(self):
        """Legacy 'failed' = halted."""
        result = map_node_outcome_to_state("unknown", "failed")
        assert result == ProductionState.HALTED


class TestMapStationFromNode:
    """Tests for node to station mapping."""

    def test_pgc_maps_to_bind(self):
        """PGC node = bind station."""
        result = map_station_from_node("pgc", "pgc")
        assert result == Station.BIND

    def test_task_maps_to_asm(self):
        """Task node = asm station."""
        result = map_station_from_node("task", "generation")
        assert result == Station.ASM

    def test_remediation_task_maps_to_rem(self):
        """Remediation task = rem station."""
        result = map_station_from_node("task", "remediation")
        assert result == Station.REM

    def test_qa_maps_to_aud(self):
        """QA node = aud station."""
        result = map_station_from_node("qa", "qa")
        assert result == Station.AUD
