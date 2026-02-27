"""Tests for production state model (ADR-043)."""


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
            "ready_for_production",
            "requirements_not_met",
            "in_production",
            "awaiting_operator",
            "produced",
            "halted",
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
        """All canonical stations from WS-SUBWAY-MAP-001 Phase 2 are present."""
        expected = {"pgc", "asm", "draft", "qa", "rem", "done"}
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
    """Tests for outcome to state mapping.

    Note: map_node_outcome_to_state returns tuple (ProductionState, Station).
    """

    def test_pgc_needs_input_maps_to_awaiting_operator(self):
        """PGC needing input = awaiting operator."""
        state, station = map_node_outcome_to_state("pgc", "needs_user_input")
        assert state == ProductionState.AWAITING_OPERATOR
        assert station == Station.PGC

    def test_pgc_success_maps_to_in_production_asm(self):
        """PGC success = in production at assembly."""
        state, station = map_node_outcome_to_state("pgc", "success")
        assert state == ProductionState.IN_PRODUCTION
        assert station == Station.ASM

    def test_task_success_maps_to_in_production_qa(self):
        """Task success = in production at QA."""
        state, station = map_node_outcome_to_state("task", "success", is_terminal=False)
        assert state == ProductionState.IN_PRODUCTION
        assert station == Station.QA

    def test_task_success_terminal_maps_to_produced(self):
        """Task success at terminal = produced."""
        state, station = map_node_outcome_to_state("task", "success", is_terminal=True)
        assert state == ProductionState.PRODUCED
        assert station == Station.DONE

    def test_qa_failed_maps_to_in_production_rem(self):
        """QA failure = in production at remediation."""
        state, station = map_node_outcome_to_state("qa", "failed")
        assert state == ProductionState.IN_PRODUCTION
        assert station == Station.REM

    def test_qa_success_maps_to_produced(self):
        """QA success = produced."""
        state, station = map_node_outcome_to_state("qa", "success")
        assert state == ProductionState.PRODUCED
        assert station == Station.DONE

    def test_legacy_pending_maps_to_ready_for_production(self):
        """Legacy 'pending' = ready for production."""
        state, station = map_node_outcome_to_state("unknown", "pending")
        assert state == ProductionState.READY_FOR_PRODUCTION

    def test_legacy_paused_maps_to_awaiting_operator(self):
        """Legacy 'paused' = awaiting operator."""
        state, station = map_node_outcome_to_state("unknown", "paused")
        assert state == ProductionState.AWAITING_OPERATOR

    def test_legacy_failed_maps_to_halted(self):
        """Legacy 'failed' = halted."""
        state, station = map_node_outcome_to_state("unknown", "failed")
        assert state == ProductionState.HALTED


class TestMapStationFromNode:
    """Tests for node to station mapping."""

    def test_pgc_maps_to_pgc(self):
        """PGC node = PGC station."""
        result = map_station_from_node("pgc", "pgc")
        assert result == Station.PGC

    def test_task_maps_to_asm(self):
        """Task node = ASM station."""
        result = map_station_from_node("task", "generation")
        assert result == Station.ASM

    def test_remediation_task_maps_to_rem(self):
        """Remediation task = REM station."""
        result = map_station_from_node("task", "remediation")
        assert result == Station.REM

    def test_qa_maps_to_qa(self):
        """QA node = QA station."""
        result = map_station_from_node("qa", "qa")
        assert result == Station.QA
