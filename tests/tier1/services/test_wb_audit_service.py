"""
Tests for wb_audit_service pure functions — WS-WB-008.

Tests the audit event builder: structure, timestamps, field completeness,
and event type validation.
"""

from datetime import datetime, timezone

import pytest

from app.domain.services.wb_audit_service import (
    SUPPORTED_EVENT_TYPES,
    build_audit_event,
)


# ===========================================================================
# build_audit_event — structure and fields
# ===========================================================================


class TestBuildAuditEventStructure:
    """Verify build_audit_event produces correct structure."""

    def test_returns_dict_with_all_required_keys(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={"title": "Test WS"},
            actor="system",
        )
        required_keys = {
            "event_type", "entity_id", "entity_type",
            "timestamp", "actor", "mutation_data",
        }
        assert required_keys == set(result.keys())

    def test_event_type_preserved(self):
        result = build_audit_event(
            event_type="wp_updated",
            entity_id="wp_wb_001",
            entity_type="work_package",
            mutation_data={},
        )
        assert result["event_type"] == "wp_updated"

    def test_entity_id_preserved(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-042",
            entity_type="work_statement",
            mutation_data={},
        )
        assert result["entity_id"] == "WS-WB-042"

    def test_entity_type_preserved(self):
        result = build_audit_event(
            event_type="candidate_import",
            entity_id="WPC-001",
            entity_type="work_package_candidate",
            mutation_data={},
        )
        assert result["entity_type"] == "work_package_candidate"

    def test_mutation_data_preserved(self):
        data = {"before": {"state": "DRAFT"}, "after": {"state": "READY"}}
        result = build_audit_event(
            event_type="state_transition",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data=data,
        )
        assert result["mutation_data"] == data

    def test_actor_default_is_system(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={},
        )
        assert result["actor"] == "system"

    def test_actor_custom_value(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={},
            actor="tom",
        )
        assert result["actor"] == "tom"


# ===========================================================================
# build_audit_event — timestamp validation
# ===========================================================================


class TestBuildAuditEventTimestamp:
    """Verify timestamps are ISO UTC format."""

    def test_timestamp_is_iso_format(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={},
        )
        # Should parse without error
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed is not None

    def test_timestamp_is_utc(self):
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={},
        )
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed.tzinfo == timezone.utc

    def test_timestamp_is_recent(self):
        before = datetime.now(timezone.utc)
        result = build_audit_event(
            event_type="ws_created",
            entity_id="WS-WB-001",
            entity_type="work_statement",
            mutation_data={},
        )
        after = datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(result["timestamp"])
        assert before <= parsed <= after


# ===========================================================================
# build_audit_event — all supported event types
# ===========================================================================


class TestBuildAuditEventTypes:
    """Verify build_audit_event works for every supported event type."""

    @pytest.mark.parametrize("event_type", sorted(SUPPORTED_EVENT_TYPES))
    def test_supported_event_type_produces_valid_event(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="test-id",
            entity_type="test-type",
            mutation_data={"key": "value"},
        )
        assert result["event_type"] == event_type
        assert "timestamp" in result
        assert "actor" in result

    def test_unsupported_event_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported event_type"):
            build_audit_event(
                event_type="bogus_event",
                entity_id="test-id",
                entity_type="test-type",
                mutation_data={},
            )

    def test_empty_event_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported event_type"):
            build_audit_event(
                event_type="",
                entity_id="test-id",
                entity_type="test-type",
                mutation_data={},
            )
