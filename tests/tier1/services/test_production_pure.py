"""Tier-1 tests for production_pure.py.

Pure data transformation tests -- no DB, no I/O, no filesystem.
"""


from app.api.services.production_pure import (
    build_child_track,
    build_interrupts,
    build_production_summary,
    build_station_sequence,
    classify_execution_state,
    classify_track_state,
    determine_line_state,
)
from app.domain.workflow.production_state import ProductionState


# =========================================================================
# build_station_sequence
# =========================================================================


class TestBuildStationSequence:
    """Tests for build_station_sequence."""

    def _stations(self):
        return [
            {"id": "pgc", "label": "Pre-Gen Check"},
            {"id": "asm", "label": "Assembly"},
            {"id": "qa", "label": "Audit"},
            {"id": "done", "label": "Complete"},
        ]

    def test_empty_stations_returns_empty(self):
        result = build_station_sequence([], None, "running", None, False)
        assert result == []

    def test_completed_marks_all_complete(self):
        result = build_station_sequence(
            self._stations(), "asm", "completed", None, False
        )
        assert len(result) == 4
        assert all(s["state"] == "complete" for s in result)

    def test_stabilized_marks_all_complete(self):
        result = build_station_sequence(
            self._stations(), "asm", "running", "stabilized", False
        )
        assert all(s["state"] == "complete" for s in result)

    def test_failed_status_marks_current_failed(self):
        result = build_station_sequence(
            self._stations(), "asm", "failed", None, False
        )
        assert result[0]["state"] == "complete"  # pgc before asm
        assert result[1]["state"] == "failed"     # asm is current
        assert result[2]["state"] == "pending"    # qa after
        assert result[3]["state"] == "pending"    # done after

    def test_blocked_terminal_marks_current_failed(self):
        result = build_station_sequence(
            self._stations(), "qa", "running", "blocked", False
        )
        assert result[0]["state"] == "complete"  # pgc
        assert result[1]["state"] == "complete"  # asm
        assert result[2]["state"] == "failed"    # qa is current
        assert result[3]["state"] == "pending"   # done

    def test_running_marks_active_station(self):
        result = build_station_sequence(
            self._stations(), "asm", "running", None, False
        )
        assert result[0]["state"] == "complete"  # pgc
        assert result[1]["state"] == "active"    # asm
        assert result[2]["state"] == "pending"   # qa
        assert result[3]["state"] == "pending"   # done

    def test_pending_user_input_adds_needs_input(self):
        result = build_station_sequence(
            self._stations(), "asm", "running", None, True
        )
        asm = result[1]
        assert asm["state"] == "active"
        assert asm["needs_input"] is True

    def test_unknown_station_id_all_pending(self):
        result = build_station_sequence(
            self._stations(), "unknown_station", "running", None, False
        )
        # current_idx = -1, so nothing is < -1, nothing == -1 after enumeration
        # All should be pending since enumerate produces 0,1,2,3
        assert all(s["state"] == "pending" for s in result)

    def test_first_station_active(self):
        result = build_station_sequence(
            self._stations(), "pgc", "running", None, False
        )
        assert result[0]["state"] == "active"
        assert result[1]["state"] == "pending"
        assert result[2]["state"] == "pending"
        assert result[3]["state"] == "pending"

    def test_last_station_active(self):
        result = build_station_sequence(
            self._stations(), "done", "running", None, False
        )
        assert result[0]["state"] == "complete"
        assert result[1]["state"] == "complete"
        assert result[2]["state"] == "complete"
        assert result[3]["state"] == "active"

    def test_preserves_station_labels(self):
        result = build_station_sequence(
            self._stations(), "pgc", "completed", None, False
        )
        assert result[0]["label"] == "Pre-Gen Check"
        assert result[1]["label"] == "Assembly"

    def test_preserves_station_ids(self):
        result = build_station_sequence(
            self._stations(), "pgc", "completed", None, False
        )
        assert result[0]["station"] == "pgc"
        assert result[3]["station"] == "done"


# =========================================================================
# classify_track_state
# =========================================================================


class TestClassifyTrackState:
    """Tests for classify_track_state."""

    def test_document_exists_not_failed_is_produced(self):
        docs = {"charter": _FakeDoc("complete")}
        state, blocked_by, is_stab = classify_track_state(
            "charter", docs, set(), []
        )
        assert state == ProductionState.PRODUCED.value
        assert blocked_by == []
        assert is_stab is True

    def test_document_exists_failed_is_ready(self):
        docs = {"charter": _FakeDoc("failed")}
        state, blocked_by, is_stab = classify_track_state(
            "charter", docs, set(), []
        )
        assert state == ProductionState.READY_FOR_PRODUCTION.value
        assert is_stab is False

    def test_document_exists_error_is_ready(self):
        docs = {"charter": _FakeDoc("error")}
        state, blocked_by, is_stab = classify_track_state(
            "charter", docs, set(), []
        )
        assert state == ProductionState.READY_FOR_PRODUCTION.value

    def test_document_exists_cancelled_is_ready(self):
        docs = {"charter": _FakeDoc("cancelled")}
        state, blocked_by, is_stab = classify_track_state(
            "charter", docs, set(), []
        )
        assert state == ProductionState.READY_FOR_PRODUCTION.value

    def test_no_document_no_requires_is_ready(self):
        state, blocked_by, is_stab = classify_track_state(
            "charter", {}, set(), []
        )
        assert state == ProductionState.READY_FOR_PRODUCTION.value
        assert blocked_by == []
        assert is_stab is False

    def test_missing_dependency_is_requirements_not_met(self):
        state, blocked_by, is_stab = classify_track_state(
            "charter", {}, set(), ["intake"]
        )
        assert state == ProductionState.REQUIREMENTS_NOT_MET.value
        assert blocked_by == ["intake"]
        assert is_stab is False

    def test_satisfied_dependency_is_ready(self):
        state, blocked_by, is_stab = classify_track_state(
            "charter", {}, {"intake"}, ["intake"]
        )
        assert state == ProductionState.READY_FOR_PRODUCTION.value
        assert blocked_by == []

    def test_partial_dependencies_lists_missing(self):
        state, blocked_by, _ = classify_track_state(
            "charter", {}, {"intake"}, ["intake", "scope"]
        )
        assert state == ProductionState.REQUIREMENTS_NOT_MET.value
        assert blocked_by == ["scope"]

    def test_dict_document_with_status_key(self):
        """classify_track_state should also handle dict-style documents."""
        docs = {"charter": {"status": "complete"}}
        state, blocked_by, is_stab = classify_track_state(
            "charter", docs, set(), []
        )
        assert state == ProductionState.PRODUCED.value
        assert is_stab is True


# =========================================================================
# classify_execution_state
# =========================================================================


class TestClassifyExecutionState:
    """Tests for classify_execution_state."""

    def test_paused_maps_to_awaiting_operator(self):
        assert classify_execution_state("paused") == ProductionState.AWAITING_OPERATOR.value

    def test_running_maps_to_in_production(self):
        assert classify_execution_state("running") == ProductionState.IN_PRODUCTION.value

    def test_in_progress_maps_to_in_production(self):
        assert classify_execution_state("in_progress") == ProductionState.IN_PRODUCTION.value

    def test_unknown_status_returns_none(self):
        assert classify_execution_state("completed") is None

    def test_empty_string_returns_none(self):
        assert classify_execution_state("") is None


# =========================================================================
# build_production_summary
# =========================================================================


class TestBuildProductionSummary:
    """Tests for build_production_summary."""

    def test_empty_tracks(self):
        summary = build_production_summary([])
        assert summary["total"] == 0
        assert summary["produced"] == 0

    def test_counts_each_state(self):
        tracks = [
            {"state": ProductionState.PRODUCED.value},
            {"state": ProductionState.PRODUCED.value},
            {"state": ProductionState.IN_PRODUCTION.value},
            {"state": ProductionState.REQUIREMENTS_NOT_MET.value},
            {"state": ProductionState.READY_FOR_PRODUCTION.value},
            {"state": ProductionState.AWAITING_OPERATOR.value},
        ]
        summary = build_production_summary(tracks)
        assert summary["total"] == 6
        assert summary["produced"] == 2
        assert summary["in_production"] == 1
        assert summary["requirements_not_met"] == 1
        assert summary["ready_for_production"] == 1
        assert summary["awaiting_operator"] == 1

    def test_unknown_state_not_counted(self):
        tracks = [{"state": "unknown_state"}]
        summary = build_production_summary(tracks)
        assert summary["total"] == 1
        assert summary["produced"] == 0
        assert summary["in_production"] == 0


# =========================================================================
# determine_line_state
# =========================================================================


class TestDetermineLineState:
    """Tests for determine_line_state."""

    def test_active_when_in_production(self):
        assert determine_line_state({
            "in_production": 1, "awaiting_operator": 0, "produced": 2, "total": 5
        }) == "active"

    def test_stopped_when_awaiting_operator(self):
        assert determine_line_state({
            "in_production": 0, "awaiting_operator": 1, "produced": 2, "total": 5
        }) == "stopped"

    def test_complete_when_all_produced(self):
        assert determine_line_state({
            "in_production": 0, "awaiting_operator": 0, "produced": 5, "total": 5
        }) == "complete"

    def test_idle_otherwise(self):
        assert determine_line_state({
            "in_production": 0, "awaiting_operator": 0, "produced": 2, "total": 5
        }) == "idle"

    def test_active_takes_priority_over_awaiting(self):
        assert determine_line_state({
            "in_production": 1, "awaiting_operator": 1, "produced": 0, "total": 5
        }) == "active"

    def test_complete_zero_total(self):
        assert determine_line_state({
            "in_production": 0, "awaiting_operator": 0, "produced": 0, "total": 0
        }) == "complete"


# =========================================================================
# build_interrupts
# =========================================================================


class TestBuildInterrupts:
    """Tests for build_interrupts."""

    def test_no_interrupts_for_produced(self):
        tracks = [{"state": ProductionState.PRODUCED.value, "document_type": "charter"}]
        assert build_interrupts(tracks, "proj-1") == []

    def test_interrupt_for_awaiting_operator(self):
        tracks = [
            {"state": ProductionState.AWAITING_OPERATOR.value, "document_type": "charter"},
        ]
        result = build_interrupts(tracks, "proj-1")
        assert len(result) == 1
        assert result[0]["document_type"] == "charter"
        assert "proj-1" in result[0]["resolve_url"]
        assert "charter" in result[0]["resolve_url"]

    def test_multiple_interrupts(self):
        tracks = [
            {"state": ProductionState.AWAITING_OPERATOR.value, "document_type": "a"},
            {"state": ProductionState.PRODUCED.value, "document_type": "b"},
            {"state": ProductionState.AWAITING_OPERATOR.value, "document_type": "c"},
        ]
        result = build_interrupts(tracks, "proj-1")
        assert len(result) == 2
        assert result[0]["document_type"] == "a"
        assert result[1]["document_type"] == "c"


# =========================================================================
# build_child_track
# =========================================================================


class TestBuildChildTrack:
    """Tests for build_child_track."""

    def test_basic_child_track(self):
        result = build_child_track(
            doc_type_id="epic",
            title="Epic 1",
            content={"intent": "Build it", "epic_id": "E-001", "sequence": 1},
            instance_id="inst-123",
        )
        assert result["document_type"] == "epic"
        assert result["document_name"] == "Epic 1"
        assert result["description"] == "Build it"
        assert result["identifier"] == "E-001"
        assert result["sequence"] == 1
        assert result["instance_id"] == "inst-123"
        assert result["state"] == ProductionState.PRODUCED.value
        assert result["stations"] == []
        assert result["blocked_by"] == []

    def test_title_none_falls_back_to_name(self):
        result = build_child_track(
            doc_type_id="epic",
            title=None,
            content={"name": "Epic from content"},
            instance_id="inst-456",
        )
        assert result["document_name"] == "Epic from content"

    def test_title_none_no_name_falls_back_to_doc_type(self):
        result = build_child_track(
            doc_type_id="epic",
            title=None,
            content={},
            instance_id="inst-789",
        )
        assert result["document_name"] == "epic"

    def test_missing_content_fields_default_empty(self):
        result = build_child_track(
            doc_type_id="epic",
            title="Test",
            content={},
            instance_id=None,
        )
        assert result["intent"] if "intent" in result else result["description"] == ""
        assert result["identifier"] == ""
        assert result["sequence"] is None
        assert result["instance_id"] is None


# =========================================================================
# Helpers
# =========================================================================


class _FakeDoc:
    """Minimal fake document for testing classify_track_state."""

    def __init__(self, status: str):
        self.status = status
